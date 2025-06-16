"""
Defines the Pydantic data models for the application.

These models are used for data validation, serialization, and ensuring
a consistent data structure is passed between different layers of the
application (e.g., from the service layer to the TUI). They are distinct
from the SQLAlchemy ORM models, which are tied to the database schema.
"""

from datetime import datetime
from pydantic import BaseModel, Field, model_validator, ConfigDict

class PromptData(BaseModel):
    """
    Pydantic model representing a prompt. Used for data validation and transfer.
    """
    # Configuration to allow creating this model from ORM objects (e.g., SQLAlchemy models)
    model_config = ConfigDict(from_attributes=True)

    # Optional fields that are present on existing prompts
    id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    # Core required fields
    name: str = Field(..., min_length=1, description="The unique name of the prompt.")
    folder: str = Field(default="general", min_length=1, description="The folder to categorize the prompt.")
    
    # Optional metadata
    description: str | None = None
    tags: list[str] = Field(default_factory=list, description="A list of tags for searching.")

    # Prompt content. At least one of these must be provided.
    system_instruction: str | None = None
    user_instruction: str | None = None
    assistant_instruction: str | None = None
    
    @model_validator(mode='after')
    def check_at_least_one_instruction(self) -> 'PromptData':
        """
        Validates that at least one of the instruction fields is not None.
        """
        if not any([
            self.system_instruction,
            self.user_instruction,
            self.assistant_instruction,
        ]):
            raise ValueError("At least one instruction (system, user, or assistant) must be provided.")
        return self

if __name__ == '__main__':
    # Example usage and demonstration of the Pydantic model
    
    print("--- Testing valid prompt data ---")
    try:
        valid_data = {
            "name": "My Test Prompt",
            "description": "A prompt for testing.",
            "user_instruction": "Please act as a pirate.",
            "tags": ["testing", "fun"],
            "folder": "experiments"
        }
        prompt_model = PromptData(**valid_data)
        print("Validation successful!")
        print(prompt_model.model_dump_json(indent=2))
    except ValueError as e:
        print(f"Validation failed unexpectedly: {e}")

    print("\n--- Testing invalid prompt data (no instructions) ---")
    try:
        invalid_data = {
            "name": "Invalid Prompt",
            "description": "This should fail validation."
        }
        PromptData(**invalid_data)
    except ValueError as e:
        print(f"Validation failed as expected: {e}")

    print("\n--- Creating model from a mock ORM object ---")
    class MockOrmPrompt:
        """A fake SQLAlchemy model object to test `from_attributes`."""
        id = 1
        name = "ORM Prompt"
        description = "Loaded from a DB-like object"
        folder = "orm_tests"
        system_instruction = "System info"
        user_instruction = "User info"
        assistant_instruction = None
        # In the DB, tags are a string; we'll handle this conversion in the service layer
        tags = "orm, test" 
        created_at = datetime.now()
        updated_at = datetime.now()

    mock_orm_obj = MockOrmPrompt()
    # Note: A real implementation would need to convert the 'tags' string to a list
    # before creating the Pydantic model. This is just a demonstration.
    # We will pretend the service layer did this:
    mock_orm_dict = {
        "id": mock_orm_obj.id,
        "name": mock_orm_obj.name,
        "description": mock_orm_obj.description,
        "folder": mock_orm_obj.folder,
        "system_instruction": mock_orm_obj.system_instruction,
        "user_instruction": mock_orm_obj.user_instruction,
        "tags": mock_orm_obj.tags.split(", "),
        "created_at": mock_orm_obj.created_at,
        "updated_at": mock_orm_obj.updated_at,
    }
    orm_based_prompt = PromptData(**mock_orm_dict)
    
    print("Successfully created Pydantic model from ORM-like data:")
    print(orm_based_prompt.model_dump_json(indent=2))

