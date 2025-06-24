"""
Defines the Pydantic data models for the application.

These models are used for data validation, serialization, and ensuring
a consistent data structure is passed between different layers of the
application (e.g., from the service layer to the UI). They are distinct
from the SQLAlchemy ORM models, which are tied to the database schema.
"""

from datetime import datetime
from pydantic import BaseModel, Field, model_validator, ConfigDict
from typing import Literal, List, Optional # Changed from list to List for older Python compatibility if needed, but current is >=3.11

class PromptData(BaseModel):
    """
    Pydantic model representing a prompt. Used for data validation and transfer.
    """
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None # Switched to Optional for consistency
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    name: str = Field(..., min_length=1, description="The unique name of the prompt.")
    folder: str = Field(default="general", min_length=1, description="The folder to categorize the prompt.")
    description: Optional[str] = None
    # The 'tags' field has been removed as per the refactoring plan.
    system_instruction: Optional[str] = None
    user_instruction: Optional[str] = None
    assistant_instruction: Optional[str] = None

    @model_validator(mode='after')
    def check_at_least_one_instruction(self) -> 'PromptData':
        if not any([
            self.system_instruction,
            self.user_instruction,
            self.assistant_instruction,
        ]):
            raise ValueError("At least one instruction (system, user, or assistant) must be provided.")
        return self

class CharacterCardData(BaseModel):
    """
    Pydantic model representing a character or scenario card.
    """
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    name: str = Field(..., min_length=1, description="The unique name of the character/scenario.")
    folder: str = Field(default="general", min_length=1, description="The folder to categorize the card.")
    description: Optional[str] = None
    type: Literal["character", "scenario"] = Field(default="character", description="The type of the card.")
    instructions: str = Field(..., min_length=1, description="The instructions for the AI.")


class ChatMessageData(BaseModel):
    """
    Pydantic model representing a single message within a chat session.
    """
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    session_id: int # A message must belong to a session
    role: Literal["system", "user", "assistant", "human"] # Added human for Langchain compatibility if needed.
    content: str
    message_order: int
    timestamp: Optional[datetime] = None

class ChatSessionData(BaseModel):
    """
    Pydantic model representing a chat session.
    """
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    session_name: str = Field(default="Chat Session")
    llm_provider: Optional[str] = None
    llm_model_name: Optional[str] = None
    originating_prompt_id: Optional[int] = None
    originating_card_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    messages: List[ChatMessageData] = Field(default_factory=list)
