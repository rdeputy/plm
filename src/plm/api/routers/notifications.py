"""
Notifications API Router

Endpoints for managing notifications and webhooks.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from plm.api.auth import require_user_id
from ...notifications import (
    NotificationChannel,
    NotificationPriority,
    NotificationType,
    get_notification_service,
)

router = APIRouter()


# =============================================================================
# Pydantic Schemas
# =============================================================================


class NotificationResponse(BaseModel):
    """Notification response."""
    id: str
    type: str
    priority: str
    title: str
    message: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    entity_number: Optional[str] = None
    action_url: Optional[str] = None
    sender_name: Optional[str] = None
    channels: list[str]
    sent_via: list[str]
    created_at: Optional[str] = None
    sent_at: Optional[str] = None
    is_read: bool


class NotificationPreferenceRequest(BaseModel):
    """Set notification preference."""
    notification_type: str
    email_enabled: bool = True
    in_app_enabled: bool = True
    webhook_enabled: bool = False
    slack_enabled: bool = False
    instant_delivery: bool = True
    digest_enabled: bool = False


class NotificationPreferenceResponse(BaseModel):
    """Notification preference response."""
    user_id: str
    notification_type: str
    email_enabled: bool
    in_app_enabled: bool
    webhook_enabled: bool
    slack_enabled: bool
    instant_delivery: bool
    digest_enabled: bool


class WebhookCreateRequest(BaseModel):
    """Create webhook request."""
    name: str
    url: str
    event_types: list[str] = Field(default_factory=list)
    entity_types: list[str] = Field(default_factory=list)
    secret: Optional[str] = None
    headers: dict[str, str] = Field(default_factory=dict)


class WebhookResponse(BaseModel):
    """Webhook response."""
    id: str
    name: str
    url: str
    event_types: list[str]
    entity_types: list[str]
    is_active: bool
    last_triggered: Optional[str] = None
    last_status: Optional[int] = None
    failure_count: int


class SendNotificationRequest(BaseModel):
    """Send a notification."""
    notification_type: str
    recipient_ids: list[str] = Field(default_factory=list)
    recipient_emails: list[str] = Field(default_factory=list)
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    entity_number: Optional[str] = None
    title: Optional[str] = None
    message: Optional[str] = None
    priority: str = "normal"
    action_url: Optional[str] = None


class UnreadCountResponse(BaseModel):
    """Unread notification count."""
    user_id: str
    unread_count: int


# =============================================================================
# Notification Endpoints
# =============================================================================


@router.get("/", response_model=list[NotificationResponse])
async def get_notifications(
    user_id: str = Depends(require_user_id),
    unread_only: bool = False,
    limit: int = Query(50, le=200),
    offset: int = 0,
):
    """Get notifications for a user."""
    service = get_notification_service()

    notifications = service.get_user_notifications(
        user_id=user_id,
        unread_only=unread_only,
        limit=limit,
        offset=offset,
    )

    return [_notification_to_response(n) for n in notifications]


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(user_id: str = Depends(require_user_id)):
    """Get unread notification count for a user."""
    service = get_notification_service()
    count = service.get_unread_count(user_id)
    return UnreadCountResponse(user_id=user_id, unread_count=count)


@router.post("/{notification_id}/read")
async def mark_as_read(notification_id: str):
    """Mark a notification as read."""
    service = get_notification_service()

    if not service.mark_read(notification_id):
        raise HTTPException(status_code=404, detail="Notification not found")

    return {"status": "read", "id": notification_id}


@router.post("/mark-all-read")
async def mark_all_as_read(user_id: str = Depends(require_user_id)):
    """Mark all notifications as read for a user."""
    service = get_notification_service()
    count = service.mark_all_read(user_id)
    return {"status": "ok", "marked_read": count}


@router.post("/send", response_model=NotificationResponse)
async def send_notification(
    data: SendNotificationRequest,
    sender_id: Optional[str] = None,
    sender_name: Optional[str] = None,
):
    """Send a notification (admin/system use)."""
    service = get_notification_service()

    try:
        notification_type = NotificationType(data.notification_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid notification type: {data.notification_type}"
        )

    try:
        priority = NotificationPriority(data.priority)
    except ValueError:
        priority = NotificationPriority.NORMAL

    notification = service.notify(
        notification_type=notification_type,
        recipient_ids=data.recipient_ids,
        recipient_emails=data.recipient_emails,
        entity_type=data.entity_type,
        entity_id=data.entity_id,
        entity_number=data.entity_number,
        sender_id=sender_id,
        sender_name=sender_name,
        priority=priority,
        action_url=data.action_url,
        custom_title=data.title,
        custom_message=data.message,
    )

    return _notification_to_response(notification)


# =============================================================================
# Preference Endpoints
# =============================================================================


@router.get("/preferences", response_model=list[NotificationPreferenceResponse])
async def get_preferences(user_id: str = Depends(require_user_id)):
    """Get notification preferences for a user."""
    service = get_notification_service()
    preferences = service.get_preferences(user_id)
    return [
        NotificationPreferenceResponse(
            user_id=p.user_id,
            notification_type=p.notification_type.value,
            email_enabled=p.email_enabled,
            in_app_enabled=p.in_app_enabled,
            webhook_enabled=p.webhook_enabled,
            slack_enabled=p.slack_enabled,
            instant_delivery=p.instant_delivery,
            digest_enabled=p.digest_enabled,
        )
        for p in preferences
    ]


@router.post("/preferences", response_model=NotificationPreferenceResponse)
async def set_preference(data: NotificationPreferenceRequest, user_id: str = Depends(require_user_id)):
    """Set a notification preference."""
    service = get_notification_service()

    try:
        notification_type = NotificationType(data.notification_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid notification type: {data.notification_type}"
        )

    pref = service.set_preference(
        user_id=user_id,
        notification_type=notification_type,
        email_enabled=data.email_enabled,
        in_app_enabled=data.in_app_enabled,
        webhook_enabled=data.webhook_enabled,
        slack_enabled=data.slack_enabled,
        instant_delivery=data.instant_delivery,
        digest_enabled=data.digest_enabled,
    )

    return NotificationPreferenceResponse(
        user_id=pref.user_id,
        notification_type=pref.notification_type.value,
        email_enabled=pref.email_enabled,
        in_app_enabled=pref.in_app_enabled,
        webhook_enabled=pref.webhook_enabled,
        slack_enabled=pref.slack_enabled,
        instant_delivery=pref.instant_delivery,
        digest_enabled=pref.digest_enabled,
    )


# =============================================================================
# Webhook Endpoints
# =============================================================================


@router.get("/webhooks", response_model=list[WebhookResponse])
async def list_webhooks():
    """List all webhooks."""
    service = get_notification_service()
    webhooks = service.list_webhooks()
    return [_webhook_to_response(w) for w in webhooks]


@router.post("/webhooks", response_model=WebhookResponse)
async def create_webhook(data: WebhookCreateRequest, created_by: Optional[str] = None):
    """Create a webhook."""
    service = get_notification_service()

    # Parse event types
    event_types = []
    for et in data.event_types:
        try:
            event_types.append(NotificationType(et))
        except ValueError:
            pass

    webhook = service.register_webhook(
        name=data.name,
        url=data.url,
        event_types=event_types if event_types else None,
        entity_types=data.entity_types if data.entity_types else None,
        secret=data.secret,
        headers=data.headers,
        created_by=created_by,
    )

    return _webhook_to_response(webhook)


@router.get("/webhooks/{webhook_id}", response_model=WebhookResponse)
async def get_webhook(webhook_id: str):
    """Get a webhook by ID."""
    service = get_notification_service()
    webhook = service.get_webhook(webhook_id)

    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    return _webhook_to_response(webhook)


@router.delete("/webhooks/{webhook_id}")
async def delete_webhook(webhook_id: str):
    """Delete a webhook."""
    service = get_notification_service()

    if not service.delete_webhook(webhook_id):
        raise HTTPException(status_code=404, detail="Webhook not found")

    return {"status": "deleted", "id": webhook_id}


@router.post("/webhooks/{webhook_id}/toggle")
async def toggle_webhook(webhook_id: str, active: bool = True):
    """Enable or disable a webhook."""
    service = get_notification_service()

    webhook = service.toggle_webhook(webhook_id, active)
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    return {"status": "ok", "active": webhook.is_active}


@router.get("/types", response_model=list[str])
async def list_notification_types():
    """List all notification types."""
    return [t.value for t in NotificationType]


# =============================================================================
# Helper Functions
# =============================================================================


def _notification_to_response(notification) -> NotificationResponse:
    """Convert Notification to response model."""
    return NotificationResponse(
        id=notification.id,
        type=notification.notification_type.value,
        priority=notification.priority.value,
        title=notification.title,
        message=notification.message,
        entity_type=notification.entity_type,
        entity_id=notification.entity_id,
        entity_number=notification.entity_number,
        action_url=notification.action_url,
        sender_name=notification.sender_name,
        channels=[c.value for c in notification.channels],
        sent_via=[c.value for c in notification.sent_via],
        created_at=notification.created_at.isoformat() if notification.created_at else None,
        sent_at=notification.sent_at.isoformat() if notification.sent_at else None,
        is_read=notification.is_read,
    )


def _webhook_to_response(webhook) -> WebhookResponse:
    """Convert WebhookConfig to response model."""
    return WebhookResponse(
        id=webhook.id,
        name=webhook.name,
        url=webhook.url,
        event_types=[e.value for e in webhook.event_types],
        entity_types=webhook.entity_types,
        is_active=webhook.is_active,
        last_triggered=webhook.last_triggered.isoformat() if webhook.last_triggered else None,
        last_status=webhook.last_status,
        failure_count=webhook.failure_count,
    )
