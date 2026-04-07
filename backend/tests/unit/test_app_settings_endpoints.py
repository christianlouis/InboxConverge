"""
Unit tests for app settings endpoints (api/v1/endpoints/app_settings.py).

All database interactions and auth dependencies are mocked.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import AsyncClient, ASGITransport

from app.main import create_application
from app.core.database import get_db
from app.core.deps import get_current_superuser, get_current_user
from app.models.database_models import User, SubscriptionTier

# ── helpers ──────────────────────────────────────────────────────────────────


def _make_admin_user(**overrides) -> MagicMock:
    defaults = dict(
        id=1,
        email="admin@example.com",
        full_name="Admin",
        is_active=True,
        is_superuser=True,
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


def _make_setting(**overrides) -> MagicMock:
    defaults = dict(
        id=1,
        key="SOME_SETTING",
        value="some_value",
        value_type="string",
        description="A setting",
        is_secret=False,
        category="general",
    )
    defaults.update(overrides)
    s = MagicMock()
    for k, v in defaults.items():
        setattr(s, k, v)
    return s


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
def admin_user():
    return _make_admin_user()


@pytest.fixture
async def admin_client(app, admin_user, mock_db):
    async def _override_superuser():
        return admin_user

    async def _override_db():
        yield mock_db

    app.dependency_overrides[get_current_superuser] = _override_superuser
    app.dependency_overrides[get_current_user] = _override_superuser
    app.dependency_overrides[get_db] = _override_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


# ── GET /app-settings ─────────────────────────────────────────────────────────


class TestListSettings:
    async def test_returns_list(self, admin_client):
        setting = _make_setting()
        with patch(
            "app.api.v1.endpoints.app_settings.ConfigService.list_all",
            new=AsyncMock(return_value=[setting]),
        ):
            response = await admin_client.get("/api/v1/settings")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["key"] == "SOME_SETTING"
        assert data[0]["value"] == "some_value"

    async def test_secret_value_masked(self, admin_client):
        setting = _make_setting(key="SECRET_KEY", value="supersecret", is_secret=True)
        with patch(
            "app.api.v1.endpoints.app_settings.ConfigService.list_all",
            new=AsyncMock(return_value=[setting]),
        ):
            response = await admin_client.get("/api/v1/settings")
        assert response.status_code == 200
        data = response.json()
        assert data[0]["value"] == "********"

    async def test_filters_by_category(self, admin_client):
        with patch(
            "app.api.v1.endpoints.app_settings.ConfigService.list_all",
            new=AsyncMock(return_value=[]),
        ):
            response = await admin_client.get("/api/v1/settings?category=general")
        assert response.status_code == 200

    async def test_unauthenticated_401(self, app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/settings")
        assert response.status_code == 401


# ── PUT /app-settings/{key} ───────────────────────────────────────────────────


class TestUpsertSetting:
    async def test_upsert_creates_or_updates(self, admin_client):
        setting = _make_setting(key="MY_KEY", value="myval")
        with patch(
            "app.api.v1.endpoints.app_settings.ConfigService.set",
            new=AsyncMock(return_value=setting),
        ):
            response = await admin_client.put(
                "/api/v1/settings/MY_KEY",
                json={
                    "key": "MY_KEY",
                    "value": "myval",
                    "value_type": "string",
                    "is_secret": False,
                },
            )
        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "MY_KEY"
        assert data["value"] == "myval"

    async def test_bootstrap_key_rejected_400(self, admin_client):
        response = await admin_client.put(
            "/api/v1/settings/SECRET_KEY",
            json={"key": "SECRET_KEY", "value": "new_secret"},
        )
        assert response.status_code == 400
        assert "bootstrap" in response.json()["detail"].lower()

    async def test_database_url_rejected(self, admin_client):
        response = await admin_client.put(
            "/api/v1/settings/DATABASE_URL",
            json={"key": "DATABASE_URL", "value": "postgresql://..."},
        )
        assert response.status_code == 400

    async def test_secret_value_masked_in_response(self, admin_client):
        setting = _make_setting(key="API_KEY", value="secret!", is_secret=True)
        with patch(
            "app.api.v1.endpoints.app_settings.ConfigService.set",
            new=AsyncMock(return_value=setting),
        ):
            response = await admin_client.put(
                "/api/v1/settings/API_KEY",
                json={
                    "key": "API_KEY",
                    "value": "secret!",
                    "is_secret": True,
                },
            )
        assert response.status_code == 200
        assert response.json()["value"] == "********"


# ── DELETE /app-settings/{key} ────────────────────────────────────────────────


class TestDeleteSetting:
    async def test_deletes_existing_setting(self, admin_client):
        with patch(
            "app.api.v1.endpoints.app_settings.ConfigService.delete",
            new=AsyncMock(return_value=True),
        ):
            response = await admin_client.delete("/api/v1/settings/MY_KEY")
        assert response.status_code == 204

    async def test_404_when_not_found(self, admin_client):
        with patch(
            "app.api.v1.endpoints.app_settings.ConfigService.delete",
            new=AsyncMock(return_value=False),
        ):
            response = await admin_client.delete("/api/v1/settings/MISSING_KEY")
        assert response.status_code == 404

    async def test_bootstrap_key_rejected_400(self, admin_client):
        response = await admin_client.delete("/api/v1/settings/SECRET_KEY")
        assert response.status_code == 400


# ── POST /app-settings/seed-defaults ─────────────────────────────────────────


class TestSeedDefaultSettings:
    async def test_seeds_defaults(self, admin_client):
        with patch(
            "app.api.v1.endpoints.app_settings.ConfigService.seed_defaults",
            new=AsyncMock(return_value=5),
        ):
            response = await admin_client.post("/api/v1/settings/seed-defaults")
        assert response.status_code == 200
        data = response.json()
        assert data["created"] == 5
        assert "Seeded 5" in data["message"]
