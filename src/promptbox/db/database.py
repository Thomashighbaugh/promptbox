"""
Manages the database connection and session creation.
"""
import streamlit as st
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from promptbox.core.config import settings
from promptbox.db.models import Base

# Use a module-level variable to hold the engine once initialized.
_engine = None
SessionLocal = None

def init_engine():
    """Initializes the database engine. Returns True on success, False on failure."""
    global _engine, SessionLocal
    if _engine is not None:
        return True
    
    try:
        _engine = create_engine(
            f"sqlite:///{settings.database_path}",
            connect_args={"check_same_thread": False},
            echo=False
        )
        # Verify connection
        _engine.connect().close()

        SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=_engine
        )
        return True
    except Exception as e:
        st.error(f"Fatal Error: Could not create database engine at {settings.database_path}.")
        st.error(f"Details: {e}")
        st.info("Please ensure the directory is writable and the path is correct.")
        return False


def create_db_and_tables():
    """
    Creates the database file and all tables defined in the Base metadata.
    """
    if not _engine:
        st.error("Database engine not initialized. Cannot create tables.")
        return
        
    try:
        Base.metadata.create_all(bind=_engine)
    except Exception as e:
        st.error(f"An error occurred during database and table creation: {e}")

@contextmanager
def get_db() -> Session:
    """
    Provides a database session within a context manager.
    """
    if not SessionLocal:
        raise RuntimeError("Database session not initialized. Call init_engine() first.")
        
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
