"""
Database Base Configuration

SQLAlchemy base, engine, and session setup.
"""

import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all models."""

    pass


# Database URL from environment or default to SQLite
DATABASE_URL = os.getenv(
    "PLM_DATABASE_URL",
    "sqlite:///./plm.db",
)

# Create engine
# For SQLite, need check_same_thread=False for FastAPI
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=os.getenv("PLM_DB_ECHO", "false").lower() == "true",
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for FastAPI to get a database session.

    Usage:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.

    Usage:
        with get_session() as session:
            session.query(Part).all()
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    """
    Initialize database tables.

    Call this on startup to ensure all tables exist.
    """
    Base.metadata.create_all(bind=engine)


def drop_db() -> None:
    """
    Drop all database tables.

    WARNING: This destroys all data!
    """
    Base.metadata.drop_all(bind=engine)
