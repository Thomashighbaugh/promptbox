"""
Manages the database connection and session creation.
"""
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from promptbox.core.config import settings
from promptbox.db.models import Base

try:
    engine = create_engine(
        f"sqlite:///{settings.database_path}",
        connect_args={"check_same_thread": False},
        echo=False
    )
except Exception as e:
    print(f"Error creating database engine: {e}")
    exit(1)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

def create_db_and_tables():
    """
    Creates the database file and all tables defined in the Base metadata.
    """
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"An error occurred during database and table creation: {e}")
        exit(1)

@contextmanager
def get_db() -> Session:
    """
    Provides a database session within a context manager.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
