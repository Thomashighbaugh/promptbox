import json
from sqlalchemy import or_
from langchain_core.language_models import BaseChatModel
from promptbox.db.database import get_db
from promptbox.db.models import Prompt as PromptDBModel
from promptbox.models.prompt import PromptData
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
            tags=prompt.tags.split(',') if prompt.tags else [],
            folder=prompt.folder,
            created_at=prompt.created_at,
            updated_at=prompt.updated_at,
        )

    def create_prompt(self, prompt_data: PromptData) -> PromptData:
        with get_db() as db:
            tags_str = ','.join(prompt_data.tags)
            new_prompt = PromptDBModel(
                name=prompt_data.name,
                description=prompt_data.description,
                system_instruction=prompt_data.system_instruction,
                user_instruction=prompt_data.user_instruction,
                assistant_instruction=prompt_data.assistant_instruction,
                tags=tags_str,
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
            prompts = db.query(PromptDBModel).order_by(PromptDBModel.name).all()
            return [self._db_to_pydantic(p) for p in prompts]

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
            prompt.tags = ','.join(prompt_data.tags)
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
            results = db.query(PromptDBModel).filter(
                or_(
                    PromptDBModel.name.ilike(search_term),
                    PromptDBModel.description.ilike(search_term),
                    PromptDBModel.system_instruction.ilike(search_term),
                    PromptDBModel.user_instruction.ilike(search_term),
                    PromptDBModel.assistant_instruction.ilike(search_term),
                    PromptDBModel.tags.ilike(search_term)
                )
            ).all()
            return [self._db_to_pydantic(r) for r in results]

    def improve_prompt(self, prompt_id: int, llm: BaseChatModel) -> dict[str, str] | None:
        if not self.llm_service:
            raise ValueError("LLMService is not configured.")

        prompt_data = self.get_prompt_by_id(prompt_id)
        if not prompt_data:
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
            json_start = response.content.find('{')
            json_end = response.content.rfind('}') + 1
            if json_start == -1 or json_end == 0:
                print("[danger]Error: LLM did not return a valid JSON object.[/]")
                return None
            
            clean_json_str = response.content[json_start:json_end]
            improved_data = json.loads(clean_json_str)
            return improved_data
        except json.JSONDecodeError:
            print("[danger]Error: Failed to decode JSON from the LLM response.[/]")
            return None
        except Exception as e:
            print(f"[danger]An error occurred during prompt improvement: {e}[/]")
            return None
