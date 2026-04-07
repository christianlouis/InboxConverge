"""
Unit tests for notification config endpoints (api/v1/endpoints/notifications.py).

All database interactions and auth dependencies are mocked.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import AsyncClient, ASGITransport

from app.main import create_application
from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.models.database_models import (
    User,
    NotificationConfig,
    NotificationChannel,
    SubscriptionTier,
)

# ── helpers ──────────────────────────────────────────────────────────────────


def _make_user(**overrides) -> MagicMock:
    defaults = dict(
        id=1,
        email="user@example.com",
        full_name="Test User",
        is_active=True,
        is_superuser=False,
        subscription_tier=SubscriptionTier.FREE,
        subscription_status="active",
        google_id=None,
        oauth_provider=None,
        last_login_at=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        stripe_customer_id=None,
        stripe_subscription_id=None,
        subscription_expires_at=None,
    )
    defaults.update(overrides)
    u = MagicMock(spec=User)
    for k, v in defaults.items():
        setattr(u, k, v)
    return u


def _make_notification_config(**overrides) -> MagicMock:
    defaults = dict(
        id=1,
        user_id=1,
        name="Test Notification",
        apprise_url="json://localhost",
        channel=NotificationChannel.WEBHOOK,
        is_enabled=True,
        config={},
        notify_on_errors=True,
        notify_on_success=False,
        notify_threshold=3,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    cfg = MagicMock(spec=NotificationConfig)
    for k, v in defaults.items():
        setattr(cfg, k, v)
    return cfg


def _scalar_one_or_none(value):
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    return r


def _scalars_all(values):
    r = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = values
    r.scalars.return_value = scalars
    return r


@pytest.fixture
def app():
    return create_application()


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    db.delete = AsyncMock()
    return db


@pytest.fixture
def current_user():
    return _make_user()


@pytest.fixture
async def auth_client(app, current_user, mock_db):
    async def _override_user():
        return current_user

    async def _override_db():
        yield mock_db

    app.dependency_overrides[get_current_active_user] = _override_user
    app.dependency_overrides[get_db] = _override_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


# ── POST /notifications ───────────────────────────────────────────────────────


class TestCreateNotificationConfig:
    async def test_creates_config_201(self, auth_client, mock_db, current_user):
        created_cfg = _make_notification_config()

        # db.refresh must populate the object returned from the endpoint
        async def _refresh(obj):
            for k, v in vars(created_cfg).items():
                if not k.startswith("_"):
                    try:
                        setattr(obj, k, v)
                    except AttributeError:
                        pass

        mock_db.refresh = AsyncMock(side_effect=_refresh)

        response = await auth_client.post(
            "/api/v1/notifications",
            json={
                "name": "My Webhook",
                "apprise_url": "json://localhost",
                "channel": "webhook",
                "is_enabled": True,
                "config": {},
                "notify_on_errors": True,
                "notify_on_success": False,
                "notify_threshold": 3,
            },
        )
        assert response.status_code == 201

    async def test_unauthenticated_401(self, app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/notifications",
                json={
                    "name": "x",
                    "apprise_url": "json://localhost",
                    "channel": "webhook",
                    "config": {},
                },
            )
        assert response.status_code == 401


# ── GET /notifications ────────────────────────────────────────────────────────


class TestListNotificationConfigs:
    async def test_returns_list(self, auth_client, mock_db):
        cfg1 = _make_notification_config(id=1)
        cfg2 = _make_notification_config(id=2)
        mock_db.execute = AsyncMock(return_value=_scalars_all([cfg1, cfg2]))
        response = await auth_client.get("/api/v1/notifications")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        assert len(response.json()) == 2

    async def test_returns_empty_list(self, auth_client, mock_db):
        mock_db.execute = AsyncMock(return_value=_scalars_all([]))
        response = await auth_client.get("/api/v1/notifications")
        assert response.status_code == 200
        assert response.json() == []


# ── GET /notifications/{id} ───────────────────────────────────────────────────


class TestGetNotificationConfig:
    async def test_returns_config(self, auth_client, mock_db):
        cfg = _make_notification_config(id=5)
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(cfg))
        response = await auth_client.get("/api/v1/notifications/5")
        assert response.status_code == 200

    async def test_404_when_not_found(self, auth_client, mock_db):
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(None))
        response = await auth_client.get("/api/v1/notifications/999")
        assert response.status_code == 404


# ── PUT /notifications/{id} ───────────────────────────────────────────────────


class TestUpdateNotificationConfig:
    async def test_updates_config(self, auth_client, mock_db):
        cfg = _make_notification_config(id=5)
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(cfg))
        mock_db.refresh = AsyncMock(side_effect=lambda obj: None)

        response = await auth_client.put(
            "/api/v1/notifications/5",
            json={"name": "Updated Name"},
        )
        assert response.status_code == 200

    async def test_404_when_not_found(self, auth_client, mock_db):
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(None))
        response = await auth_client.put(
            "/api/v1/notifications/999",
            json={"name": "Updated"},
        )
        assert response.status_code == 404


# ── DELETE /notifications/{id} ────────────────────────────────────────────────


class TestDeleteNotificationConfig:
    async def test_deletes_config_204(self, auth_client, mock_db):
        cfg = _make_notification_config(id=5)
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(cfg))
        response = await auth_client.delete("/api/v1/notifications/5")
        assert response.status_code == 204
        mock_db.delete.assert_awaited_once_with(cfg)

    async def test_404_when_not_found(self, auth_client, mock_db):
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(None))
        response = await auth_client.delete("/api/v1/notifications/999")
        assert response.status_code == 404


# ── POST /notifications/test ──────────────────────────────────────────────────


class TestTestNotificationConfig:
    async def test_test_success(self, auth_client):
        with patch(
            "app.api.v1.endpoints.notifications.test_notification",
            new=AsyncMock(return_value=(True, "sent successfully")),
        ):
            response = await auth_client.post(
                "/api/v1/notifications/test",
                json={"apprise_url": "json://localhost"},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    async def test_test_failure(self, auth_client):
        with patch(
            "app.api.v1.endpoints.notifications.test_notification",
            new=AsyncMock(return_value=(False, "delivery failed")),
        ):
            response = await auth_client.post(
                "/api/v1/notifications/test",
                json={"apprise_url": "invalid://url"},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
