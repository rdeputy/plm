"""
Audit Trail API Router

Endpoints for querying audit history.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from ...audit import AuditAction, get_audit_service

router = APIRouter()


# =============================================================================
# Pydantic Schemas
# =============================================================================


class FieldChangeResponse(BaseModel):
    """Field change in audit entry."""
    field: str
    display_name: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None


class AuditEntryResponse(BaseModel):
    """Audit entry response."""
    id: str
    timestamp: str
    user_id: str
    user_name: str
    action: str
    entity_type: str
    entity_id: str
    entity_number: Optional[str] = None
    summary: str
    changes: list[FieldChangeResponse] = Field(default_factory=list)
    reason: Optional[str] = None
    change_order_id: Optional[str] = None
    workflow_id: Optional[str] = None


class AuditStatsResponse(BaseModel):
    """Audit statistics response."""
    total_entries: int
    by_action: dict[str, int]
    by_entity_type: dict[str, int]
    by_user: dict[str, int]


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/entity/{entity_type}/{entity_id}", response_model=list[AuditEntryResponse])
async def get_entity_history(
    entity_type: str,
    entity_id: str,
    limit: int = Query(100, le=500),
    offset: int = 0,
    action: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
):
    """Get audit history for a specific entity."""
    service = get_audit_service()

    action_filter = None
    if action:
        try:
            action_filter = [AuditAction(action)]
        except ValueError:
            pass

    entries = service.get_entity_history(
        entity_type=entity_type,
        entity_id=entity_id,
        limit=limit,
        offset=offset,
        action_filter=action_filter,
        from_date=from_date,
        to_date=to_date,
    )

    return [_entry_to_response(e) for e in entries]


@router.get("/user/{user_id}", response_model=list[AuditEntryResponse])
async def get_user_activity(
    user_id: str,
    limit: int = Query(100, le=500),
    offset: int = 0,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
):
    """Get activity history for a user."""
    service = get_audit_service()

    entries = service.get_user_activity(
        user_id=user_id,
        limit=limit,
        offset=offset,
        from_date=from_date,
        to_date=to_date,
    )

    return [_entry_to_response(e) for e in entries]


@router.get("/search", response_model=list[AuditEntryResponse])
async def search_audit(
    entity_type: Optional[str] = None,
    action: Optional[str] = None,
    user_id: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    query: Optional[str] = None,
    limit: int = Query(100, le=500),
    offset: int = 0,
):
    """Search audit entries with filters."""
    service = get_audit_service()

    action_enum = None
    if action:
        try:
            action_enum = AuditAction(action)
        except ValueError:
            pass

    entries = service.search(
        entity_type=entity_type,
        action=action_enum,
        user_id=user_id,
        from_date=from_date,
        to_date=to_date,
        query=query,
        limit=limit,
        offset=offset,
    )

    return [_entry_to_response(e) for e in entries]


@router.get("/recent", response_model=list[AuditEntryResponse])
async def get_recent_activity(
    hours: int = Query(24, le=168),  # Max 1 week
    limit: int = Query(100, le=500),
):
    """Get recent activity across all entities."""
    service = get_audit_service()

    entries = service.get_recent_activity(hours=hours, limit=limit)

    return [_entry_to_response(e) for e in entries]


@router.get("/stats", response_model=AuditStatsResponse)
async def get_statistics(
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
):
    """Get audit statistics."""
    service = get_audit_service()

    stats = service.get_statistics(from_date=from_date, to_date=to_date)

    return AuditStatsResponse(**stats)


@router.get("/actions", response_model=list[str])
async def list_action_types():
    """List all available audit action types."""
    return [a.value for a in AuditAction]


# =============================================================================
# Helper Functions
# =============================================================================


def _entry_to_response(entry) -> AuditEntryResponse:
    """Convert AuditEntry to response model."""
    return AuditEntryResponse(
        id=entry.id,
        timestamp=entry.timestamp.isoformat(),
        user_id=entry.user_id,
        user_name=entry.user_name,
        action=entry.action.value,
        entity_type=entry.entity_type,
        entity_id=entry.entity_id,
        entity_number=entry.entity_number,
        summary=entry.summary,
        changes=[
            FieldChangeResponse(
                field=c.field_name,
                display_name=c.display_name or c.field_name,
                old_value=str(c.old_value) if c.old_value is not None else None,
                new_value=str(c.new_value) if c.new_value is not None else None,
            )
            for c in entry.changes
        ],
        reason=entry.reason,
        change_order_id=entry.change_order_id,
        workflow_id=entry.workflow_id,
    )
