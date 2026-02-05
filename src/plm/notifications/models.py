"""
Notification Models

Data structures for the notification system.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class NotificationType(str, Enum):
    """Types of notifications."""
    # Workflow
    TASK_ASSIGNED = "task_assigned"
    TASK_DUE_SOON = "task_due_soon"
    TASK_OVERDUE = "task_overdue"
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_REJECTED = "workflow_rejected"

    # Approvals
    APPROVAL_REQUIRED = "approval_required"
    APPROVAL_RECEIVED = "approval_received"
    REJECTION_RECEIVED = "rejection_received"

    # Document
    DOCUMENT_CHECKOUT = "document_checkout"
    DOCUMENT_CHECKIN = "document_checkin"
    DOCUMENT_RELEASED = "document_released"
    DOCUMENT_SUPERSEDED = "document_superseded"

    # Part/BOM
    PART_RELEASED = "part_released"
    PART_OBSOLETED = "part_obsoleted"
    BOM_CHANGED = "bom_changed"
    SUPERSESSION = "supersession"

    # ECO
    ECO_SUBMITTED = "eco_submitted"
    ECO_APPROVED = "eco_approved"
    ECO_REJECTED = "eco_rejected"
    ECO_IMPLEMENTED = "eco_implemented"

    # System
    SYSTEM_ALERT = "system_alert"
    MENTION = "mention"
    COMMENT = "comment"


class NotificationChannel(str, Enum):
    """Delivery channels for notifications."""
    EMAIL = "email"
    WEBHOOK = "webhook"
    IN_APP = "in_app"
    SMS = "sms"
    SLACK = "slack"
    TEAMS = "teams"


class NotificationPriority(str, Enum):
    """Notification priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class Notification:
    """
    A notification to be sent to users.
    """
    id: str
    notification_type: NotificationType
    priority: NotificationPriority = NotificationPriority.NORMAL

    # Recipients
    recipient_ids: list[str] = field(default_factory=list)
    recipient_emails: list[str] = field(default_factory=list)
    recipient_roles: list[str] = field(default_factory=list)

    # Content
    title: str = ""
    message: str = ""
    html_message: Optional[str] = None

    # Context
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    entity_number: Optional[str] = None
    action_url: Optional[str] = None

    # Sender
    sender_id: Optional[str] = None
    sender_name: Optional[str] = None

    # Delivery
    channels: list[NotificationChannel] = field(default_factory=list)
    sent_via: list[NotificationChannel] = field(default_factory=list)

    # Status
    created_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    is_read: bool = False

    # Additional data
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if not self.channels:
            self.channels = [NotificationChannel.IN_APP, NotificationChannel.EMAIL]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.notification_type.value,
            "priority": self.priority.value,
            "title": self.title,
            "message": self.message,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "entity_number": self.entity_number,
            "action_url": self.action_url,
            "sender_name": self.sender_name,
            "channels": [c.value for c in self.channels],
            "sent_via": [c.value for c in self.sent_via],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "is_read": self.is_read,
        }


@dataclass
class NotificationPreference:
    """
    User preferences for notification delivery.
    """
    user_id: str
    notification_type: NotificationType

    # Channel preferences
    email_enabled: bool = True
    in_app_enabled: bool = True
    webhook_enabled: bool = False
    slack_enabled: bool = False

    # Timing
    instant_delivery: bool = True      # Send immediately
    digest_enabled: bool = False       # Include in digest
    quiet_hours_start: Optional[int] = None  # Hour (0-23)
    quiet_hours_end: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "notification_type": self.notification_type.value,
            "email_enabled": self.email_enabled,
            "in_app_enabled": self.in_app_enabled,
            "webhook_enabled": self.webhook_enabled,
            "slack_enabled": self.slack_enabled,
            "instant_delivery": self.instant_delivery,
            "digest_enabled": self.digest_enabled,
        }


@dataclass
class WebhookConfig:
    """
    Webhook configuration for external integrations.
    """
    id: str
    name: str
    url: str

    # What to send
    event_types: list[NotificationType] = field(default_factory=list)
    entity_types: list[str] = field(default_factory=list)  # Filter by entity type

    # Security
    secret: Optional[str] = None       # For HMAC signing
    headers: dict[str, str] = field(default_factory=dict)

    # Settings
    is_active: bool = True
    retry_count: int = 3
    timeout_seconds: int = 30

    # Status
    last_triggered: Optional[datetime] = None
    last_status: Optional[int] = None
    failure_count: int = 0

    created_at: Optional[datetime] = None
    created_by: Optional[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "event_types": [e.value for e in self.event_types],
            "entity_types": self.entity_types,
            "is_active": self.is_active,
            "last_triggered": self.last_triggered.isoformat() if self.last_triggered else None,
            "last_status": self.last_status,
            "failure_count": self.failure_count,
        }


# =============================================================================
# Notification Templates
# =============================================================================


def get_notification_template(
    notification_type: NotificationType,
    context: dict[str, Any],
) -> tuple[str, str]:
    """
    Get title and message for a notification type.

    Returns:
        Tuple of (title, message)
    """
    templates = {
        NotificationType.TASK_ASSIGNED: (
            "New Task Assigned",
            "You have been assigned a new approval task for {entity_type} {entity_number}.",
        ),
        NotificationType.TASK_DUE_SOON: (
            "Task Due Soon",
            "Your approval task for {entity_type} {entity_number} is due in {due_days} day(s).",
        ),
        NotificationType.TASK_OVERDUE: (
            "Task Overdue",
            "Your approval task for {entity_type} {entity_number} is overdue. Please review immediately.",
        ),
        NotificationType.WORKFLOW_STARTED: (
            "Workflow Started",
            "{sender_name} has started a {workflow_name} workflow for {entity_type} {entity_number}.",
        ),
        NotificationType.WORKFLOW_COMPLETED: (
            "Workflow Completed",
            "The {workflow_name} workflow for {entity_type} {entity_number} has been completed.",
        ),
        NotificationType.WORKFLOW_REJECTED: (
            "Workflow Rejected",
            "The {workflow_name} workflow for {entity_type} {entity_number} has been rejected.",
        ),
        NotificationType.APPROVAL_REQUIRED: (
            "Approval Required",
            "{entity_type} {entity_number} requires your approval.",
        ),
        NotificationType.APPROVAL_RECEIVED: (
            "Approval Received",
            "{sender_name} has approved {entity_type} {entity_number}.",
        ),
        NotificationType.REJECTION_RECEIVED: (
            "Rejection Received",
            "{sender_name} has rejected {entity_type} {entity_number}. Reason: {reason}",
        ),
        NotificationType.DOCUMENT_CHECKOUT: (
            "Document Checked Out",
            "{sender_name} has checked out document {entity_number}.",
        ),
        NotificationType.DOCUMENT_CHECKIN: (
            "Document Checked In",
            "{sender_name} has checked in document {entity_number}.",
        ),
        NotificationType.DOCUMENT_RELEASED: (
            "Document Released",
            "Document {entity_number} has been released.",
        ),
        NotificationType.ECO_SUBMITTED: (
            "ECO Submitted",
            "{sender_name} has submitted ECO {entity_number}: {title}",
        ),
        NotificationType.ECO_APPROVED: (
            "ECO Approved",
            "ECO {entity_number} has been approved and is ready for implementation.",
        ),
        NotificationType.ECO_REJECTED: (
            "ECO Rejected",
            "ECO {entity_number} has been rejected. Reason: {reason}",
        ),
        NotificationType.PART_RELEASED: (
            "Part Released",
            "Part {entity_number} has been released to production.",
        ),
        NotificationType.SUPERSESSION: (
            "Part Superseded",
            "Part {old_part_number} has been superseded by {new_part_number}.",
        ),
    }

    template = templates.get(notification_type, ("Notification", "{message}"))
    title = template[0]
    message = template[1].format(**context) if context else template[1]

    return title, message
