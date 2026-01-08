"""
Database configuration and connection management
"""
import os
from sqlmodel import create_engine, SQLModel, Session

# Get DATABASE_URL from environment or use local default
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./expenses.db")

# SQLite-specific configuration
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL query logging
    connect_args=connect_args
)


def create_db_and_tables():
    """Create all database tables"""
    SQLModel.metadata.create_all(engine)


def get_session():
    """Dependency for FastAPI to get DB session"""
    with Session(engine) as session:
        yield session

