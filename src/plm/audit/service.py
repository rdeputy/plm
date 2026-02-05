"""
Audit Service

Centralized service for recording and querying audit entries.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import uuid4

from .models import AuditAction, AuditEntry, FieldChange

logger = logging.getLogger(__name__)


class AuditService:
    """
    Service for managing audit trail entries.

    Provides:
    - Recording audit entries for all actions
    - Querying audit history by entity, user, time range
    - Diff detection between old and new values
    """

    def __init__(self):
        # In-memory storage (replace with DB in production)
        self._entries: dict[str, AuditEntry] = {}
        # Index by entity
        self._by_entity: dict[str, list[str]] = {}
        # Index by user
        self._by_user: dict[str, list[str]] = {}

    def log(
        self,
        action: AuditAction,
        entity_type: str,
        entity_id: str,
        user_id: str,
        user_name: str,
        entity_number: Optional[str] = None,
        changes: list[FieldChange] | None = None,
        old_values: dict[str, Any] | None = None,
        new_values: dict[str, Any] | None = None,
        reason: Optional[str] = None,
        change_order_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        user_email: Optional[str] = None,
        user_ip: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditEntry:
        """
        Log an audit entry.

        Args:
            action: The action being performed
            entity_type: Type of entity (part, bom, document, etc.)
            entity_id: Entity ID
            user_id: User performing action
            user_name: User display name
            entity_number: Optional display identifier
            changes: List of field changes (or auto-detect from old/new)
            old_values: Previous state (for auto-diff)
            new_values: New state (for auto-diff)
            reason: User-provided reason
            change_order_id: Linked ECO
            workflow_id: Linked workflow
            user_email: User email
            user_ip: Client IP
            session_id: Session identifier
            metadata: Additional context data

        Returns:
            Created AuditEntry
        """
        # Auto-detect changes if old/new provided
        if changes is None and old_values and new_values:
            changes = self._detect_changes(old_values, new_values)

        entry = AuditEntry(
            id=str(uuid4()),
            timestamp=datetime.now(),
            user_id=user_id,
            user_name=user_name,
            user_email=user_email,
            user_ip=user_ip,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_number=entity_number,
            changes=changes or [],
            reason=reason,
            change_order_id=change_order_id,
            workflow_id=workflow_id,
            session_id=session_id,
            metadata=metadata or {},
        )

        # Store entry
        self._entries[entry.id] = entry

        # Update indexes
        entity_key = f"{entity_type}:{entity_id}"
        if entity_key not in self._by_entity:
            self._by_entity[entity_key] = []
        self._by_entity[entity_key].append(entry.id)

        if user_id not in self._by_user:
            self._by_user[user_id] = []
        self._by_user[user_id].append(entry.id)

        logger.info(f"Audit: {entry.summary}")

        return entry

    def log_create(
        self,
        entity_type: str,
        entity_id: str,
        user_id: str,
        user_name: str,
        entity_number: Optional[str] = None,
        values: dict[str, Any] | None = None,
        **kwargs,
    ) -> AuditEntry:
        """Log a create action."""
        changes = []
        if values:
            changes = [
                FieldChange(field_name=k, old_value=None, new_value=v)
                for k, v in values.items()
                if v is not None
            ]
        return self.log(
            action=AuditAction.CREATE,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            user_name=user_name,
            entity_number=entity_number,
            changes=changes,
            **kwargs,
        )

    def log_update(
        self,
        entity_type: str,
        entity_id: str,
        user_id: str,
        user_name: str,
        old_values: dict[str, Any],
        new_values: dict[str, Any],
        entity_number: Optional[str] = None,
        **kwargs,
    ) -> AuditEntry:
        """Log an update action with automatic change detection."""
        return self.log(
            action=AuditAction.UPDATE,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            user_name=user_name,
            entity_number=entity_number,
            old_values=old_values,
            new_values=new_values,
            **kwargs,
        )

    def log_delete(
        self,
        entity_type: str,
        entity_id: str,
        user_id: str,
        user_name: str,
        entity_number: Optional[str] = None,
        reason: Optional[str] = None,
        **kwargs,
    ) -> AuditEntry:
        """Log a delete action."""
        return self.log(
            action=AuditAction.DELETE,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            user_name=user_name,
            entity_number=entity_number,
            reason=reason,
            **kwargs,
        )

    def log_status_change(
        self,
        action: AuditAction,
        entity_type: str,
        entity_id: str,
        user_id: str,
        user_name: str,
        old_status: str,
        new_status: str,
        entity_number: Optional[str] = None,
        **kwargs,
    ) -> AuditEntry:
        """Log a status/lifecycle change."""
        return self.log(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            user_name=user_name,
            entity_number=entity_number,
            changes=[
                FieldChange(
                    field_name="status",
                    old_value=old_status,
                    new_value=new_status,
                    display_name="Status",
                )
            ],
            **kwargs,
        )

    def get_entry(self, entry_id: str) -> Optional[AuditEntry]:
        """Get an audit entry by ID."""
        return self._entries.get(entry_id)

    def get_entity_history(
        self,
        entity_type: str,
        entity_id: str,
        limit: int = 100,
        offset: int = 0,
        action_filter: list[AuditAction] | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
    ) -> list[AuditEntry]:
        """
        Get audit history for an entity.

        Args:
            entity_type: Entity type
            entity_id: Entity ID
            limit: Max entries to return
            offset: Pagination offset
            action_filter: Filter by action types
            from_date: Start of time range
            to_date: End of time range

        Returns:
            List of AuditEntry sorted by timestamp (newest first)
        """
        entity_key = f"{entity_type}:{entity_id}"
        entry_ids = self._by_entity.get(entity_key, [])

        entries = []
        for eid in entry_ids:
            entry = self._entries.get(eid)
            if not entry:
                continue

            # Apply filters
            if action_filter and entry.action not in action_filter:
                continue
            if from_date and entry.timestamp < from_date:
                continue
            if to_date and entry.timestamp > to_date:
                continue

            entries.append(entry)

        # Sort by timestamp descending
        entries.sort(key=lambda e: e.timestamp, reverse=True)

        return entries[offset:offset + limit]

    def get_user_activity(
        self,
        user_id: str,
        limit: int = 100,
        offset: int = 0,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
    ) -> list[AuditEntry]:
        """Get activity history for a user."""
        entry_ids = self._by_user.get(user_id, [])

        entries = []
        for eid in entry_ids:
            entry = self._entries.get(eid)
            if not entry:
                continue

            if from_date and entry.timestamp < from_date:
                continue
            if to_date and entry.timestamp > to_date:
                continue

            entries.append(entry)

        entries.sort(key=lambda e: e.timestamp, reverse=True)

        return entries[offset:offset + limit]

    def search(
        self,
        entity_type: Optional[str] = None,
        action: Optional[AuditAction] = None,
        user_id: Optional[str] = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        query: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditEntry]:
        """
        Search audit entries with filters.

        Args:
            entity_type: Filter by entity type
            action: Filter by action
            user_id: Filter by user
            from_date: Start of time range
            to_date: End of time range
            query: Text search in summary
            limit: Max results
            offset: Pagination offset

        Returns:
            List of matching AuditEntry
        """
        entries = []

        for entry in self._entries.values():
            # Apply filters
            if entity_type and entry.entity_type != entity_type:
                continue
            if action and entry.action != action:
                continue
            if user_id and entry.user_id != user_id:
                continue
            if from_date and entry.timestamp < from_date:
                continue
            if to_date and entry.timestamp > to_date:
                continue
            if query and query.lower() not in entry.summary.lower():
                continue

            entries.append(entry)

        # Sort by timestamp descending
        entries.sort(key=lambda e: e.timestamp, reverse=True)

        return entries[offset:offset + limit]

    def get_recent_activity(
        self,
        hours: int = 24,
        limit: int = 100,
    ) -> list[AuditEntry]:
        """Get recent activity across all entities."""
        cutoff = datetime.now() - timedelta(hours=hours)

        entries = [
            e for e in self._entries.values()
            if e.timestamp >= cutoff
        ]

        entries.sort(key=lambda e: e.timestamp, reverse=True)

        return entries[:limit]

    def get_statistics(
        self,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
    ) -> dict[str, Any]:
        """Get audit statistics."""
        entries = list(self._entries.values())

        if from_date:
            entries = [e for e in entries if e.timestamp >= from_date]
        if to_date:
            entries = [e for e in entries if e.timestamp <= to_date]

        # Count by action
        by_action: dict[str, int] = {}
        for e in entries:
            by_action[e.action.value] = by_action.get(e.action.value, 0) + 1

        # Count by entity type
        by_entity: dict[str, int] = {}
        for e in entries:
            by_entity[e.entity_type] = by_entity.get(e.entity_type, 0) + 1

        # Count by user
        by_user: dict[str, int] = {}
        for e in entries:
            by_user[e.user_name] = by_user.get(e.user_name, 0) + 1

        return {
            "total_entries": len(entries),
            "by_action": by_action,
            "by_entity_type": by_entity,
            "by_user": dict(sorted(by_user.items(), key=lambda x: x[1], reverse=True)[:10]),
        }

    def _detect_changes(
        self,
        old_values: dict[str, Any],
        new_values: dict[str, Any],
    ) -> list[FieldChange]:
        """Detect changes between old and new values."""
        changes = []

        all_keys = set(old_values.keys()) | set(new_values.keys())

        for key in all_keys:
            old_val = old_values.get(key)
            new_val = new_values.get(key)

            if old_val != new_val:
                changes.append(FieldChange(
                    field_name=key,
                    old_value=old_val,
                    new_value=new_val,
                ))

        return changes


# Singleton instance
_service: Optional[AuditService] = None


def get_audit_service() -> AuditService:
    """Get the singleton audit service instance."""
    global _service
    if _service is None:
        _service = AuditService()
    return _service
