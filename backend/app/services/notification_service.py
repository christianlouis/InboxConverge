"""
Notification service using Apprise for multi-channel alerting.

Supports:
- User-specific notifications (per-user Apprise URLs)
- Admin-wide system notifications (system-level alerts)
- Test notifications to verify configuration
"""

import logging

import apprise

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.database_models import NotificationConfig, AdminNotificationConfig

logger = logging.getLogger(__name__)


async def send_user_notification(
    db: AsyncSession,
    user_id: int,
    title: str,
    body: str,
    notify_on_error: bool = True,
) -> int:
    """
    Send a notification to all enabled notification channels for a given user.

    Args:
        db: Database session
        user_id: The user to notify
        title: Notification title/subject
        body: Notification body text
        notify_on_error: If True, only sends to channels with notify_on_errors=True
                         If False, only sends to channels with notify_on_success=True

    Returns:
        Number of channels notified successfully
    """
    result = await db.execute(
        select(NotificationConfig).where(
            NotificationConfig.user_id == user_id,
            NotificationConfig.is_enabled == True,  # noqa: E712
            NotificationConfig.apprise_url.isnot(None),
        )
    )
    configs = result.scalars().all()

    if not configs:
        return 0

    sent = 0
    for config in configs:
        if notify_on_error and not config.notify_on_errors:
            continue
        if not notify_on_error and not config.notify_on_success:
            continue

        try:
            success = await _send_apprise(str(config.apprise_url or ""), title, body)
            if success:
                sent += 1
        except Exception as exc:
            logger.warning(
                "Failed to send notification via channel %s (user %s): %s",
                config.id,
                user_id,
                exc,
            )

    return sent


async def send_admin_notification(
    db: AsyncSession,
    title: str,
    body: str,
) -> int:
    """
    Send a notification to all enabled admin notification channels.

    Returns:
        Number of channels notified successfully
    """
    result = await db.execute(
        select(AdminNotificationConfig).where(
            AdminNotificationConfig.is_enabled == True,  # noqa: E712
            AdminNotificationConfig.notify_on_errors == True,  # noqa: E712
        )
    )
    configs = result.scalars().all()

    if not configs:
        return 0

    sent = 0
    for config in configs:
        try:
            success = await _send_apprise(str(config.apprise_url or ""), title, body)
            if success:
                sent += 1
        except Exception as exc:
            logger.warning(
                "Failed to send admin notification via channel %s: %s",
                config.id,
                exc,
            )

    return sent


async def test_notification(apprise_url: str) -> tuple[bool, str]:
    """
    Send a test notification to the given Apprise URL.

    Returns:
        (success, message) tuple
    """
    try:
        success = await _send_apprise(
            apprise_url,
            title="InboxRescue: Test Notification",
            body="This is a test notification from InboxRescue. Your notification channel is configured correctly!",
        )
        if success:
            return True, "Test notification sent successfully"
        return False, "Notification delivery failed (check your Apprise URL)"
    except Exception as exc:
        return False, f"Error sending test notification: {exc}"


async def _send_apprise(url: str, title: str, body: str) -> bool:
    """Internal helper – create an Apprise instance, load the URL, and notify."""
    ap = apprise.Apprise()
    if not ap.add(url):
        logger.warning("Apprise could not parse URL: %s", url[:60])
        return False

    result = await ap.async_notify(title=title, body=body)
    return bool(result)
