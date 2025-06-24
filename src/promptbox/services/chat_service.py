"""
Service layer for handling business logic related to Chat Sessions and Messages.
"""
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import joinedload # To eager load messages with sessions
from promptbox.db.database import get_db, Session
from promptbox.db.models import ChatSession as ChatSessionDBModel, ChatMessage as ChatMessageDBModel
from promptbox.models.data_models import ChatSessionData, ChatMessageData
from promptbox.core.config import settings # For markdown export path


class ChatService:

    def _db_chat_message_to_pydantic(self, msg: ChatMessageDBModel) -> ChatMessageData:
        return ChatMessageData.model_validate(msg)

    def _db_chat_session_to_pydantic(self, session: ChatSessionDBModel, include_messages: bool = True) -> ChatSessionData:
        messages = []
        if include_messages and session.messages:
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
        with get_db() as db:
            new_session_db = ChatSessionDBModel(
                session_name=session_data.session_name,
                llm_provider=session_data.llm_provider,
                llm_model_name=session_data.llm_model_name,
                originating_prompt_id=session_data.originating_prompt_id,
                originating_card_id=session_data.originating_card_id
                # created_at and updated_at are handled by the model defaults
            )
            db.add(new_session_db)
            db.commit()
            db.refresh(new_session_db)

            # If there are initial messages in session_data, save them too
            if session_data.messages:
                for order, msg_data in enumerate(session_data.messages):
                    new_msg_db = ChatMessageDBModel(
                        session_id=new_session_db.id,
                        role=msg_data.role,
                        content=msg_data.content,
                        message_order=order # Or use msg_data.message_order if provided
                    )
                    db.add(new_msg_db)
                db.commit()
                db.refresh(new_session_db) # Refresh again to load messages relationship

            return self._db_chat_session_to_pydantic(new_session_db, include_messages=True)

    def add_message_to_session(self, session_id: int, message_data: ChatMessageData, db: Optional[Session] = None) -> ChatMessageData | None:
        """Adds a single message to an existing session. Can use an existing db session."""
        def _add_message(s: Session):
            session = s.query(ChatSessionDBModel).filter(ChatSessionDBModel.id == session_id).first()
            if not session:
                return None

            new_message = ChatMessageDBModel(
                session_id=session_id,
                role=message_data.role,
                content=message_data.content,
                message_order=message_data.message_order
            )
            s.add(new_message)
            s.commit()
            s.refresh(new_message)
            return self._db_chat_message_to_pydantic(new_message)

        if db:
            return _add_message(db)
        else:
            with get_db() as new_db:
                return _add_message(new_db)

    def save_chat_messages(self, session_id: int, messages: List[ChatMessageData]) -> List[ChatMessageData]:
        """Saves a list of messages for a session, replacing existing messages if orders conflict, or appending."""
        # This implementation will clear existing messages and add new ones to ensure order integrity.
        # A more complex merge strategy could be implemented if needed.
        with get_db() as db:
            # Delete existing messages for this session
            db.query(ChatMessageDBModel).filter(ChatMessageDBModel.session_id == session_id).delete()
            
            saved_messages_pydantic = []
            for msg_data in messages:
                new_message_db = ChatMessageDBModel(
                    session_id=session_id,
                    role=msg_data.role,
                    content=msg_data.content,
                    message_order=msg_data.message_order
                )
                db.add(new_message_db)
                # We can't refresh here until commit, so build pydantic models after loop
            db.commit()

            # Retrieve newly saved messages to get their IDs and timestamps
            newly_saved_db_messages = db.query(ChatMessageDBModel)\
                .filter(ChatMessageDBModel.session_id == session_id)\
                .order_by(ChatMessageDBModel.message_order)\
                .all()
            return [self._db_chat_message_to_pydantic(msg) for msg in newly_saved_db_messages]


    def get_chat_session(self, session_id: int) -> ChatSessionData | None:
        with get_db() as db:
            session = db.query(ChatSessionDBModel)\
                .options(joinedload(ChatSessionDBModel.messages))\
                .filter(ChatSessionDBModel.id == session_id)\
                .first()
            return self._db_chat_session_to_pydantic(session, include_messages=True) if session else None

    def get_all_chat_sessions(self) -> List[ChatSessionData]:
        with get_db() as db:
            sessions = db.query(ChatSessionDBModel)\
                .order_by(ChatSessionDBModel.updated_at.desc())\
                .all() # Messages are not loaded by default for performance
            return [self._db_chat_session_to_pydantic(s, include_messages=False) for s in sessions]

    def delete_chat_session(self, session_id: int) -> bool:
        with get_db() as db:
            session = db.query(ChatSessionDBModel).filter(ChatSessionDBModel.id == session_id).first()
            if session:
                db.delete(session) # Messages are deleted due to cascade
                db.commit()
                return True
            return False
            
    def update_chat_session_metadata(self, session_id: int, session_name: Optional[str] = None, llm_provider: Optional[str] = None, llm_model_name: Optional[str] = None) -> ChatSessionData | None:
        with get_db() as db:
            session = db.query(ChatSessionDBModel).filter(ChatSessionDBModel.id == session_id).first()
            if not session:
                return None
            
            if session_name is not None:
                session.session_name = session_name
            if llm_provider is not None:
                session.llm_provider = llm_provider
            if llm_model_name is not None:
                session.llm_model_name = llm_model_name
            
            session.updated_at = datetime.utcnow() # Manually update timestamp
            db.commit()
            db.refresh(session)
            return self._db_chat_session_to_pydantic(session, include_messages=False) # Only metadata changed

    def export_session_to_markdown(self, session_id: int) -> str | None:
        from promptbox.utils.file_handler import save_markdown_file # Local import to avoid circular dependency if utils need services
        
        session_data = self.get_chat_session(session_id) # This will include messages
        if not session_data:
            return None

        content = f"# Chat Session: {session_data.session_name}\n"
        content += f"_Provider: {session_data.llm_provider}, Model: {session_data.llm_model_name}_\n"
        content += f"_Session ID: {session_data.id}, Saved: {session_data.updated_at.strftime('%Y-%m-%d %H:%M:%S')}_\n\n"

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
            elif msg.role.lower() == "ai" or msg.role.lower() == "assistant": # Common variations
                content += f"### Assistant\n\n{msg.content}\n\n"
            else: # Fallback for other roles
                 content += f"### {role_display}\n\n{msg.content}\n\n"
            content += "---\n\n"
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_session_name = "".join(c for c in session_data.session_name if c.isalnum() or c in (' ', '_', '-')).rstrip()
        filename = f"Chat Session - {safe_session_name} - {timestamp}.md"
        
        try:
            # Ensure backup_dir exists (it should be created by config.py, but good to be safe)
            settings.backup_dir.mkdir(parents=True, exist_ok=True)
            file_path = save_markdown_file(filename, content, directory=settings.backup_dir)
            return file_path
        except Exception as e:
            # Consider logging this error
            print(f"Error exporting session to markdown: {e}")
            return None
