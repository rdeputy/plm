"""
Audit Trail Models

Data structures for tracking all changes in the PLM system.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class AuditAction(str, Enum):
    """Types of auditable actions."""
    # CRUD
    CREATE = "create"
    READ = "read"               # Optional - for sensitive data access
    UPDATE = "update"
    DELETE = "delete"

    # Lifecycle
    SUBMIT = "submit"
    APPROVE = "approve"
    REJECT = "reject"
    RELEASE = "release"
    REVISE = "revise"
    OBSOLETE = "obsolete"
    RESTORE = "restore"

    # Document actions
    CHECKOUT = "checkout"
    CHECKIN = "checkin"
    CANCEL_CHECKOUT = "cancel_checkout"
    DOWNLOAD = "download"
    UPLOAD = "upload"

    # Workflow
    WORKFLOW_START = "workflow_start"
    WORKFLOW_ADVANCE = "workflow_advance"
    WORKFLOW_COMPLETE = "workflow_complete"
    WORKFLOW_REJECT = "workflow_reject"
    WORKFLOW_RECALL = "workflow_recall"
    DELEGATE = "delegate"

    # BOM
    BOM_ADD_ITEM = "bom_add_item"
    BOM_REMOVE_ITEM = "bom_remove_item"
    BOM_UPDATE_QTY = "bom_update_qty"

    # System
    LOGIN = "login"
    LOGOUT = "logout"
    EXPORT = "export"
    IMPORT = "import"
    BULK_UPDATE = "bulk_update"


@dataclass
class FieldChange:
    """A single field change within an audit entry."""
    field_name: str
    old_value: Any
    new_value: Any
    display_name: Optional[str] = None  # Human-readable field name

    def to_dict(self) -> dict:
        return {
            "field": self.field_name,
            "display_name": self.display_name or self.field_name,
            "old_value": _serialize_value(self.old_value),
            "new_value": _serialize_value(self.new_value),
        }


@dataclass
class AuditEntry:
    """
    A single audit log entry.

    Immutable record of an action in the system.
    """
    id: str
    timestamp: datetime

    # Who
    user_id: str
    user_name: str
    user_email: Optional[str] = None
    user_ip: Optional[str] = None
    user_agent: Optional[str] = None

    # What
    action: AuditAction
    entity_type: str              # part, bom, document, eco, etc.
    entity_id: str
    entity_number: Optional[str] = None  # Display identifier

    # Changes
    changes: list[FieldChange] = field(default_factory=list)
    summary: str = ""             # Human-readable summary

    # Context
    reason: Optional[str] = None          # User-provided reason
    change_order_id: Optional[str] = None # Linked ECO
    workflow_id: Optional[str] = None     # Linked workflow instance
    session_id: Optional[str] = None      # User session

    # Additional data
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.summary:
            self.summary = self._generate_summary()

    def _generate_summary(self) -> str:
        """Generate human-readable summary."""
        action_text = self.action.value.replace("_", " ").title()

        if self.changes:
            fields = [c.field_name for c in self.changes[:3]]
            field_text = ", ".join(fields)
            if len(self.changes) > 3:
                field_text += f" (+{len(self.changes) - 3} more)"
            return f"{action_text} {self.entity_type} {self.entity_number or self.entity_id}: {field_text}"

        return f"{action_text} {self.entity_type} {self.entity_number or self.entity_id}"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "user_name": self.user_name,
            "action": self.action.value,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "entity_number": self.entity_number,
            "summary": self.summary,
            "changes": [c.to_dict() for c in self.changes],
            "reason": self.reason,
            "change_order_id": self.change_order_id,
            "workflow_id": self.workflow_id,
        }


def _serialize_value(value: Any) -> Any:
    """Serialize a value for storage."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (list, dict)):
        return value
    return str(value)
