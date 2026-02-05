"""
Notifications Module

Multi-channel notification system for PLM events.
Supports:
- Email notifications
- Webhook callbacks
- In-app notifications
- Notification preferences
"""
from .models import (
    NotificationType,
    NotificationChannel,
    NotificationPriority,
    Notification,
    NotificationPreference,
    WebhookConfig,
)
from .service import NotificationService, get_notification_service

__all__ = [
    # Models
    "NotificationType",
    "NotificationChannel",
    "NotificationPriority",
    "Notification",
    "NotificationPreference",
    "WebhookConfig",
    # Service
    "NotificationService",
    "get_notification_service",
]
