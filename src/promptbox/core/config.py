"""
Handles loading application-wide configuration settings.

This version uses two locations:
1.  The Current Working Directory (CWD) for user-provided files like .env.
    This allows the user to place their API keys in their project folder.
2.  A dedicated folder in the user's home directory (~/.promptbox) for stable
    application data like the database. This ensures the database is always
    found, regardless of where the command is run.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# By default, python-dotenv searches for the .env file in the current working
# directory. This is the correct behavior for a command-line tool, as it
# allows the user to manage API keys in their project folder.
load_dotenv()

# Renamed the module-level constant to avoid confusion with the instance attribute.
_APP_HOME_DIR_NAME = ".promptbox"

class Settings:
    """
    A singleton-like class to hold all application settings.
    Attributes are loaded from environment variables.
    """
    def __init__(self):
        # --- Application's root directory in user's home ---
        # This is now an instance attribute, directly accessible via settings.APP_HOME
        self.APP_HOME: Path = Path.home() / _APP_HOME_DIR_NAME

        # --- API Keys (loaded by load_dotenv() from the CWD) ---
        self.mistral_api_key: str | None = os.getenv("MISTRAL_API_KEY")
        self.groq_api_key: str | None = os.getenv("GROQ_API_KEY")
        self.google_api_key: str | None = os.getenv("GOOGLE_API_KEY")
        self.cerebras_api_key: str | None = os.getenv("CEREBRAS_API_KEY")
        self.novita_api_key: str | None = os.getenv("NOVITA_API_KEY")

        # --- API Endpoints ---
        self.ollama_api_base: str = os.getenv("OLLAMA_API_BASE") or "http://127.0.0.1:11434"

        # --- Default File Paths (now relative to self.APP_HOME) ---
        self.data_dir: Path = self.APP_HOME / "data"
        self.backup_dir: Path = self.APP_HOME / "backups"

        # --- Overridable Paths ---
        # The database now lives in a predictable location.
        # Ensure DATABASE_PATH from .env is resolved correctly if it's an absolute path.
        db_path_env = os.getenv("DATABASE_PATH")
        if db_path_env and Path(db_path_env).is_absolute():
            self.database_path: Path = Path(db_path_env)
        elif db_path_env: # Relative path, assumed relative to CWD or requires specific handling
             # For simplicity, if DATABASE_PATH is relative, let's make it relative to APP_HOME
            self.database_path: Path = self.APP_HOME / db_path_env
        else: # Default path
            self.database_path: Path = self.data_dir / "promptbox.db"


        # Ensure data directories exist in the user's home folder
        self._create_directories()

    def _create_directories(self):
        """
        Creates the necessary data and backup directories if they don't exist.
        """
        # Ensure APP_HOME itself is created first as it's the parent for data_dir
        self.APP_HOME.mkdir(exist_ok=True, parents=True)
        self.data_dir.mkdir(exist_ok=True, parents=True)
        self.backup_dir.mkdir(exist_ok=True, parents=True)
        # Ensure the parent directory for the database_path also exists
        self.database_path.parent.mkdir(exist_ok=True, parents=True)


    def get_api_key(self, provider: str) -> str | None:
        """A helper method to get an API key by its provider name."""
        return getattr(self, f"{provider.lower()}_api_key", None)

# Instantiate a single settings object for the entire application to use.
settings = Settings()
