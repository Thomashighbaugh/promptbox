from sqlalchemy import func
from promptbox.db.database import get_db
from promptbox.db.models import ChatLog as ChatLogDBModel, Prompt as PromptDBModel
from promptbox.services.llm_service import LLMService
from promptbox.services.prompt_service import PromptService
from promptbox.utils.file_handler import save_markdown_file

class ChatService:
    def __init__(self, llm_service: LLMService, prompt_service: PromptService):
        self.llm_service = llm_service
        self.prompt_service = prompt_service

    def get_next_log_number(self, db_session, prompt_id: int) -> str:
        highest_num = db_session.query(func.max(func.substr(ChatLogDBModel.log_name, -2)))\
            .filter(ChatLogDBModel.prompt_id == prompt_id)\
            .scalar()

        next_num = 0
        if highest_num and highest_num.isdigit():
            next_num = int(highest_num) + 1
        
        return f"{next_num:02d}"

    def save_chat_log(self, prompt_id: int, chat_content: str) -> bool:
        with get_db() as db:
            prompt = db.query(PromptDBModel).filter(PromptDBModel.id == prompt_id).first()
            if not prompt:
                return False

            log_name = f"{prompt.name}_chat_{self.get_next_log_number(db, prompt_id)}"
            new_log = ChatLogDBModel(
                prompt_id=prompt_id,
                log_name=log_name,
                content=chat_content
            )
            db.add(new_log)
            db.commit()
            return True

    def get_chat_logs_for_prompt(self, prompt_id: int) -> list[ChatLogDBModel]:
        with get_db() as db:
            return db.query(ChatLogDBModel).filter(ChatLogDBModel.prompt_id == prompt_id).order_by(ChatLogDBModel.created_at.desc()).all()

    def delete_chat_log(self, log_id: int) -> bool:
        with get_db() as db:
            log = db.query(ChatLogDBModel).filter(ChatLogDBModel.id == log_id).first()
            if log:
                db.delete(log)
                db.commit()
                return True
            return False
            
    def export_log_to_markdown(self, log_id: int) -> str | None:
        from promptbox.utils.file_handler import save_markdown_file
        with get_db() as db:
            log = db.query(ChatLogDBModel).filter(ChatLogDBModel.id == log_id).first()
            if not log:
                return None
        file_path = save_markdown_file(f"{log.log_name}.md", log.content)
        return file_path
