"""
Manages database connections and session creation for multiple databases.
(Formerly data_models.py in the same directory, renamed for clarity)
"""
import streamlit as st # type: ignore
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Table # type: ignore
from sqlalchemy.orm import relationship # type: ignore
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session as SQLAlchemySession # Renamed to avoid conflict with typing.Session
from typing import Dict, Literal

from promptbox.core.config import settings
from promptbox.db.models import prompts_metadata, cards_metadata, sessions_metadata # MODIFIED IMPORT

_engines: Dict[str, any] = {}
_session_locals: Dict[str, sessionmaker] = {}

DB_PROMPTS = "prompts"
DB_CARDS = "cards"
DB_SESSIONS = "sessions"

DATABASE_CONFIG: Dict[str, Dict[str, any]] = {
    DB_PROMPTS: {
        "path": settings.prompts_database_path,
        "metadata_ref": prompts_metadata # MODIFIED: Directly assigned
    },
    DB_CARDS: {
        "path": settings.cards_database_path,
        "metadata_ref": cards_metadata # MODIFIED: Directly assigned
    },
    DB_SESSIONS: {
        "path": settings.sessions_database_path,
        "metadata_ref": sessions_metadata # MODIFIED: Directly assigned
    }
}

def init_all_engines() -> bool:
    """Initializes all configured database engines. Returns True if all succeed."""
    global _engines, _session_locals

    all_success = True
    if not _engines: # Initialize only if not already done
        for db_key, config in DATABASE_CONFIG.items():
            try:
                engine = create_engine(
                    f"sqlite:///{config['path']}",
                    connect_args={"check_same_thread": False},
                    echo=False
                )
                # Test connection
                with engine.connect():
                    pass # Connection successful

                _engines[db_key] = engine
                _session_locals[db_key] = sessionmaker(
                    autocommit=False,
                    autoflush=False,
                    bind=engine
                )
                print(f"Database engine for '{db_key}' initialized at {config['path']}")
            except Exception as e:
                st.error(f"Fatal Error: Could not create database engine for '{db_key}' at {config['path']}.")
                st.error(f"Details: {e}")
                st.info("Please ensure the directory is writable and the path is correct in your .env or config.")
                all_success = False
    elif len(_engines) != len(DATABASE_CONFIG): # Check if some engines were missed previously
        # This case is less likely if the first init loop runs fully, but as a safeguard.
        st.warning("Engines were partially initialized. Attempting to initialize remaining engines.")
        # Logic to initialize only missing engines could be added here if necessary.
        # For now, we assume if _engines is populated, it was a full attempt.
        # If all_success was false previously, it will remain false.
        pass # Or re-attempt initialization for missing ones.

    return all_success if _engines and len(_engines) == len(DATABASE_CONFIG) else False

# REMOVED set_metadata_for_db function

def create_tables_for_engine(db_key: Literal["prompts", "cards", "sessions"]):
    """Creates tables for a specific database engine using its registered metadata."""
    if db_key not in _engines:
        st.error(f"Database engine for '{db_key}' not initialized. Cannot create tables.")
        return

    metadata = DATABASE_CONFIG[db_key].get("metadata_ref")
    if not metadata:
        # This condition should ideally not be met if DATABASE_CONFIG is correctly populated.
        st.error(f"Metadata for '{db_key}' database not found in configuration. Tables cannot be created.")
        return

    try:
        engine = _engines[db_key]
        metadata.create_all(bind=engine)
        print(f"Tables for '{db_key}' database checked/created successfully.")
    except Exception as e:
        st.error(f"An error occurred during table creation for '{db_key}': {e}")
        # st.exception(e) # For more detailed traceback if needed

def create_all_db_and_tables():
    """
    Calls create_tables_for_engine for all configured databases.
    Ensure this is called *after* models are imported and metadata is set,
    and after engines are initialized.
    """
    if not _engines: # Ensure engines are initialized before trying to create tables
        st.warning("Engines not yet initialized. Attempting initialization before creating tables.")
        if not init_all_engines():
            st.error("Engine initialization failed. Cannot proceed to create tables.")
            return

    for db_key in DATABASE_CONFIG.keys():
        create_tables_for_engine(db_key)

@contextmanager
def get_db(db_key: Literal["prompts", "cards", "sessions"]) -> SQLAlchemySession:
    """
    Provides a database session for the specified database within a context manager.
    """
    if not _session_locals or db_key not in _session_locals:
        # Attempt to initialize if not already done.
        st.warning(f"Session factory for '{db_key}' not found. Attempting to initialize engines...")
        if not init_all_engines():
             raise RuntimeError(f"Database session for '{db_key}' not initialized and auto-init failed. Check logs for engine errors.")
        if db_key not in _session_locals: # Check again after attempt
            raise RuntimeError(f"Database session for '{db_key}' still not initialized after attempt. Critical error.")

    session_local_instance = _session_locals[db_key]
    db = session_local_instance()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
