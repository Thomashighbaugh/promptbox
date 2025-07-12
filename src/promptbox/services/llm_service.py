import requests
import streamlit as st

# Langchain imports for model instantiation
from langchain_core.language_models import BaseChatModel
from langchain_community.chat_models import ChatOllama
from langchain_mistralai import ChatMistralAI
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

# Native client imports for dynamically listing models
import groq
import google.generativeai as genai
from openai import OpenAI

from promptbox.core.config import settings


class LLMService:
    def get_chat_model(self, provider: str, model_name: str) -> BaseChatModel | None:
        try:
            match provider.lower():
                case "ollama":
                    return ChatOllama(model=model_name, base_url=settings.ollama_api_base)
                case "mistral":
                    return ChatMistralAI(model=model_name, api_key=settings.mistral_api_key)
                case "groq":
                    return ChatGroq(model_name=model_name, api_key=settings.groq_api_key)
                case "gemini":
                    return ChatGoogleGenerativeAI(model=model_name, google_api_key=settings.google_api_key)
                case "cerebras":
                    return ChatOpenAI(model=model_name, api_key=settings.cerebras_api_key, base_url="https://api.cerebras.ai/v1")
                case "nvidia":
                    return ChatOpenAI(model=model_name, api_key=settings.nvidia_api_key, base_url="https://integrate.api.nvidia.com/v1")
                case "github":
                    # GitHub models in the example are served via an Azure-like endpoint
                    if not settings.azure_openai_endpoint:
                        st.error("GitHub provider requires AZURE_OPENAI_ENDPOINT to be set in .env")
                        return None
                    return ChatOpenAI(model=model_name, api_key=settings.github_access_token, base_url=settings.azure_openai_endpoint)
                case _:
                    st.warning(f"Unknown provider '{provider}'")
                    return None
        except Exception as e:
            st.error(f"Error initializing model '{model_name}' from '{provider}': {e}")
            return None

    @st.cache_data(show_spinner="Fetching available LLM models...")
    def list_available_models(_self) -> dict[str, list[str]]:
        """
        Using st.cache_data to prevent re-fetching models on every UI interaction.
        The `_self` parameter is used because st.cache_data doesn't work on methods
        out of the box, so we make it act like a static method for caching purposes.
        """
        models = {}

        # --- Ollama (direct HTTP request, ignoring proxies) ---
        try:
            url = f"{settings.ollama_api_base}/api/tags"
            response = requests.get(
                url,
                timeout=3,
                proxies={'http': None, 'https': None}
            )
            response.raise_for_status()
            model_data = response.json()
            if model_data.get('models'):
                models["Ollama"] = sorted([m['name'] for m in model_data['models']])
        except Exception:
            st.warning(f"Could not connect to Ollama at '{settings.ollama_api_base}'. Ensure the server is running.")

        # --- Mistral (dynamic via direct HTTP request) ---
        if settings.mistral_api_key:
            try:
                headers = {"Authorization": f"Bearer {settings.mistral_api_key}"}
                response = requests.get("https://api.mistral.ai/v1/models", headers=headers, timeout=3)
                response.raise_for_status()
                model_data = response.json()
                models["Mistral"] = sorted([m['id'] for m in model_data.get('data', [])])
            except Exception as e:
                st.warning(f"Could not fetch Mistral models. Check API key. Error: {e}")

        # --- Groq (dynamic) ---
        if settings.groq_api_key:
            try:
                client = groq.Groq(api_key=settings.groq_api_key)
                model_list = client.models.list()
                models["Groq"] = sorted([m.id for m in model_list.data if m.active])
            except Exception as e:
                st.warning(f"Could not fetch Groq models. Check API key. Error: {e}")

        # --- Gemini (dynamic) ---
        if settings.google_api_key:
            try:
                genai.configure(api_key=settings.google_api_key)
                model_list = genai.list_models()
                chat_models = [m.name for m in model_list if 'generateContent' in m.supported_generation_methods]
                models["Gemini"] = sorted([name.replace('models/', '') for name in chat_models])
            except Exception as e:
                st.warning(f"Could not fetch Gemini models. Check API key. Error: {e}")

        # --- Cerebras (dynamic) ---
        if settings.cerebras_api_key:
            try:
                client = OpenAI(api_key=settings.cerebras_api_key, base_url="https://api.cerebras.ai/v1")
                model_list = client.models.list()
                models["Cerebras"] = sorted([m.id for m in model_list.data])
            except Exception as e:
                st.warning(f"Could not fetch Cerebras models. Check API key. Error: {e}")

        # --- NVIDIA (static list from config) ---
        # This provider will only appear in the dropdown if NVIDIA_API_KEY is set in your .env file.
        if settings.nvidia_api_key:
            if settings.nvidia_available_models:
                model_names = [name.strip() for name in settings.nvidia_available_models.split(',') if name.strip()]
                if model_names:
                    models["Nvidia"] = sorted(model_names)
            else:
                st.warning("NVIDIA API key found, but no models listed in NVIDIA_AVAILABLE_MODELS env var.")

        # --- GitHub (static list) ---
        # This provider will only appear if GITHUB_ACCESS_TOKEN and AZURE_OPENAI_ENDPOINT are set in your .env file.
        if settings.github_access_token and settings.azure_openai_endpoint:
            # This list is from the example script
            deployment_names = [
                "openai/o1", "openai/o1-mini", "openai/o1-preview", "openai/gpt-4o-mini", "openai/gpt-4o",
                "deepseek/DeepSeek-V3-0324", "deepseek/DeepSeek-R1",
                "ai21-labs/AI21-Jamba-1.5-Large", "ai21-labs/AI21-Jamba-1.5-Mini",
                "cohere/cohere-command-r", "cohere/cohere-command-r-plus", "cohere/cohere-command-a",
                "mistral-ai/Mistral-Nemo", "mistral-ai/Mistral-Small",
                "mistral-ai/Mistral-Large-2411", "mistral-ai/Codestral-22B-v0.1",
                "meta/Llama-3.2-11B-Vision-Instruct", "meta/Llama-3.2-90B-Vision-Instruct",
                "meta/Llama-3.3-70B-Instruct", "meta/Llama-3.1-8B-Instruct",
                "meta/Llama-3.1-70B-Instruct", "meta/Llama-3.1-405B-Instruct",
                "meta/Llama-3-8B-Instruct", "meta/Llama-3-70B-Instruct",
                "microsoft/Phi-4", "microsoft/Phi-3.5-MoE-instruct",
                "microsoft/Phi-3.5-mini-instruct", "microsoft/Phi-3.5-vision-instruct",
                "microsoft/Phi-3-mini-4k-instruct", "microsoft/Phi-3-mini-128k-instruct",
                "microsoft/Phi-3-small-8k-instruct", "microsoft/Phi-3-small-128k-instruct",
                "microsoft/Phi-3-medium-4k-instruct", "microsoft/Phi-3-medium-128k-instruct",
                "xai/grok-3",
                "core42/jais-30b-chat"
            ]
            models["GitHub"] = sorted(deployment_names)

        return models
