"""
Unit tests for user profile and SMTP config endpoints (api/v1/endpoints/users.py).

All database interactions and auth dependencies are mocked.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from httpx import AsyncClient, ASGITransport

from app.main import create_application
from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.models.database_models import User, UserSmtpConfig, SubscriptionTier

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


def _make_smtp_config(**overrides) -> MagicMock:
    defaults = dict(
        id=1,
        user_id=1,
        host="smtp.example.com",
        port=587,
        username="user@example.com",
        encrypted_password="encrypted",
        use_tls=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    cfg = MagicMock(spec=UserSmtpConfig)
    for k, v in defaults.items():
        setattr(cfg, k, v)
    return cfg


def _scalar_one_or_none(value):
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
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


# ── GET /me ───────────────────────────────────────────────────────────────────


class TestGetMe:
    async def test_returns_user_data(self, auth_client, current_user):
        response = await auth_client.get("/api/v1/users/me")
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == current_user.email

    async def test_unauthenticated_401(self, app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/users/me")
        assert response.status_code == 401


# ── PUT /me ───────────────────────────────────────────────────────────────────


class TestUpdateMe:
    async def test_update_full_name(self, auth_client, mock_db, current_user):
        mock_db.refresh = AsyncMock(
            side_effect=lambda obj: setattr(obj, "full_name", "Updated Name")
        )
        response = await auth_client.put(
            "/api/v1/users/me", json={"full_name": "Updated Name"}
        )
        assert response.status_code == 200

    async def test_update_email(self, auth_client, mock_db, current_user):
        mock_db.refresh = AsyncMock(
            side_effect=lambda obj: setattr(obj, "email", "new@example.com")
        )
        response = await auth_client.put(
            "/api/v1/users/me", json={"email": "new@example.com"}
        )
        assert response.status_code == 200


# ── GET /smtp-config ──────────────────────────────────────────────────────────


class TestGetSmtpConfig:
    async def test_returns_config_when_exists(self, auth_client, mock_db):
        cfg = _make_smtp_config()
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(cfg))
        response = await auth_client.get("/api/v1/users/smtp-config")
        assert response.status_code == 200
        data = response.json()
        assert data["host"] == "smtp.example.com"
        assert data["port"] == 587
        assert "has_password" in data
        # Password must not be exposed
        assert "encrypted_password" not in data

    async def test_returns_404_when_no_config(self, auth_client, mock_db):
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(None))
        response = await auth_client.get("/api/v1/users/smtp-config")
        assert response.status_code == 404


# ── PUT /smtp-config ──────────────────────────────────────────────────────────


class TestUpsertSmtpConfig:
    async def test_creates_new_config(self, auth_client, mock_db):
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(None))

        # db.refresh populates the new config object with required fields
        async def _refresh(obj):
            obj.id = 1
            obj.user_id = 1
            obj.host = "smtp.example.com"
            obj.port = 587
            obj.username = "user@example.com"
            obj.encrypted_password = "encrypted"
            obj.use_tls = True
            obj.created_at = datetime.now(timezone.utc)
            obj.updated_at = datetime.now(timezone.utc)

        mock_db.refresh = AsyncMock(side_effect=_refresh)

        from unittest.mock import patch

        with patch(
            "app.api.v1.endpoints.users.encrypt_credential", return_value="encrypted"
        ):
            response = await auth_client.put(
                "/api/v1/users/smtp-config",
                json={
                    "host": "smtp.example.com",
                    "port": 587,
                    "username": "user@example.com",
                    "password": "secret",
                    "use_tls": True,
                },
            )
        assert response.status_code == 200

    async def test_updates_existing_config(self, auth_client, mock_db):
        existing = _make_smtp_config()
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(existing))
        mock_db.refresh = AsyncMock(side_effect=lambda obj: None)

        from unittest.mock import patch

        with patch(
            "app.api.v1.endpoints.users.encrypt_credential", return_value="encrypted"
        ):
            response = await auth_client.put(
                "/api/v1/users/smtp-config",
                json={
                    "host": "newsmtp.example.com",
                    "port": 465,
                    "username": "newuser@example.com",
                    "password": "newpass",
                    "use_tls": False,
                },
            )
        assert response.status_code == 200


# ── DELETE /smtp-config ───────────────────────────────────────────────────────


class TestDeleteSmtpConfig:
    async def test_deletes_existing_config(self, auth_client, mock_db):
        existing = _make_smtp_config()
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(existing))
        response = await auth_client.delete("/api/v1/users/smtp-config")
        assert response.status_code == 204
        mock_db.delete.assert_awaited_once_with(existing)

    async def test_no_config_is_noop(self, auth_client, mock_db):
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(None))
        response = await auth_client.delete("/api/v1/users/smtp-config")
        assert response.status_code == 204
        mock_db.delete.assert_not_awaited()
