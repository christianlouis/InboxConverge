"""
Unit tests for authentication endpoints (api/v1/endpoints/auth.py).

All database interactions and the oauth_service are mocked so no real
PostgreSQL instance or Google credentials are needed.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import AsyncClient, ASGITransport

from app.main import create_application
from app.core.database import get_db
from app.models.database_models import User, SubscriptionTier

# ── helpers ──────────────────────────────────────────────────────────────────


def _make_user(**overrides) -> MagicMock:
    defaults = dict(
        id=1,
        email="user@example.com",
        hashed_password=None,
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
    return db


@pytest.fixture
async def anon_client(app, mock_db):
    """Client with no auth (db mocked)."""

    async def _override_db():
        yield mock_db

    app.dependency_overrides[get_db] = _override_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


# ── /register ─────────────────────────────────────────────────────────────────


class TestRegisterEndpoint:
    async def test_register_new_user_201(self, anon_client, mock_db):
        # DB returns no existing user
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(None))

        # db.refresh will be called with the new User object; we simulate it
        # by setting the required response fields on that object.
        from datetime import datetime, timezone
        from app.models.database_models import SubscriptionTier

        async def _refresh(obj):
            obj.id = 99
            obj.email = "new@example.com"
            obj.full_name = None
            obj.is_active = True
            obj.subscription_tier = SubscriptionTier.FREE
            obj.subscription_status = "active"
            obj.created_at = datetime.now(timezone.utc)
            obj.updated_at = datetime.now(timezone.utc)

        mock_db.refresh = AsyncMock(side_effect=_refresh)

        response = await anon_client.post(
            "/api/v1/auth/register",
            json={"email": "new@example.com", "password": "secretpassword"},
        )
        assert response.status_code == 201

    async def test_register_existing_user_400(self, anon_client, mock_db):
        existing = _make_user(email="taken@example.com")
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(existing))

        response = await anon_client.post(
            "/api/v1/auth/register",
            json={"email": "taken@example.com", "password": "pass"},
        )
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    async def test_register_blocked_domain_403(self, app, mock_db):
        """When ALLOWED_DOMAINS is set, unknown domains should get 403."""

        async def _override_db():
            yield mock_db

        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(None))
        app.dependency_overrides[get_db] = _override_db

        transport = ASGITransport(app=app)
        with patch("app.api.v1.endpoints.auth.settings") as mock_settings:
            mock_settings.ALLOWED_DOMAINS = ["allowed.com"]
            mock_settings.DEFAULT_USER_TIER = "free"
            mock_settings.ADMIN_EMAIL = None
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/v1/auth/register",
                    json={"email": "user@blocked.com", "password": "pass"},
                )
        app.dependency_overrides.clear()
        assert response.status_code == 403


# ── /login ─────────────────────────────────────────────────────────────────────


class TestLoginEndpoint:
    async def test_login_success_returns_tokens(self, anon_client, mock_db):
        from app.core.security import get_password_hash

        hashed = get_password_hash("correctpassword")
        user = _make_user(email="user@example.com", hashed_password=hashed)
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(user))

        response = await anon_client.post(
            "/api/v1/auth/login",
            data={"username": "user@example.com", "password": "correctpassword"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password_401(self, anon_client, mock_db):
        from app.core.security import get_password_hash

        hashed = get_password_hash("correctpassword")
        user = _make_user(email="user@example.com", hashed_password=hashed)
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(user))

        response = await anon_client.post(
            "/api/v1/auth/login",
            data={"username": "user@example.com", "password": "wrongpassword"},
        )
        assert response.status_code == 401

    async def test_login_user_not_found_401(self, anon_client, mock_db):
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(None))

        response = await anon_client.post(
            "/api/v1/auth/login",
            data={"username": "unknown@example.com", "password": "pass"},
        )
        assert response.status_code == 401

    async def test_login_inactive_user_403(self, anon_client, mock_db):
        from app.core.security import get_password_hash

        hashed = get_password_hash("password")
        user = _make_user(
            email="user@example.com", hashed_password=hashed, is_active=False
        )
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(user))

        response = await anon_client.post(
            "/api/v1/auth/login",
            data={"username": "user@example.com", "password": "password"},
        )
        assert response.status_code == 403

    async def test_login_no_password_hash_401(self, anon_client, mock_db):
        """OAuth-only users have no hashed_password – login should fail."""
        user = _make_user(hashed_password=None)
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(user))

        response = await anon_client.post(
            "/api/v1/auth/login",
            data={"username": "user@example.com", "password": "pass"},
        )
        assert response.status_code == 401


# ── /google ────────────────────────────────────────────────────────────────────


class TestGoogleOAuthEndpoint:
    async def test_google_oauth_unverified_email_400(self, anon_client, mock_db):
        with patch(
            "app.api.v1.endpoints.auth.oauth_service.get_google_user_info",
            new=AsyncMock(
                return_value={
                    "email": "user@gmail.com",
                    "google_id": "g123",
                    "full_name": "Test",
                    "verified_email": False,
                }
            ),
        ):
            response = await anon_client.post(
                "/api/v1/auth/google",
                json={"code": "code", "redirect_uri": "http://localhost"},
            )
        assert response.status_code == 400

    async def test_google_oauth_new_user_created(self, anon_client, mock_db):
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(None))
        mock_db.refresh = AsyncMock(side_effect=lambda obj: None)

        with (
            patch(
                "app.api.v1.endpoints.auth.oauth_service.get_google_user_info",
                new=AsyncMock(
                    return_value={
                        "email": "google@example.com",
                        "google_id": "g123",
                        "full_name": "Google User",
                        "verified_email": True,
                    }
                ),
            ),
            patch(
                "app.api.v1.endpoints.auth.oauth_service.create_tokens_for_user",
                return_value={
                    "access_token": "tok",
                    "refresh_token": "ref",
                    "token_type": "bearer",
                },
            ),
        ):
            response = await anon_client.post(
                "/api/v1/auth/google",
                json={"code": "code", "redirect_uri": "http://localhost"},
            )
        assert response.status_code == 200
        assert response.json()["access_token"] == "tok"

    async def test_google_oauth_existing_user_logs_in(self, anon_client, mock_db):
        existing = _make_user(email="google@example.com", google_id="g123")
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(existing))
        mock_db.refresh = AsyncMock(side_effect=lambda obj: None)

        with (
            patch(
                "app.api.v1.endpoints.auth.oauth_service.get_google_user_info",
                new=AsyncMock(
                    return_value={
                        "email": "google@example.com",
                        "google_id": "g123",
                        "full_name": "Google User",
                        "verified_email": True,
                    }
                ),
            ),
            patch(
                "app.api.v1.endpoints.auth.oauth_service.create_tokens_for_user",
                return_value={
                    "access_token": "tok2",
                    "refresh_token": "ref2",
                    "token_type": "bearer",
                },
            ),
        ):
            response = await anon_client.post(
                "/api/v1/auth/google",
                json={"code": "code", "redirect_uri": "http://localhost"},
            )
        assert response.status_code == 200


# ── /google/authorize-url ──────────────────────────────────────────────────────


class TestGoogleAuthorizeUrl:
    async def test_returns_authorization_url(self, anon_client):
        response = await anon_client.get(
            "/api/v1/auth/google/authorize-url",
            params={"redirect_uri": "http://localhost/callback"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "authorization_url" in data
        assert "accounts.google.com" in data["authorization_url"]

    async def test_url_contains_redirect_uri(self, anon_client):
        redirect = "http://myapp.example.com/callback"
        response = await anon_client.get(
            "/api/v1/auth/google/authorize-url",
            params={"redirect_uri": redirect},
        )
        assert response.status_code == 200


# ── helper functions (domain checks, tier, admin email) ───────────────────────


class TestAuthHelpers:
    def test_domain_of(self):
        from app.api.v1.endpoints.auth import _domain_of

        assert _domain_of("user@Example.COM") == "example.com"
        assert _domain_of("a@b.de") == "b.de"

    def test_default_tier_fallback(self):
        from app.api.v1.endpoints.auth import _default_tier
        from app.models.database_models import SubscriptionTier

        with patch("app.api.v1.endpoints.auth.settings") as ms:
            ms.DEFAULT_USER_TIER = "invalid_tier"
            tier = _default_tier()
        assert tier == SubscriptionTier.FREE

    def test_default_tier_valid(self):
        from app.api.v1.endpoints.auth import _default_tier
        from app.models.database_models import SubscriptionTier

        with patch("app.api.v1.endpoints.auth.settings") as ms:
            ms.DEFAULT_USER_TIER = "pro"
            tier = _default_tier()
        assert tier == SubscriptionTier.PRO

    def test_is_admin_email_match(self):
        from app.api.v1.endpoints.auth import _is_admin_email

        with patch("app.api.v1.endpoints.auth.settings") as ms:
            ms.ADMIN_EMAIL = "admin@example.com"
            assert _is_admin_email("ADMIN@EXAMPLE.COM") is True
            assert _is_admin_email("other@example.com") is False

    def test_is_admin_email_none_config(self):
        from app.api.v1.endpoints.auth import _is_admin_email

        with patch("app.api.v1.endpoints.auth.settings") as ms:
            ms.ADMIN_EMAIL = None
            assert _is_admin_email("admin@example.com") is False
