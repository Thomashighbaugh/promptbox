"""
Defines the interactive chat user interface.

This module contains the ChatUI class which manages an entire chat session,
from model selection to the interactive conversation loop, including handling
streaming output from the LLM.
"""

from rich.live import Live
from rich.panel import Panel
from rich.markdown import Markdown

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage

from promptbox.models.prompt import PromptData
from promptbox.services.llm_service import LLMService
from promptbox.services.chat_service import ChatService
from promptbox.tui.components import console, create_header
from promptbox.tui.menus import clear_screen, get_user_input, create_menu

def select_llm_model(llm_service: LLMService) -> tuple[str, str] | None:
    """
    Presents a menu for the user to select an available LLM.

    Returns:
        A tuple of (provider_name, model_name) or None if selection is cancelled.
    """
    clear_screen()
    console.print(create_header())
    console.print("\n[bold]Select a Language Model for this Chat[/bold]\n")
    
    available_models = llm_service.list_available_models()
    if not available_models:
        console.print("[danger]No language models are available. Check your API keys or Ollama connection.[/]")
        get_user_input("\nPress Enter to return...")
        return None

    options = {}
    providers = list(available_models.keys())
    for i, provider in enumerate(providers):
        console.print(f"[menu_key]({i+1})[/] - [menu_text]{provider}[/]")
    
    provider_choice = get_user_input("\nChoose a provider: ")
    if not provider_choice.isdigit() or not (1 <= int(provider_choice) <= len(providers)):
        return None
    
    selected_provider = providers[int(provider_choice) - 1]
    models = available_models[selected_provider]

    console.print(f"\n[bold]Available models for {selected_provider}:[/bold]\n")
    for i, model in enumerate(models):
        console.print(f"[menu_key]({i+1})[/] - [menu_text]{model}[/]")

    model_choice = get_user_input("\nChoose a model: ")
    if not model_choice.isdigit() or not (1 <= int(model_choice) <= len(models)):
        return None

    selected_model = models[int(model_choice) - 1]
    return selected_provider, selected_model


class ChatUI:
    def __init__(self, llm_service: LLMService, chat_service: ChatService, prompt_data: PromptData, provider: str, model_name: str):
        self.llm_service = llm_service
        self.chat_service = chat_service
        self.prompt_data = prompt_data
        self.model = self.llm_service.get_chat_model(provider, model_name)
        self.history: list[BaseMessage] = []
        self._initialize_history()

    def _initialize_history(self):
        """Sets up the initial messages from the prompt template."""
        if self.prompt_data.system_instruction:
            self.history.append(SystemMessage(content=self.prompt_data.system_instruction))
        
        if self.prompt_data.user_instruction:
            self.history.append(HumanMessage(content=self.prompt_data.user_instruction))
        if self.prompt_data.assistant_instruction:
            self.history.append(AIMessage(content=self.prompt_data.assistant_instruction))

    def _render_history(self) -> Panel:
        """Renders the entire conversation history into a Rich Panel."""
        content = ""
        for msg in self.history:
            if isinstance(msg, SystemMessage):
                content += f"**System:**\n> {msg.content}\n\n---\n"
            elif isinstance(msg, HumanMessage):
                content += f"**You:**\n{msg.content}\n\n---\n"
            elif isinstance(msg, AIMessage):
                content += f"**Assistant:**\n{msg.content}\n\n---\n"
        
        return Panel(Markdown(content.strip()), title="Chat Session", border_style="cyan", expand=True)

    def _get_ai_response(self):
        """
        Streams the AI's response to the console and updates the history.
        """
        ai_response_content = ""
        # Create a temporary panel for the streaming response
        response_panel = Panel(Markdown("Thinking..."), title="Assistant", border_style="green", expand=True)
        
        with Live(response_panel, console=console, auto_refresh=False, vertical_overflow="visible") as live:
            try:
                for chunk in self.model.stream(self.history):
                    ai_response_content += chunk.content
                    live.update(
                        Panel(Markdown(ai_response_content + "▌"), title="Assistant", border_style="green", expand=True),
                        refresh=True
                    )
            except Exception as e:
                ai_response_content = f"An error occurred: {e}"
                live.update(Panel(ai_response_content, title="Error", border_style="red"), refresh=True)
        
        self.history.append(AIMessage(content=ai_response_content))

    def _render_ui(self):
        """Clears screen and renders the chat history and input panel."""
        clear_screen()
        console.print(self._render_history())
        
        input_instructions = "Type your message below. Use [bold]'/save'[/] to save the log, or [bold]'/exit'[/] to finish."
        console.print(Panel(input_instructions, title="Input", border_style="green"))

    def run(self):
        """Starts the interactive chat loop."""
        if not self.model:
            console.print("[danger]Chat model could not be initialized. Aborting chat.[/]")
            get_user_input()
            return
        
        # --- Automatic First Turn ---
        # If the last message in the history is from the user, the AI should respond automatically.
        if self.history and isinstance(self.history[-1], HumanMessage):
            self._render_ui()
            self._get_ai_response()

        while True:
            self._render_ui()
            user_input = get_user_input("You: ")

            if user_input.lower() == '/exit':
                break
            
            if user_input.lower() == '/save':
                full_log = "\n".join([f"{type(m).__name__}: {m.content}" for m in self.history])
                if self.chat_service.save_chat_log(self.prompt_data.id, full_log):
                    console.print("[info]Chat log saved.[/]")
                else:
                    console.print("[danger]Failed to save chat log.[/]")
                get_user_input("Press Enter to continue...")
                continue
            
            self.history.append(HumanMessage(content=user_input))
            self._render_ui() # Show the user's message immediately
            self._get_ai_response()
