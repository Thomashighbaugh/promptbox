"""
Handles loading application-wide configuration settings.
Now supports multiple database files.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

_APP_HOME_DIR_NAME = ".promptbox"

class Settings:
    def __init__(self):
        self.APP_HOME: Path = Path.home() / _APP_HOME_DIR_NAME

        # --- API Keys ---
        self.mistral_api_key: str | None = os.getenv("MISTRAL_API_KEY")
        self.groq_api_key: str | None = os.getenv("GROQ_API_KEY")
        self.google_api_key: str | None = os.getenv("GOOGLE_API_KEY")
        self.cerebras_api_key: str | None = os.getenv("CEREBRAS_API_KEY")
        self.novita_api_key: str | None = os.getenv("NOVITA_API_KEY")

        # --- API Endpoints ---
        self.ollama_api_base: str = os.getenv("OLLAMA_API_BASE") or "http://127.0.0.1:11434"

        # --- Application Data Directories ---
        self.data_dir: Path = self.APP_HOME / "data"
        self.backup_dir: Path = self.APP_HOME / "backups"

        # --- Database Paths ---
        # Prompts Database
        prompts_db_env = os.getenv("PROMPTS_DATABASE_PATH")
        if prompts_db_env and Path(prompts_db_env).is_absolute():
            self.prompts_database_path: Path = Path(prompts_db_env)
        elif prompts_db_env:
            self.prompts_database_path: Path = self.APP_HOME / prompts_db_env # Relative to APP_HOME
        else:
            self.prompts_database_path: Path = self.data_dir / "prompts.db"

        # Character Cards Database
        cards_db_env = os.getenv("CARDS_DATABASE_PATH")
        if cards_db_env and Path(cards_db_env).is_absolute():
            self.cards_database_path: Path = Path(cards_db_env)
        elif cards_db_env:
            self.cards_database_path: Path = self.APP_HOME / cards_db_env
        else:
            self.cards_database_path: Path = self.data_dir / "character_cards.db"

        # Chat Sessions Database
        sessions_db_env = os.getenv("SESSIONS_DATABASE_PATH")
        if sessions_db_env and Path(sessions_db_env).is_absolute():
            self.sessions_database_path: Path = Path(sessions_db_env)
        elif sessions_db_env:
            self.sessions_database_path: Path = self.APP_HOME / sessions_db_env
        else:
            self.sessions_database_path: Path = self.data_dir / "chat_sessions.db"
            
        self._create_directories()

    def _create_directories(self):
        self.APP_HOME.mkdir(exist_ok=True, parents=True)
        self.data_dir.mkdir(exist_ok=True, parents=True)
        self.backup_dir.mkdir(exist_ok=True, parents=True)
        
        self.prompts_database_path.parent.mkdir(exist_ok=True, parents=True)
        self.cards_database_path.parent.mkdir(exist_ok=True, parents=True)
        self.sessions_database_path.parent.mkdir(exist_ok=True, parents=True)

    def get_api_key(self, provider: str) -> str | None:
        return getattr(self, f"{provider.lower()}_api_key", None)

settings = Settings()
