"""
Defines the SQLAlchemy ORM models for the application's database.
"""
import datetime
from sqlalchemy import (
    ForeignKey,
    String,
    DateTime,
    Text,
    Integer, 
    func
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class Prompt(Base):
    __tablename__ = "prompts"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    system_instruction: Mapped[str] = mapped_column(Text, nullable=True)
    user_instruction: Mapped[str] = mapped_column(Text, nullable=True)
    assistant_instruction: Mapped[str] = mapped_column(Text, nullable=True)
    folder: Mapped[str] = mapped_column(String(255), nullable=False, default="general")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    
    chat_sessions: Mapped[list["ChatSession"]] = relationship(
        back_populates="originating_prompt", 
        cascade="all, delete-orphan",
        foreign_keys="[ChatSession.originating_prompt_id]"
    )

    def __repr__(self):
        return f"<Prompt(id={self.id}, name='{self.name}', folder='{self.folder}')>"

class CharacterCard(Base):
    __tablename__ = "character_cards"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    folder: Mapped[str] = mapped_column(String(255), nullable=False, default="general")
    description: Mapped[str] = mapped_column(Text, nullable=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False, default="character") # "character" or "scenario"
    
    # Replaced 'instructions' with structured instruction fields
    system_instruction: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_instruction: Mapped[str | None] = mapped_column(Text, nullable=True)
    assistant_instruction: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    chat_sessions: Mapped[list["ChatSession"]] = relationship(
        back_populates="originating_card",
        cascade="all, delete-orphan",
        foreign_keys="[ChatSession.originating_card_id]"
    )

    def __repr__(self):
        return f"<CharacterCard(id={self.id}, name='{self.name}', type='{self.type}')>"

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    session_name: Mapped[str] = mapped_column(String(255), nullable=False, default="Chat Session")
    
    llm_provider: Mapped[str] = mapped_column(String(100), nullable=True)
    llm_model_name: Mapped[str] = mapped_column(String(100), nullable=True)
    
    originating_prompt_id: Mapped[int | None] = mapped_column(ForeignKey("prompts.id"), nullable=True)
    originating_card_id: Mapped[int | None] = mapped_column(ForeignKey("character_cards.id"), nullable=True)
    
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    originating_prompt: Mapped["Prompt | None"] = relationship(back_populates="chat_sessions", foreign_keys=[originating_prompt_id])
    originating_card: Mapped["CharacterCard | None"] = relationship(back_populates="chat_sessions", foreign_keys=[originating_card_id])
    messages: Mapped[list["ChatMessage"]] = relationship(back_populates="session", cascade="all, delete-orphan", order_by="ChatMessage.message_order")

    def __repr__(self):
        return f"<ChatSession(id={self.id}, name='{self.session_name}', provider='{self.llm_provider}', model='{self.llm_model_name}')>"

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("chat_sessions.id"), nullable=False)
    
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    message_order: Mapped[int] = mapped_column(Integer, nullable=False) 
    
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now())

    session: Mapped["ChatSession"] = relationship(back_populates="messages")

    def __repr__(self):
        return f"<ChatMessage(id={self.id}, session_id={self.session_id}, role='{self.role}', order={self.message_order})>"









































































































