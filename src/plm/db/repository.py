"""
Base Repository Pattern

Generic repository base class for database operations.
"""

from __future__ import annotations

from typing import Generic, TypeVar, Optional, Type, List
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from .base import Base

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    """Generic repository for CRUD operations."""

    def __init__(self, session: Session, model_class: Type[T]):
        self.session = session
        self.model_class = model_class

    def get(self, id: str) -> Optional[T]:
        """Get entity by ID."""
        return self.session.get(self.model_class, id)

    def get_by(self, **filters) -> Optional[T]:
        """Get single entity by filters."""
        stmt = select(self.model_class).filter_by(**filters)
        return self.session.execute(stmt).scalar_one_or_none()

    def list(
        self,
        limit: int = 100,
        offset: int = 0,
        order_by: Optional[str] = None,
        **filters,
    ) -> list[T]:
        """List entities with optional filters."""
        stmt = select(self.model_class)

        for key, value in filters.items():
            if value is not None and hasattr(self.model_class, key):
                stmt = stmt.filter(getattr(self.model_class, key) == value)

        if order_by and hasattr(self.model_class, order_by):
            stmt = stmt.order_by(getattr(self.model_class, order_by))

        stmt = stmt.offset(offset).limit(limit)
        return list(self.session.execute(stmt).scalars().all())

    def search(
        self,
        search_term: str,
        search_fields: list[str],
        limit: int = 100,
        **filters,
    ) -> list[T]:
        """Search entities by term in specified fields."""
        stmt = select(self.model_class)

        # Apply filters
        for key, value in filters.items():
            if value is not None and hasattr(self.model_class, key):
                stmt = stmt.filter(getattr(self.model_class, key) == value)

        # Apply search
        if search_term and search_fields:
            from sqlalchemy import or_

            search_conditions = []
            term = f"%{search_term}%"
            for field in search_fields:
                if hasattr(self.model_class, field):
                    search_conditions.append(
                        getattr(self.model_class, field).ilike(term)
                    )
            if search_conditions:
                stmt = stmt.filter(or_(*search_conditions))

        return list(self.session.execute(stmt.limit(limit)).scalars().all())

    def create(self, **data) -> T:
        """Create a new entity."""
        if "id" not in data:
            data["id"] = str(uuid4())

        entity = self.model_class(**data)
        self.session.add(entity)
        self.session.flush()
        return entity

    def update(self, id: str, **data) -> Optional[T]:
        """Update an entity."""
        entity = self.get(id)
        if not entity:
            return None

        for key, value in data.items():
            if value is not None and hasattr(entity, key):
                setattr(entity, key, value)

        self.session.flush()
        return entity

    def delete(self, id: str) -> bool:
        """Delete an entity."""
        entity = self.get(id)
        if not entity:
            return False

        self.session.delete(entity)
        self.session.flush()
        return True

    def commit(self):
        """Commit the transaction."""
        self.session.commit()

    def rollback(self):
        """Rollback the transaction."""
        self.session.rollback()
