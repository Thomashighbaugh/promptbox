"""
Defines the SQLAlchemy ORM models for the application's database.
Models are now separated into different Bases with their own MetaData
to support multiple database files.
"""
import datetime
from sqlalchemy import (
    ForeignKey,
    String,
    DateTime,
    Text,
    Integer,
    func,
    MetaData
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# --- Metadata and Base for Prompts Database ---
prompts_metadata = MetaData()
class PromptsBase(DeclarativeBase):
    metadata = prompts_metadata

# --- Metadata and Base for Character Cards Database ---
cards_metadata = MetaData()
class CardsBase(DeclarativeBase):
    metadata = cards_metadata

# --- Metadata and Base for Chat Sessions Database ---
sessions_metadata = MetaData()
class SessionsBase(DeclarativeBase):
    metadata = sessions_metadata


class Prompt(PromptsBase):
    __tablename__ = "prompts"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    system_instruction: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_instruction: Mapped[str | None] = mapped_column(Text, nullable=True)
    assistant_instruction: Mapped[str | None] = mapped_column(Text, nullable=True)
    folder: Mapped[str] = mapped_column(String(255), nullable=False, default="general")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    # REMOVED: chat_sessions relationship (cross-database)

    def __repr__(self):
        return f"<Prompt(id={self.id}, name='{self.name}', folder='{self.folder}')>"

class CharacterCard(CardsBase):
    __tablename__ = "character_cards"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    folder: Mapped[str] = mapped_column(String(255), nullable=False, default="general")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False, default="character") # "character" or "scenario"

    system_instruction: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_instruction: Mapped[str | None] = mapped_column(Text, nullable=True)
    assistant_instruction: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    # REMOVED: chat_sessions relationship (cross-database)

    def __repr__(self):
        return f"<CharacterCard(id={self.id}, name='{self.name}', type='{self.type}')>"

class ChatSession(SessionsBase):
    __tablename__ = "chat_sessions"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    session_name: Mapped[str] = mapped_column(String(255), nullable=False, default="Chat Session")

    llm_provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    llm_model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # MODIFIED: Removed ForeignKey constraints as these IDs now point to tables in different DB files
    originating_prompt_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    originating_card_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    # REMOVED: originating_prompt and originating_card relationships (cross-database)

    # This relationship is within the same database (sessions.db), so it remains.
    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.message_order"
    )

    def __repr__(self):
        return f"<ChatSession(id={self.id}, name='{self.session_name}', provider='{self.llm_provider}', model='{self.llm_model_name}')>"

class ChatMessage(SessionsBase):
    __tablename__ = "chat_messages"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("chat_sessions.id"), nullable=False) # FK to local chat_sessions table

    role: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    message_order: Mapped[int] = mapped_column(Integer, nullable=False)

    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now())

    # This relationship is within the same database (sessions.db), so it remains.
    session: Mapped["ChatSession"] = relationship(back_populates="messages")

    def __repr__(self):
        return f"<ChatMessage(id={self.id}, session_id={self.session_id}, role='{self.role}', order={self.message_order})>"

