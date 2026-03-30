"""
Database Setup for pyPortMan Backend
SQLite database configuration using SQLAlchemy
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database URL from environment or default to SQLite
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./pyportman.db"
)

# Create engine with SQLite-specific settings
# StaticPool is used for SQLite to handle multiple threads
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False  # Set to True for SQL query logging
    )
else:
    engine = create_engine(DATABASE_URL, echo=False)

# Create SessionLocal class for database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """
    Dependency for FastAPI to get database session
    Usage: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database by creating all tables
    Call this on application startup
    """
    from models import Base
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")


def reset_db():
    """
    Drop all tables and recreate them
    WARNING: This will delete all data!
    """
    from models import Base
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("Database reset successfully!")


if __name__ == "__main__":
    # Test database connection
    init_db()
    print("Database connection test successful!")
