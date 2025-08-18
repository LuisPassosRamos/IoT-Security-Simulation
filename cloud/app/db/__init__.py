"""
Database initialization and connection management
"""

from sqlalchemy import create_engine
from sqlmodel import SQLModel, Session
import os


def get_database_url() -> str:
    """Get database URL from environment"""
    return os.getenv('DATABASE_URL', 'sqlite:///./app.db')


def create_db_engine():
    """Create database engine"""
    database_url = get_database_url()
    
    # For SQLite, ensure the directory exists
    if database_url.startswith('sqlite'):
        db_path = database_url.split(':///', 1)[1]
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
    
    engine = create_engine(
        database_url,
        echo=False,  # Set to True for SQL query logging
        connect_args={"check_same_thread": False} if database_url.startswith('sqlite') else {}
    )
    
    return engine


def init_database(engine):
    """Initialize database tables"""
    SQLModel.metadata.create_all(engine)


def get_session(engine):
    """Get database session"""
    with Session(engine) as session:
        yield session