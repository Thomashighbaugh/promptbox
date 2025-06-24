import json
import streamlit as st
from sqlalchemy import or_
from langchain_core.language_models import BaseChatModel
from promptbox.db.database import get_db
from promptbox.db.models import Prompt as PromptDBModel
from promptbox.models.data_models import PromptData # Updated import
from promptbox.services.llm_service import LLMService

class PromptService:
    def __init__(self, llm_service: LLMService | None = None):
        self.llm_service = llm_service

    def _db_to_pydantic(self, prompt: PromptDBModel) -> PromptData:
        return PromptData(
            id=prompt.id,
            name=prompt.name,
            description=prompt.description,
            system_instruction=prompt.system_instruction,
            user_instruction=prompt.user_instruction,
            assistant_instruction=prompt.assistant_instruction,
            # tags field removed
            folder=prompt.folder,
            created_at=prompt.created_at,
            updated_at=prompt.updated_at,
        )

    def create_prompt(self, prompt_data: PromptData) -> PromptData:
        with get_db() as db:
            # tags_str removed
            new_prompt = PromptDBModel(
                name=prompt_data.name,
                description=prompt_data.description,
                system_instruction=prompt_data.system_instruction,
                user_instruction=prompt_data.user_instruction,
                assistant_instruction=prompt_data.assistant_instruction,
                # tags field removed
                folder=prompt_data.folder,
            )
            db.add(new_prompt)
            db.commit()
            db.refresh(new_prompt)
            return self._db_to_pydantic(new_prompt)

    def get_prompt_by_id(self, prompt_id: int) -> PromptData | None:
        with get_db() as db:
            prompt = db.query(PromptDBModel).filter(PromptDBModel.id == prompt_id).first()
            return self._db_to_pydantic(prompt) if prompt else None

    def get_all_prompts(self) -> list[PromptData]:
        with get_db() as db:
            prompts = db.query(PromptDBModel).order_by(PromptDBModel.folder, PromptDBModel.name).all()
            return [self._db_to_pydantic(p) for p in prompts]
            
    def get_prompts_by_folder(self, folder_path: str | None) -> list[PromptData]:
        """
        Retrieves prompts, optionally filtered by a folder path.
        If folder_path is None, returns all prompts.
        If folder_path is specified, returns prompts in that folder and its subfolders.
        """
        with get_db() as db:
            query = db.query(PromptDBModel)
            if folder_path and folder_path != "All": # Assuming "All" means no filter
                # Ensure trailing slash for parent folder matching if that's the desired logic for "starts with"
                # If exact match: .filter(PromptDBModel.folder == folder_path)
                # If match folder and subfolders:
                query = query.filter(PromptDBModel.folder.like(f"{folder_path}%"))
            
            prompts = query.order_by(PromptDBModel.folder, PromptDBModel.name).all()
            return [self._db_to_pydantic(p) for p in prompts]

    def get_distinct_folders(self) -> list[str]:
        """Gets a list of all unique folder paths."""
        with get_db() as db:
            # Query for distinct folder values, filter out None or empty strings if necessary
            folders = db.query(PromptDBModel.folder).distinct().all()
            # Flatten the list of tuples and filter out any None/empty values
            return sorted([folder[0] for folder in folders if folder[0]])


    def update_prompt(self, prompt_id: int, prompt_data: PromptData) -> PromptData | None:
        with get_db() as db:
            prompt = db.query(PromptDBModel).filter(PromptDBModel.id == prompt_id).first()
            if not prompt:
                return None

            prompt.name = prompt_data.name
            prompt.description = prompt_data.description
            prompt.system_instruction = prompt_data.system_instruction
            prompt.user_instruction = prompt_data.user_instruction
            prompt.assistant_instruction = prompt_data.assistant_instruction
            # tags field removed
            prompt.folder = prompt_data.folder

            db.commit()
            db.refresh(prompt)
            return self._db_to_pydantic(prompt)

    def delete_prompt(self, prompt_id: int) -> bool:
        with get_db() as db:
            prompt = db.query(PromptDBModel).filter(PromptDBModel.id == prompt_id).first()
            if prompt:
                db.delete(prompt)
                db.commit()
                return True
            return False

    def search_prompts_full_text(self, query: str) -> list[PromptData]:
        with get_db() as db:
            search_term = f"%{query.lower()}%"
            # tags field removed from search
            results = db.query(PromptDBModel).filter(
                or_(
                    PromptDBModel.name.ilike(search_term),
                    PromptDBModel.description.ilike(search_term),
                    PromptDBModel.system_instruction.ilike(search_term),
                    PromptDBModel.user_instruction.ilike(search_term),
                    PromptDBModel.assistant_instruction.ilike(search_term),
                    PromptDBModel.folder.ilike(search_term) # Added folder to search
                )
            ).order_by(PromptDBModel.folder, PromptDBModel.name).all()
            return [self._db_to_pydantic(r) for r in results]

    def improve_prompt(self, prompt_id: int, llm: BaseChatModel) -> dict[str, str] | None:
        if not self.llm_service:
            st.error("LLMService is not configured for prompt improvement.") # More direct error
            # raise ValueError("LLMService is not configured.") # Or raise an error
            return None

        prompt_data = self.get_prompt_by_id(prompt_id)
        if not prompt_data:
            st.error(f"Prompt with ID {prompt_id} not found.")
            return None

        original_prompt_text = f"""
        "system_instruction": "{prompt_data.system_instruction or ''}",
        "user_instruction": "{prompt_data.user_instruction or ''}",
        "assistant_instruction": "{prompt_data.assistant_instruction or ''}"
        """

        optimization_instruction = f"""
        You are an expert prompt engineer. Your task is to analyze the following LLM prompt and rewrite it to be clearer, more effective, and more robust.
        Focus on clarity, specificity, and removing ambiguity.

        You MUST return ONLY a single, valid JSON object containing the rewritten prompt.
        The JSON object must have three keys: "system_instruction", "user_instruction", and "assistant_instruction".
        Do not include any text, notes, or explanations before or after the JSON object.

        Original prompt JSON to improve:
        ---
        {{
        {original_prompt_text}
        }}
        ---
        """

        try:
            response = llm.invoke(optimization_instruction)
            # Ensure response.content is a string before find/rfind
            response_content_str = str(response.content)
            json_start = response_content_str.find('{')
            json_end = response_content_str.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                st.error("LLM did not return a valid JSON object structure.")
                return None

            clean_json_str = response_content_str[json_start:json_end]
            improved_data = json.loads(clean_json_str)

            # Validate the structure of the returned JSON
            if not all(key in improved_data for key in ["system_instruction", "user_instruction", "assistant_instruction"]):
                st.error("LLM returned JSON with missing keys. Required: 'system_instruction', 'user_instruction', 'assistant_instruction'.")
                return None
                
            return {
                "system_instruction": improved_data.get("system_instruction", ""),
                "user_instruction": improved_data.get("user_instruction", ""),
                "assistant_instruction": improved_data.get("assistant_instruction", "")
            }
            
        except json.JSONDecodeError:
            st.error(f"Failed to decode JSON from the LLM response. Content received:```{clean_json_str}```")
            return None
        except Exception as e:
             st.error(f"An error occurred during JSON decoding: {e}")
        return None
