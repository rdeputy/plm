"""
API Dependencies

Dependency injection for FastAPI routes.
"""

from typing import Generator

from sqlalchemy.orm import Session

from plm.db import SessionLocal


def get_db_session() -> Generator[Session, None, None]:
    """Get database session for request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
