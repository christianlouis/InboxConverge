"""
Unit tests for auth endpoints (backend/app/api/v1/endpoints/auth.py).

All tests mock the database session, security functions, and OAuth service
so no real PostgreSQL instance or external API is required.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import quote as urlquote

from httpx import AsyncClient, ASGITransport

from app.main import create_application
from app.core.database import get_db
from app.models.database_models import User, SubscriptionTier

# ── helpers ──────────────────────────────────────────────────────────────


def _make_user(**overrides) -> MagicMock:
    """Return a MagicMock that behaves like a User ORM instance."""
    defaults = dict(
        id=1,
        email="user@example.com",
        hashed_password="hashedpw",
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
    user = MagicMock(spec=User)
    for k, v in defaults.items():
        setattr(user, k, v)
    return user


def _scalar_one_or_none(value):
    """Create a mock result whose .scalar_one_or_none() returns *value*."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _fake_tokens():
    return {
        "access_token": "fake-access-token",
        "refresh_token": "fake-refresh-token",
        "token_type": "bearer",
    }


# ── fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture
def app():
    return create_application()


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.delete = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.fixture
async def client(app, mock_db):
    """AsyncClient with only get_db overridden (no auth required)."""

    async def _override_db():
        yield mock_db

    app.dependency_overrides[get_db] = _override_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()


# ═══════════════════════════════════════════════════════════════════════════
# Helper functions
# ═══════════════════════════════════════════════════════════════════════════


class TestHelpers:
    """Unit tests for private helper functions in auth.py."""

    def test_domain_of(self):
        from app.api.v1.endpoints.auth import _domain_of

        assert _domain_of("alice@Example.COM") == "example.com"
        assert _domain_of("bob@sub.domain.org") == "sub.domain.org"

    @patch("app.api.v1.endpoints.auth.settings")
    def test_check_domain_allowed_no_restriction(self, mock_settings):
        from app.api.v1.endpoints.auth import _check_domain_allowed

        mock_settings.ALLOWED_DOMAINS = []
        _check_domain_allowed("anyone@whatever.com")  # should not raise

    @patch("app.api.v1.endpoints.auth.settings")
    def test_check_domain_allowed_passes(self, mock_settings):
        from app.api.v1.endpoints.auth import _check_domain_allowed

        mock_settings.ALLOWED_DOMAINS = ["acme.com"]
        _check_domain_allowed("alice@acme.com")  # should not raise

    @patch("app.api.v1.endpoints.auth.settings")
    def test_check_domain_allowed_blocks(self, mock_settings):
        from fastapi import HTTPException

        from app.api.v1.endpoints.auth import _check_domain_allowed

        mock_settings.ALLOWED_DOMAINS = ["acme.com"]
        with pytest.raises(HTTPException) as exc_info:
            _check_domain_allowed("alice@blocked.com")
        assert exc_info.value.status_code == 403

    @patch("app.api.v1.endpoints.auth.settings")
    def test_default_tier_valid(self, mock_settings):
        from app.api.v1.endpoints.auth import _default_tier

        mock_settings.DEFAULT_USER_TIER = "pro"
        assert _default_tier() == SubscriptionTier.PRO

    @patch("app.api.v1.endpoints.auth.settings")
    def test_default_tier_invalid_falls_back(self, mock_settings):
        from app.api.v1.endpoints.auth import _default_tier

        mock_settings.DEFAULT_USER_TIER = "invalid_tier"
        assert _default_tier() == SubscriptionTier.FREE

    @patch("app.api.v1.endpoints.auth.settings")
    def test_is_admin_email_match(self, mock_settings):
        from app.api.v1.endpoints.auth import _is_admin_email

        mock_settings.ADMIN_EMAIL = "Admin@Example.com"
        assert _is_admin_email("admin@example.com") is True

    @patch("app.api.v1.endpoints.auth.settings")
    def test_is_admin_email_no_match(self, mock_settings):
        from app.api.v1.endpoints.auth import _is_admin_email

        mock_settings.ADMIN_EMAIL = "admin@example.com"
        assert _is_admin_email("other@example.com") is False

    @patch("app.api.v1.endpoints.auth.settings")
    def test_is_admin_email_none(self, mock_settings):
        from app.api.v1.endpoints.auth import _is_admin_email

        mock_settings.ADMIN_EMAIL = None
        assert _is_admin_email("anyone@example.com") is False


# ═══════════════════════════════════════════════════════════════════════════
# POST /api/v1/auth/register
# ═══════════════════════════════════════════════════════════════════════════


class TestRegister:

    @patch("app.api.v1.endpoints.auth.settings")
    @patch("app.api.v1.endpoints.auth.get_password_hash", return_value="hashed123")
    async def test_register_success(self, _mock_hash, mock_settings, client, mock_db):
        mock_settings.ALLOWED_DOMAINS = []
        mock_settings.DEFAULT_USER_TIER = "free"
        mock_settings.ADMIN_EMAIL = None

        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(None))

        # Simulate db.refresh assigning an id and required fields
        def _set_id(obj):
            obj.id = 42
            obj.email = "new@example.com"
            obj.full_name = "New User"
            obj.is_active = True
            obj.subscription_tier = SubscriptionTier.FREE
            obj.subscription_status = "active"
            obj.created_at = datetime.now(timezone.utc)

        mock_db.refresh = AsyncMock(side_effect=_set_id)

        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "new@example.com",
                "full_name": "New User",
                "password": "secret",
            },
        )

        assert resp.status_code == 201
        body = resp.json()
        assert body["email"] == "new@example.com"
        assert body["id"] == 42
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited_once()

    async def test_register_duplicate_email(self, client, mock_db):
        existing = _make_user(email="dup@example.com")
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(existing))

        resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "dup@example.com", "full_name": "Dup", "password": "pw"},
        )

        assert resp.status_code == 400
        assert "already registered" in resp.json()["detail"]

    @patch("app.api.v1.endpoints.auth.settings")
    async def test_register_domain_restricted(self, mock_settings, client, mock_db):
        mock_settings.ALLOWED_DOMAINS = ["acme.com"]

        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(None))

        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "user@blocked.com",
                "full_name": "Blocked",
                "password": "pw",
            },
        )

        assert resp.status_code == 403
        assert "not authorised" in resp.json()["detail"]


# ═══════════════════════════════════════════════════════════════════════════
# POST /api/v1/auth/login
# ═══════════════════════════════════════════════════════════════════════════


class TestLogin:

    @patch("app.api.v1.endpoints.auth.settings")
    @patch(
        "app.api.v1.endpoints.auth.oauth_service.create_tokens_for_user",
        return_value=_fake_tokens(),
    )
    @patch("app.api.v1.endpoints.auth.verify_password", return_value=True)
    async def test_login_success(
        self, _mock_verify, _mock_tokens, mock_settings, client, mock_db
    ):
        mock_settings.ALLOWED_DOMAINS = []
        mock_settings.ADMIN_EMAIL = None

        user = _make_user(email="login@example.com")
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(user))

        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": "login@example.com", "password": "correct"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["access_token"] == "fake-access-token"
        assert body["token_type"] == "bearer"
        mock_db.commit.assert_awaited_once()

    @patch("app.api.v1.endpoints.auth.verify_password", return_value=False)
    async def test_login_user_not_found(self, _mock_verify, client, mock_db):
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(None))

        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": "nobody@example.com", "password": "pw"},
        )

        assert resp.status_code == 401
        assert "Incorrect email or password" in resp.json()["detail"]

    @patch("app.api.v1.endpoints.auth.verify_password", return_value=False)
    async def test_login_wrong_password(self, _mock_verify, client, mock_db):
        user = _make_user(email="login@example.com")
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(user))

        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": "login@example.com", "password": "wrong"},
        )

        assert resp.status_code == 401
        assert "Incorrect email or password" in resp.json()["detail"]

    @patch("app.api.v1.endpoints.auth.verify_password", return_value=True)
    async def test_login_inactive_user(self, _mock_verify, client, mock_db):
        user = _make_user(email="inactive@example.com", is_active=False)
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(user))

        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": "inactive@example.com", "password": "pw"},
        )

        assert resp.status_code == 403
        assert "inactive" in resp.json()["detail"]

    @patch("app.api.v1.endpoints.auth.settings")
    @patch(
        "app.api.v1.endpoints.auth.oauth_service.create_tokens_for_user",
        return_value=_fake_tokens(),
    )
    @patch("app.api.v1.endpoints.auth.verify_password", return_value=True)
    async def test_login_admin_auto_promotion(
        self, _mock_verify, _mock_tokens, mock_settings, client, mock_db
    ):
        mock_settings.ALLOWED_DOMAINS = []
        mock_settings.ADMIN_EMAIL = "admin@example.com"

        user = _make_user(email="admin@example.com", is_superuser=False, is_active=True)
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(user))

        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": "admin@example.com", "password": "pw"},
        )

        assert resp.status_code == 200
        # The endpoint should have set is_superuser = True on the user mock
        assert user.is_superuser is True


# ═══════════════════════════════════════════════════════════════════════════
# POST /api/v1/auth/google
# ═══════════════════════════════════════════════════════════════════════════


class TestGoogleOAuth:

    @patch("app.api.v1.endpoints.auth.settings")
    @patch(
        "app.api.v1.endpoints.auth.oauth_service.create_tokens_for_user",
        return_value=_fake_tokens(),
    )
    @patch("app.api.v1.endpoints.auth.oauth_service.get_google_user_info")
    async def test_google_existing_user(
        self, mock_google_info, _mock_tokens, mock_settings, client, mock_db
    ):
        mock_settings.ALLOWED_DOMAINS = []
        mock_settings.ADMIN_EMAIL = None

        mock_google_info.return_value = {
            "email": "existing@example.com",
            "google_id": "g-123",
            "full_name": "Existing User",
            "verified_email": True,
        }

        user = _make_user(email="existing@example.com", google_id="g-123")
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(user))

        resp = await client.post(
            "/api/v1/auth/google",
            json={"code": "auth-code", "redirect_uri": "http://localhost/callback"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["access_token"] == "fake-access-token"
        mock_db.commit.assert_awaited_once()

    @patch("app.api.v1.endpoints.auth.settings")
    @patch(
        "app.api.v1.endpoints.auth.oauth_service.create_tokens_for_user",
        return_value=_fake_tokens(),
    )
    @patch("app.api.v1.endpoints.auth.oauth_service.get_google_user_info")
    async def test_google_new_user(
        self, mock_google_info, _mock_tokens, mock_settings, client, mock_db
    ):
        mock_settings.ALLOWED_DOMAINS = []
        mock_settings.DEFAULT_USER_TIER = "free"
        mock_settings.ADMIN_EMAIL = None

        mock_google_info.return_value = {
            "email": "brand-new@example.com",
            "google_id": "g-456",
            "full_name": "Brand New",
            "verified_email": True,
        }

        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(None))

        def _set_id(obj):
            obj.id = 99

        mock_db.refresh = AsyncMock(side_effect=_set_id)

        resp = await client.post(
            "/api/v1/auth/google",
            json={"code": "auth-code", "redirect_uri": "http://localhost/callback"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["access_token"] == "fake-access-token"
        mock_db.add.assert_called_once()

    @patch("app.api.v1.endpoints.auth.oauth_service.get_google_user_info")
    async def test_google_email_not_verified(self, mock_google_info, client, mock_db):
        mock_google_info.return_value = {
            "email": "unverified@example.com",
            "google_id": "g-789",
            "verified_email": False,
        }

        resp = await client.post(
            "/api/v1/auth/google",
            json={"code": "auth-code", "redirect_uri": "http://localhost/callback"},
        )

        assert resp.status_code == 400
        assert "not verified" in resp.json()["detail"]

    @patch("app.api.v1.endpoints.auth.settings")
    @patch("app.api.v1.endpoints.auth.oauth_service.get_google_user_info")
    async def test_google_domain_restricted_new_user(
        self, mock_google_info, mock_settings, client, mock_db
    ):
        mock_settings.ALLOWED_DOMAINS = ["acme.com"]
        mock_settings.DEFAULT_USER_TIER = "free"
        mock_settings.ADMIN_EMAIL = None

        mock_google_info.return_value = {
            "email": "person@blocked.com",
            "google_id": "g-block",
            "full_name": "Blocked",
            "verified_email": True,
        }

        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(None))

        resp = await client.post(
            "/api/v1/auth/google",
            json={"code": "auth-code", "redirect_uri": "http://localhost/callback"},
        )

        assert resp.status_code == 403
        assert "not authorised" in resp.json()["detail"]


# ═══════════════════════════════════════════════════════════════════════════
# GET /api/v1/auth/google/authorize-url
# ═══════════════════════════════════════════════════════════════════════════


class TestGoogleAuthorizeUrl:

    @patch("app.api.v1.endpoints.auth.settings")
    async def test_returns_correct_url(self, mock_settings, client):
        mock_settings.GOOGLE_CLIENT_ID = "test-client-id"

        resp = await client.get(
            "/api/v1/auth/google/authorize-url",
            params={"redirect_uri": "http://localhost:3000/callback"},
        )

        assert resp.status_code == 200
        body = resp.json()
        url = body["authorization_url"]
        assert "accounts.google.com" in url
        assert "client_id=test-client-id" in url
        assert "redirect_uri=http://localhost:3000/callback" in url
        expected_scope = urlquote("openid email profile")
        assert f"scope={expected_scope}" in url
        assert "prompt=select_account" in url
