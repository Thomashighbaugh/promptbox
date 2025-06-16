"""
Defines the SQLAlchemy ORM models for the application's database.
"""
import datetime
from sqlalchemy import (
    create_engine,
    ForeignKey,
    String,
    DateTime,
    Text,
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
    tags: Mapped[str] = mapped_column(String(255), nullable=True)
    folder: Mapped[str] = mapped_column(String(255), nullable=False, default="general")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    chat_logs: Mapped[list["ChatLog"]] = relationship(back_populates="prompt", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Prompt(id={self.id}, name='{self.name}', folder='{self.folder}')>"

class ChatLog(Base):
    __tablename__ = "chat_logs"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    prompt_id: Mapped[int] = mapped_column(ForeignKey("prompts.id"), nullable=False)
    log_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now())
    prompt: Mapped["Prompt"] = relationship(back_populates="chat_logs")

    def __repr__(self):
        return f"<ChatLog(id={self.id}, log_name='{self.log_name}', prompt_id={self.prompt_id})>"
