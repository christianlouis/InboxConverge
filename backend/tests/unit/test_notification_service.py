"""
Unit tests for the notification service (services/notification_service.py).

All external dependencies (database, Apprise) are mocked so no real
infrastructure is needed.
"""

from unittest.mock import AsyncMock, MagicMock, patch

from app.services.notification_service import (
    send_user_notification,
    send_admin_notification,
    test_notification as _test_notification,
    _send_apprise,
)

# ── helpers ──────────────────────────────────────────────────────────────────


def _make_notification_config(
    *,
    id: int = 1,
    user_id: int = 42,
    apprise_url: str = "json://localhost",
    is_enabled: bool = True,
    notify_on_errors: bool = True,
    notify_on_success: bool = False,
):
    cfg = MagicMock()
    cfg.id = id
    cfg.user_id = user_id
    cfg.apprise_url = apprise_url
    cfg.is_enabled = is_enabled
    cfg.notify_on_errors = notify_on_errors
    cfg.notify_on_success = notify_on_success
    return cfg


def _make_db(configs=None):
    """Return an AsyncMock db with execute returning the given config list."""
    db = AsyncMock()
    result = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = configs or []
    result.scalars.return_value = scalars
    db.execute = AsyncMock(return_value=result)
    return db


# ── send_user_notification ────────────────────────────────────────────────────


class TestSendUserNotification:
    async def test_returns_zero_when_no_configs(self):
        db = _make_db(configs=[])
        count = await send_user_notification(db, user_id=1, title="T", body="B")
        assert count == 0

    async def test_sends_to_error_channel(self):
        cfg = _make_notification_config(notify_on_errors=True, notify_on_success=False)
        db = _make_db(configs=[cfg])
        with patch(
            "app.services.notification_service._send_apprise",
            new=AsyncMock(return_value=True),
        ) as mock_send:
            count = await send_user_notification(
                db, user_id=42, title="Err", body="msg", notify_on_error=True
            )
        assert count == 1
        mock_send.assert_awaited_once()

    async def test_skips_error_channel_for_success_notification(self):
        cfg = _make_notification_config(notify_on_errors=True, notify_on_success=False)
        db = _make_db(configs=[cfg])
        with patch(
            "app.services.notification_service._send_apprise",
            new=AsyncMock(return_value=True),
        ) as mock_send:
            count = await send_user_notification(
                db, user_id=42, title="Ok", body="msg", notify_on_error=False
            )
        assert count == 0
        mock_send.assert_not_awaited()

    async def test_sends_to_success_channel(self):
        cfg = _make_notification_config(notify_on_errors=False, notify_on_success=True)
        db = _make_db(configs=[cfg])
        with patch(
            "app.services.notification_service._send_apprise",
            new=AsyncMock(return_value=True),
        ) as mock_send:
            count = await send_user_notification(
                db, user_id=42, title="Ok", body="msg", notify_on_error=False
            )
        assert count == 1
        mock_send.assert_awaited_once()

    async def test_failed_apprise_not_counted(self):
        cfg = _make_notification_config(notify_on_errors=True)
        db = _make_db(configs=[cfg])
        with patch(
            "app.services.notification_service._send_apprise",
            new=AsyncMock(return_value=False),
        ):
            count = await send_user_notification(db, user_id=42, title="T", body="B")
        assert count == 0

    async def test_exception_in_apprise_swallowed(self):
        cfg = _make_notification_config(notify_on_errors=True)
        db = _make_db(configs=[cfg])
        with patch(
            "app.services.notification_service._send_apprise",
            new=AsyncMock(side_effect=Exception("boom")),
        ):
            count = await send_user_notification(db, user_id=42, title="T", body="B")
        assert count == 0

    async def test_multiple_channels_counted_individually(self):
        cfg1 = _make_notification_config(id=1, notify_on_errors=True)
        cfg2 = _make_notification_config(id=2, notify_on_errors=True)
        db = _make_db(configs=[cfg1, cfg2])
        with patch(
            "app.services.notification_service._send_apprise",
            new=AsyncMock(return_value=True),
        ):
            count = await send_user_notification(db, user_id=42, title="T", body="B")
        assert count == 2


# ── send_admin_notification ───────────────────────────────────────────────────


class TestSendAdminNotification:
    async def test_returns_zero_when_no_configs(self):
        db = _make_db(configs=[])
        count = await send_admin_notification(db, title="T", body="B")
        assert count == 0

    async def test_sends_to_enabled_channel(self):
        cfg = MagicMock()
        cfg.id = 1
        cfg.apprise_url = "json://localhost"
        db = _make_db(configs=[cfg])
        with patch(
            "app.services.notification_service._send_apprise",
            new=AsyncMock(return_value=True),
        ):
            count = await send_admin_notification(db, title="T", body="B")
        assert count == 1

    async def test_exception_in_channel_swallowed(self):
        cfg = MagicMock()
        cfg.id = 1
        cfg.apprise_url = "json://localhost"
        db = _make_db(configs=[cfg])
        with patch(
            "app.services.notification_service._send_apprise",
            new=AsyncMock(side_effect=RuntimeError("oops")),
        ):
            count = await send_admin_notification(db, title="T", body="B")
        assert count == 0


# ── test_notification ─────────────────────────────────────────────────────────


class TestTestNotification:
    async def test_success(self):
        with patch(
            "app.services.notification_service._send_apprise",
            new=AsyncMock(return_value=True),
        ):
            ok, msg = await _test_notification("json://localhost")
        assert ok is True
        assert "success" in msg.lower()

    async def test_failure_from_apprise(self):
        with patch(
            "app.services.notification_service._send_apprise",
            new=AsyncMock(return_value=False),
        ):
            ok, msg = await _test_notification("json://localhost")
        assert ok is False

    async def test_exception_returns_false(self):
        with patch(
            "app.services.notification_service._send_apprise",
            new=AsyncMock(side_effect=Exception("network error")),
        ):
            ok, msg = await _test_notification("json://localhost")
        assert ok is False
        assert "error" in msg.lower()


# ── _send_apprise internal helper ─────────────────────────────────────────────


class TestSendApprise:
    async def test_invalid_url_returns_false(self):
        # Apprise.add() returns False for unrecognised schemes
        with patch("app.services.notification_service.apprise") as mock_apprise_module:
            ap_instance = MagicMock()
            ap_instance.add.return_value = False
            mock_apprise_module.Apprise.return_value = ap_instance
            result = await _send_apprise("not-a-valid-url://", "T", "B")
        assert result is False

    async def test_valid_url_returns_true(self):
        with patch("app.services.notification_service.apprise") as mock_apprise_module:
            ap_instance = MagicMock()
            ap_instance.add.return_value = True
            ap_instance.async_notify = AsyncMock(return_value=True)
            mock_apprise_module.Apprise.return_value = ap_instance
            result = await _send_apprise("json://localhost", "T", "B")
        assert result is True
