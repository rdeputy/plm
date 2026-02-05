"""
Notification Service

Centralized service for sending notifications across channels.
"""

import hashlib
import hmac
import json
import logging
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from .models import (
    Notification,
    NotificationChannel,
    NotificationPreference,
    NotificationPriority,
    NotificationType,
    WebhookConfig,
    get_notification_template,
)

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Service for managing and sending notifications.

    Handles:
    - Creating notifications from events
    - Delivering via configured channels
    - Managing user preferences
    - Webhook management
    """

    def __init__(self):
        # In-memory storage (replace with DB in production)
        self._notifications: dict[str, Notification] = {}
        self._preferences: dict[str, dict[str, NotificationPreference]] = {}
        self._webhooks: dict[str, WebhookConfig] = {}

        # By user index
        self._by_user: dict[str, list[str]] = {}

    # =========================================================================
    # Notification Creation
    # =========================================================================

    def notify(
        self,
        notification_type: NotificationType,
        recipient_ids: list[str] | None = None,
        recipient_emails: list[str] | None = None,
        recipient_roles: list[str] | None = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        entity_number: Optional[str] = None,
        sender_id: Optional[str] = None,
        sender_name: Optional[str] = None,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        action_url: Optional[str] = None,
        context: dict[str, Any] | None = None,
        custom_title: Optional[str] = None,
        custom_message: Optional[str] = None,
    ) -> Notification:
        """
        Create and send a notification.

        Args:
            notification_type: Type of notification
            recipient_ids: User IDs to notify
            recipient_emails: Direct email addresses
            recipient_roles: Roles to notify
            entity_type: Related entity type
            entity_id: Related entity ID
            entity_number: Display number
            sender_id: User who triggered notification
            sender_name: Sender display name
            priority: Notification priority
            action_url: URL for action button
            context: Template context data
            custom_title: Override default title
            custom_message: Override default message

        Returns:
            Created Notification
        """
        # Build context for template
        template_context = {
            "entity_type": entity_type or "",
            "entity_number": entity_number or "",
            "entity_id": entity_id or "",
            "sender_name": sender_name or "System",
            **(context or {}),
        }

        # Get template
        title, message = get_notification_template(notification_type, template_context)

        if custom_title:
            title = custom_title
        if custom_message:
            message = custom_message

        # Create notification
        notification = Notification(
            id=str(uuid4()),
            notification_type=notification_type,
            priority=priority,
            recipient_ids=recipient_ids or [],
            recipient_emails=recipient_emails or [],
            recipient_roles=recipient_roles or [],
            title=title,
            message=message,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_number=entity_number,
            action_url=action_url,
            sender_id=sender_id,
            sender_name=sender_name,
            metadata=context or {},
        )

        # Store notification
        self._notifications[notification.id] = notification

        # Index by recipients
        for user_id in notification.recipient_ids:
            if user_id not in self._by_user:
                self._by_user[user_id] = []
            self._by_user[user_id].append(notification.id)

        # Send via channels
        self._deliver(notification)

        logger.info(f"Notification created: {notification.id} - {notification.title}")

        return notification

    def notify_task_assigned(
        self,
        assignee_id: str,
        assignee_email: Optional[str],
        entity_type: str,
        entity_id: str,
        entity_number: str,
        task_name: str,
        due_date: Optional[datetime] = None,
        sender_name: Optional[str] = None,
    ) -> Notification:
        """Send task assignment notification."""
        return self.notify(
            notification_type=NotificationType.TASK_ASSIGNED,
            recipient_ids=[assignee_id],
            recipient_emails=[assignee_email] if assignee_email else None,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_number=entity_number,
            sender_name=sender_name,
            priority=NotificationPriority.HIGH,
            context={
                "task_name": task_name,
                "due_date": due_date.isoformat() if due_date else None,
            },
        )

    def notify_workflow_started(
        self,
        workflow_name: str,
        entity_type: str,
        entity_id: str,
        entity_number: str,
        recipient_ids: list[str],
        sender_name: str,
    ) -> Notification:
        """Send workflow started notification."""
        return self.notify(
            notification_type=NotificationType.WORKFLOW_STARTED,
            recipient_ids=recipient_ids,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_number=entity_number,
            sender_name=sender_name,
            context={"workflow_name": workflow_name},
        )

    def notify_approval_required(
        self,
        approver_ids: list[str],
        entity_type: str,
        entity_id: str,
        entity_number: str,
        action_url: Optional[str] = None,
    ) -> Notification:
        """Send approval required notification."""
        return self.notify(
            notification_type=NotificationType.APPROVAL_REQUIRED,
            recipient_ids=approver_ids,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_number=entity_number,
            priority=NotificationPriority.HIGH,
            action_url=action_url,
        )

    def notify_eco_submitted(
        self,
        eco_id: str,
        eco_number: str,
        eco_title: str,
        submitter_name: str,
        reviewer_ids: list[str],
    ) -> Notification:
        """Send ECO submission notification."""
        return self.notify(
            notification_type=NotificationType.ECO_SUBMITTED,
            recipient_ids=reviewer_ids,
            entity_type="eco",
            entity_id=eco_id,
            entity_number=eco_number,
            sender_name=submitter_name,
            context={"title": eco_title},
        )

    # =========================================================================
    # Notification Delivery
    # =========================================================================

    def _deliver(self, notification: Notification) -> None:
        """Deliver notification via configured channels."""
        for channel in notification.channels:
            try:
                if channel == NotificationChannel.IN_APP:
                    self._deliver_in_app(notification)
                elif channel == NotificationChannel.EMAIL:
                    self._deliver_email(notification)
                elif channel == NotificationChannel.WEBHOOK:
                    self._deliver_webhooks(notification)

                notification.sent_via.append(channel)
            except Exception as e:
                logger.error(f"Failed to deliver via {channel.value}: {e}")

        notification.sent_at = datetime.now()

    def _deliver_in_app(self, notification: Notification) -> None:
        """Deliver as in-app notification (already stored)."""
        # Already stored in _notifications
        logger.debug(f"In-app notification stored: {notification.id}")

    def _deliver_email(self, notification: Notification) -> None:
        """Deliver via email."""
        # In production, integrate with email service (SendGrid, SES, etc.)
        for email in notification.recipient_emails:
            logger.info(f"Would send email to {email}: {notification.title}")

        # Also send to users by looking up their emails
        for user_id in notification.recipient_ids:
            # Would look up user email here
            logger.info(f"Would send email to user {user_id}: {notification.title}")

    def _deliver_webhooks(self, notification: Notification) -> None:
        """Deliver to configured webhooks."""
        for webhook in self._webhooks.values():
            if not webhook.is_active:
                continue

            # Check if webhook wants this event type
            if webhook.event_types and notification.notification_type not in webhook.event_types:
                continue

            # Check entity type filter
            if webhook.entity_types and notification.entity_type not in webhook.entity_types:
                continue

            self._send_webhook(webhook, notification)

    def _send_webhook(self, webhook: WebhookConfig, notification: Notification) -> bool:
        """Send notification to a webhook."""
        payload = {
            "event": notification.notification_type.value,
            "timestamp": datetime.now().isoformat(),
            "notification_id": notification.id,
            "data": {
                "title": notification.title,
                "message": notification.message,
                "entity_type": notification.entity_type,
                "entity_id": notification.entity_id,
                "entity_number": notification.entity_number,
                "sender": notification.sender_name,
                "metadata": notification.metadata,
            },
        }

        # Sign payload if secret configured
        headers = dict(webhook.headers)
        if webhook.secret:
            signature = hmac.new(
                webhook.secret.encode(),
                json.dumps(payload).encode(),
                hashlib.sha256
            ).hexdigest()
            headers["X-PLM-Signature"] = signature

        # In production, use httpx to send request
        logger.info(f"Would POST to webhook {webhook.name}: {webhook.url}")
        logger.debug(f"Payload: {payload}")

        webhook.last_triggered = datetime.now()
        webhook.last_status = 200  # Would be actual response code

        return True

    # =========================================================================
    # Notification Queries
    # =========================================================================

    def get_notification(self, notification_id: str) -> Optional[Notification]:
        """Get a notification by ID."""
        return self._notifications.get(notification_id)

    def get_user_notifications(
        self,
        user_id: str,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Notification]:
        """Get notifications for a user."""
        notification_ids = self._by_user.get(user_id, [])

        notifications = []
        for nid in notification_ids:
            notification = self._notifications.get(nid)
            if notification:
                if unread_only and notification.is_read:
                    continue
                notifications.append(notification)

        # Sort by created_at descending
        notifications.sort(key=lambda n: n.created_at or datetime.min, reverse=True)

        return notifications[offset:offset + limit]

    def get_unread_count(self, user_id: str) -> int:
        """Get unread notification count for a user."""
        notifications = self.get_user_notifications(user_id, unread_only=True)
        return len(notifications)

    def mark_read(self, notification_id: str) -> bool:
        """Mark a notification as read."""
        notification = self.get_notification(notification_id)
        if notification:
            notification.is_read = True
            notification.read_at = datetime.now()
            return True
        return False

    def mark_all_read(self, user_id: str) -> int:
        """Mark all notifications as read for a user."""
        count = 0
        for notification in self.get_user_notifications(user_id, unread_only=True):
            notification.is_read = True
            notification.read_at = datetime.now()
            count += 1
        return count

    # =========================================================================
    # Preference Management
    # =========================================================================

    def get_preferences(self, user_id: str) -> list[NotificationPreference]:
        """Get all preferences for a user."""
        user_prefs = self._preferences.get(user_id, {})
        return list(user_prefs.values())

    def set_preference(
        self,
        user_id: str,
        notification_type: NotificationType,
        email_enabled: bool = True,
        in_app_enabled: bool = True,
        webhook_enabled: bool = False,
        slack_enabled: bool = False,
        instant_delivery: bool = True,
        digest_enabled: bool = False,
    ) -> NotificationPreference:
        """Set notification preference for a user."""
        pref = NotificationPreference(
            user_id=user_id,
            notification_type=notification_type,
            email_enabled=email_enabled,
            in_app_enabled=in_app_enabled,
            webhook_enabled=webhook_enabled,
            slack_enabled=slack_enabled,
            instant_delivery=instant_delivery,
            digest_enabled=digest_enabled,
        )

        if user_id not in self._preferences:
            self._preferences[user_id] = {}
        self._preferences[user_id][notification_type.value] = pref

        return pref

    # =========================================================================
    # Webhook Management
    # =========================================================================

    def register_webhook(
        self,
        name: str,
        url: str,
        event_types: list[NotificationType] | None = None,
        entity_types: list[str] | None = None,
        secret: Optional[str] = None,
        headers: dict[str, str] | None = None,
        created_by: Optional[str] = None,
    ) -> WebhookConfig:
        """Register a webhook endpoint."""
        webhook = WebhookConfig(
            id=str(uuid4()),
            name=name,
            url=url,
            event_types=event_types or [],
            entity_types=entity_types or [],
            secret=secret,
            headers=headers or {},
            created_by=created_by,
        )

        self._webhooks[webhook.id] = webhook
        logger.info(f"Registered webhook: {name} -> {url}")

        return webhook

    def get_webhook(self, webhook_id: str) -> Optional[WebhookConfig]:
        """Get a webhook by ID."""
        return self._webhooks.get(webhook_id)

    def list_webhooks(self) -> list[WebhookConfig]:
        """List all webhooks."""
        return list(self._webhooks.values())

    def delete_webhook(self, webhook_id: str) -> bool:
        """Delete a webhook."""
        if webhook_id in self._webhooks:
            del self._webhooks[webhook_id]
            return True
        return False

    def toggle_webhook(self, webhook_id: str, active: bool) -> Optional[WebhookConfig]:
        """Enable/disable a webhook."""
        webhook = self.get_webhook(webhook_id)
        if webhook:
            webhook.is_active = active
            return webhook
        return None


# Singleton instance
_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """Get the singleton notification service instance."""
    global _service
    if _service is None:
        _service = NotificationService()
    return _service
