"""
Service layer for handling business logic related to Chat Sessions and Messages.
"""
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import joinedload
from promptbox.db.connection_manager import get_db, DB_SESSIONS, SQLAlchemySession as Session # MODIFIED IMPORT
from promptbox.db.models import ChatSession as ChatSessionDBModel, ChatMessage as ChatMessageDBModel
from promptbox.models.data_models import ChatSessionData, ChatMessageData
from promptbox.core.config import settings

class ChatService:

    def _db_chat_message_to_pydantic(self, msg: ChatMessageDBModel) -> ChatMessageData:
        return ChatMessageData.model_validate(msg)

    def _db_chat_session_to_pydantic(self, session: ChatSessionDBModel, include_messages: bool = True) -> ChatSessionData:
        messages = []
        if include_messages and session.messages: # session.messages relationship still works locally
            messages = [self._db_chat_message_to_pydantic(msg) for msg in session.messages]

        return ChatSessionData(
            id=session.id,
            session_name=session.session_name,
            llm_provider=session.llm_provider,
            llm_model_name=session.llm_model_name,
            originating_prompt_id=session.originating_prompt_id,
            originating_card_id=session.originating_card_id,
            created_at=session.created_at,
            updated_at=session.updated_at,
            messages=messages
        )

    def create_chat_session(self, session_data: ChatSessionData) -> ChatSessionData:
        with get_db(DB_SESSIONS) as db: # MODIFIED
            new_session_db = ChatSessionDBModel(
                session_name=session_data.session_name,
                llm_provider=session_data.llm_provider,
                llm_model_name=session_data.llm_model_name,
                originating_prompt_id=session_data.originating_prompt_id,
                originating_card_id=session_data.originating_card_id
            )
            db.add(new_session_db)
            db.commit()
            db.refresh(new_session_db)

            if session_data.messages:
                for order, msg_data in enumerate(session_data.messages):
                    new_msg_db = ChatMessageDBModel(
                        session_id=new_session_db.id,
                        role=msg_data.role,
                        content=msg_data.content,
                        message_order=msg_data.message_order # Use provided order
                    )
                    db.add(new_msg_db)
                db.commit()
                db.refresh(new_session_db) # Refresh to load messages relationship

            return self._db_chat_session_to_pydantic(new_session_db, include_messages=True)

    def add_message_to_session(self, session_id: int, message_data: ChatMessageData, db_session: Optional[Session] = None) -> ChatMessageData | None:
        def _add_message(s: Session):
            # No need to query session if we are just adding a message with session_id
            # However, if we wanted to update session's updated_at, we would query.
            # For now, this is simpler.
            new_message = ChatMessageDBModel(
                session_id=session_id, # Assumes session_id is valid
                role=message_data.role,
                content=message_data.content,
                message_order=message_data.message_order
            )
            s.add(new_message)
            s.commit()
            s.refresh(new_message)

            # Update the parent session's updated_at timestamp
            session_to_update = s.query(ChatSessionDBModel).filter(ChatSessionDBModel.id == session_id).first()
            if session_to_update:
                session_to_update.updated_at = datetime.utcnow()
                s.commit()
            return self._db_chat_message_to_pydantic(new_message)

        if db_session:
            return _add_message(db_session)
        else:
            with get_db(DB_SESSIONS) as new_db: # MODIFIED
                return _add_message(new_db)

    def save_chat_messages(self, session_id: int, messages: List[ChatMessageData]) -> List[ChatMessageData]:
        with get_db(DB_SESSIONS) as db: # MODIFIED
            db.query(ChatMessageDBModel).filter(ChatMessageDBModel.session_id == session_id).delete()
            db.commit() # Commit deletion first

            saved_messages_pydantic = []
            for msg_data in messages:
                new_message_db = ChatMessageDBModel(
                    session_id=session_id,
                    role=msg_data.role,
                    content=msg_data.content,
                    message_order=msg_data.message_order
                )
                db.add(new_message_db)
            db.commit()

            newly_saved_db_messages = db.query(ChatMessageDBModel)\
                .filter(ChatMessageDBModel.session_id == session_id)\
                .order_by(ChatMessageDBModel.message_order)\
                .all()

            # Update the parent session's updated_at timestamp
            session_to_update = db.query(ChatSessionDBModel).filter(ChatSessionDBModel.id == session_id).first()
            if session_to_update:
                session_to_update.updated_at = datetime.utcnow()
                db.commit()

            return [self._db_chat_message_to_pydantic(msg) for msg in newly_saved_db_messages]


    def get_chat_session(self, session_id: int) -> ChatSessionData | None:
        with get_db(DB_SESSIONS) as db: # MODIFIED
            session = db.query(ChatSessionDBModel)\
                .options(joinedload(ChatSessionDBModel.messages))\
                .filter(ChatSessionDBModel.id == session_id)\
                .first()
            return self._db_chat_session_to_pydantic(session, include_messages=True) if session else None

    def get_all_chat_sessions(self) -> List[ChatSessionData]:
        with get_db(DB_SESSIONS) as db: # MODIFIED
            sessions = db.query(ChatSessionDBModel)\
                .order_by(ChatSessionDBModel.updated_at.desc())\
                .all()
            return [self._db_chat_session_to_pydantic(s, include_messages=False) for s in sessions]

    def delete_chat_session(self, session_id: int) -> bool:
        with get_db(DB_SESSIONS) as db: # MODIFIED
            session = db.query(ChatSessionDBModel).filter(ChatSessionDBModel.id == session_id).first()
            if session:
                db.delete(session) # Messages are deleted due to cascade within sessions.db
                db.commit()
                return True
            return False

    def update_chat_session_metadata(self, session_id: int, session_name: Optional[str] = None, llm_provider: Optional[str] = None, llm_model_name: Optional[str] = None) -> ChatSessionData | None:
        with get_db(DB_SESSIONS) as db: # MODIFIED
            session = db.query(ChatSessionDBModel).filter(ChatSessionDBModel.id == session_id).first()
            if not session:
                return None

            if session_name is not None:
                session.session_name = session_name
            if llm_provider is not None:
                session.llm_provider = llm_provider
            if llm_model_name is not None:
                session.llm_model_name = llm_model_name

            session.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(session)
            return self._db_chat_session_to_pydantic(session, include_messages=False)

    def export_session_to_markdown(self, session_id: int) -> str | None:
        from promptbox.utils.file_handler import save_markdown_file

        session_data = self.get_chat_session(session_id)
        if not session_data:
            return None

        content = f"# Chat Session: {session_data.session_name}\n"
        content += f"_Provider: {session_data.llm_provider or 'N/A'}, Model: {session_data.llm_model_name or 'N/A'}_\n"
        content += f"_Session ID: {session_data.id}, Saved: {session_data.updated_at.strftime('%Y-%m-%d %H:%M:%S') if session_data.updated_at else 'N/A'}_\n\n"

        if session_data.originating_prompt_id:
            content += f"Started from Prompt ID: {session_data.originating_prompt_id}\n"
        if session_data.originating_card_id:
            content += f"Started from Card ID: {session_data.originating_card_id}\n"
        content += "---\n\n"

        for msg in sorted(session_data.messages, key=lambda m: m.message_order):
            role_display = msg.role.capitalize()
            if msg.role.lower() == "system":
                content += f"## System Instruction\n\n> {msg.content}\n\n"
            elif msg.role.lower() in ["human", "user"]:
                content += f"### User\n\n{msg.content}\n\n"
            elif msg.role.lower() in ["ai", "assistant"]:
                content += f"### Assistant\n\n{msg.content}\n\n"
            else:
                 content += f"### {role_display}\n\n{msg.content}\n\n"
            content += "---\n\n"

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_session_name = "".join(c for c in session_data.session_name if c.isalnum() or c in (' ', '_', '-')).rstrip()
        filename = f"Chat Session - {safe_session_name} - {timestamp}.md"

        try:
            settings.backup_dir.mkdir(parents=True, exist_ok=True)
            file_path = save_markdown_file(filename, content, directory=settings.backup_dir)
            return file_path
        except Exception as e:
            print(f"Error exporting session to markdown: {e}")
            return None

    # Helper methods for checking dependencies (logical, not DB FKs)
    # These might be useful if strict deletion prevention is desired before attempting a delete.
    def get_sessions_by_originating_prompt(self, prompt_id: int) -> List[ChatSessionData]:
        with get_db(DB_SESSIONS) as db: # MODIFIED
            sessions = db.query(ChatSessionDBModel)\
                .filter(ChatSessionDBModel.originating_prompt_id == prompt_id)\
                .all()
            return [self._db_chat_session_to_pydantic(s, include_messages=False) for s in sessions]

    def get_sessions_by_originating_card(self, card_id: int) -> List[ChatSessionData]:
        with get_db(DB_SESSIONS) as db: # MODIFIED
            sessions = db.query(ChatSessionDBModel)\
                .filter(ChatSessionDBModel.originating_card_id == card_id)\
                .all()
            return [self._db_chat_session_to_pydantic(s, include_messages=False) for s in sessions]
