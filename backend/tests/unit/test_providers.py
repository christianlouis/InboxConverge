"""
Unit tests for provider endpoints (backend/app/api/v1/endpoints/providers.py).

All tests mock the database session, auth dependencies, and external services
so no real PostgreSQL instance or Google API access is required.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import AsyncClient, ASGITransport

from app.main import create_application
from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.models.database_models import User, GmailCredential
from app.services.gmail_service import GmailInjectionError

# ── helpers ──────────────────────────────────────────────────────────────


def _make_user(**overrides) -> MagicMock:
    """Return a MagicMock that behaves like a User ORM instance."""
    defaults = dict(
        id=1,
        email="user@example.com",
        hashed_password="hashed",
        full_name="Test User",
        is_active=True,
        is_superuser=False,
        google_id=None,
        oauth_provider=None,
        last_login_at=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    user = MagicMock(spec=User)
    for k, v in defaults.items():
        setattr(user, k, v)
    return user


def _make_gmail_credential(**overrides) -> MagicMock:
    """Return a MagicMock that behaves like a GmailCredential ORM instance."""
    defaults = dict(
        id=1,
        user_id=1,
        gmail_email="user@gmail.com",
        encrypted_access_token="encrypted_access",
        encrypted_refresh_token="encrypted_refresh",
        token_expiry=datetime.now(timezone.utc),
        scopes={
            "granted_scopes": ["scope1"],
            "import_label_templates": ["imported"],
        },
        is_valid=True,
        last_verified_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        import_label_templates=["imported"],
        default_import_label_templates=["{{source_email}}", "imported"],
        granted_scopes=["scope1"],
    )
    defaults.update(overrides)
    cred = MagicMock(spec=GmailCredential)
    for k, v in defaults.items():
        setattr(cred, k, v)
    return cred


def _scalar_one_or_none(value):
    """Create a mock result whose .scalar_one_or_none() returns *value*."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


# ── fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture
def app():
    return create_application()


@pytest.fixture
def test_user():
    return _make_user()


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.delete = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.fixture
async def auth_client(app, test_user, mock_db):
    """AsyncClient where the caller is an authenticated active user."""

    async def _override_user():
        return test_user

    async def _override_db():
        yield mock_db

    app.dependency_overrides[get_current_active_user] = _override_user
    app.dependency_overrides[get_db] = _override_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


# ═══════════════════════════════════════════════════════════════════════════
# Provider Presets
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestListProviderPresets:
    async def test_returns_all_presets(self, auth_client):
        resp = await auth_client.get("/api/v1/providers/presets")
        assert resp.status_code == 200
        data = resp.json()
        assert "providers" in data
        assert len(data["providers"]) == 13
        ids = [p["id"] for p in data["providers"]]
        assert "gmail" in ids
        assert "outlook" in ids
        assert "icloud" in ids


@pytest.mark.asyncio
class TestGetProviderPreset:
    async def test_known_preset(self, auth_client):
        resp = await auth_client.get("/api/v1/providers/presets/gmail")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "gmail"
        assert data["name"] == "Gmail"
        assert "gmail.com" in data["domains"]

    async def test_unknown_preset_404(self, auth_client):
        resp = await auth_client.get("/api/v1/providers/presets/nonexistent")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()


# ═══════════════════════════════════════════════════════════════════════════
# Save Gmail Credential (POST /gmail-credential)
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestSaveGmailCredential:
    @patch("app.api.v1.endpoints.providers.build_gmail_credential_scopes")
    @patch("app.api.v1.endpoints.providers.encrypt_credential")
    @patch("app.api.v1.endpoints.providers.GmailService")
    async def test_create_new_credential(
        self, mock_gmail_cls, mock_encrypt, mock_build_scopes, auth_client, mock_db
    ):
        mock_gmail_instance = MagicMock()
        mock_gmail_instance.verify_access = AsyncMock(return_value=True)
        mock_gmail_cls.return_value = mock_gmail_instance
        mock_encrypt.return_value = "encrypted_token"
        mock_build_scopes.return_value = {
            "granted_scopes": [],
            "import_label_templates": ["{{source_email}}", "imported"],
        }

        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(None))

        now = datetime.now(timezone.utc)

        async def _populate_on_refresh(obj):
            """Simulate what the DB does after INSERT + refresh."""
            obj.id = 1
            obj.created_at = now
            obj.updated_at = now

        mock_db.refresh = AsyncMock(side_effect=_populate_on_refresh)

        resp = await auth_client.post(
            "/api/v1/providers/gmail-credential",
            json={
                "access_token": "test_access",
                "refresh_token": "test_refresh",
                "gmail_email": "user@gmail.com",
            },
        )

        assert resp.status_code == 201
        data = resp.json()
        assert data["gmail_email"] == "user@gmail.com"
        assert data["is_valid"] is True

    @patch("app.api.v1.endpoints.providers.build_gmail_credential_scopes")
    @patch("app.api.v1.endpoints.providers.encrypt_credential")
    @patch("app.api.v1.endpoints.providers.GmailService")
    async def test_update_existing_credential(
        self, mock_gmail_cls, mock_encrypt, mock_build_scopes, auth_client, mock_db
    ):
        mock_gmail_instance = MagicMock()
        mock_gmail_instance.verify_access = AsyncMock(return_value=True)
        mock_gmail_cls.return_value = mock_gmail_instance
        mock_encrypt.return_value = "encrypted_token"
        mock_build_scopes.return_value = {
            "granted_scopes": ["scope1"],
            "import_label_templates": ["imported"],
        }

        existing = _make_gmail_credential()
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(existing))

        resp = await auth_client.post(
            "/api/v1/providers/gmail-credential",
            json={
                "access_token": "new_access",
                "refresh_token": "new_refresh",
                "gmail_email": "user@gmail.com",
            },
        )

        assert resp.status_code == 201
        data = resp.json()
        assert data["gmail_email"] == "user@gmail.com"

    @patch("app.api.v1.endpoints.providers.GmailService")
    async def test_invalid_credentials_400(self, mock_gmail_cls, auth_client, mock_db):
        mock_gmail_instance = MagicMock()
        mock_gmail_instance.verify_access = AsyncMock(return_value=False)
        mock_gmail_cls.return_value = mock_gmail_instance

        resp = await auth_client.post(
            "/api/v1/providers/gmail-credential",
            json={
                "access_token": "bad_token",
                "refresh_token": "bad_refresh",
                "gmail_email": "user@gmail.com",
            },
        )

        assert resp.status_code == 400
        assert "invalid" in resp.json()["detail"].lower()


# ═══════════════════════════════════════════════════════════════════════════
# Get Gmail Credential (GET /gmail-credential)
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestGetGmailCredential:
    async def test_found(self, auth_client, mock_db):
        cred = _make_gmail_credential()
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(cred))

        resp = await auth_client.get("/api/v1/providers/gmail-credential")
        assert resp.status_code == 200
        data = resp.json()
        assert data["gmail_email"] == "user@gmail.com"
        assert data["is_valid"] is True

    async def test_not_found_404(self, auth_client, mock_db):
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(None))

        resp = await auth_client.get("/api/v1/providers/gmail-credential")
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
# Delete Gmail Credential (DELETE /gmail-credential)
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestDeleteGmailCredential:
    async def test_delete_success(self, auth_client, mock_db):
        cred = _make_gmail_credential()
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(cred))

        resp = await auth_client.delete("/api/v1/providers/gmail-credential")
        assert resp.status_code == 204
        mock_db.delete.assert_awaited_once_with(cred)
        mock_db.commit.assert_awaited()

    async def test_delete_not_found_404(self, auth_client, mock_db):
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(None))

        resp = await auth_client.delete("/api/v1/providers/gmail-credential")
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
# Update Import Labels (PUT /gmail-credential/labels)
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestUpdateImportLabels:
    @patch("app.api.v1.endpoints.providers.extract_granted_scopes")
    @patch("app.api.v1.endpoints.providers.build_gmail_credential_scopes")
    @patch("app.api.v1.endpoints.providers.normalize_import_label_templates")
    async def test_update_labels_success(
        self,
        mock_normalize,
        mock_build_scopes,
        mock_extract_scopes,
        auth_client,
        mock_db,
    ):
        cred = _make_gmail_credential()
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(cred))
        mock_normalize.return_value = ["custom-label"]
        mock_extract_scopes.return_value = ["scope1"]
        mock_build_scopes.return_value = {
            "granted_scopes": ["scope1"],
            "import_label_templates": ["custom-label"],
        }

        resp = await auth_client.put(
            "/api/v1/providers/gmail-credential/labels",
            json={"import_label_templates": ["custom-label"]},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["gmail_email"] == "user@gmail.com"

    async def test_update_labels_not_found_404(self, auth_client, mock_db):
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(None))

        resp = await auth_client.put(
            "/api/v1/providers/gmail-credential/labels",
            json={"import_label_templates": ["test"]},
        )

        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
# Get Gmail Authorize URL (GET /gmail/authorize-url)
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestGetGmailAuthorizeUrl:
    @patch("app.api.v1.endpoints.providers.settings")
    async def test_success(self, mock_settings, auth_client):
        mock_settings.GOOGLE_CLIENT_ID = "test-client-id"

        resp = await auth_client.get(
            "/api/v1/providers/gmail/authorize-url",
            params={"redirect_uri": "http://localhost/callback"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert "authorization_url" in data
        assert "test-client-id" in data["authorization_url"]
        assert "redirect_uri=http" in data["authorization_url"]

    @patch("app.api.v1.endpoints.providers.settings")
    async def test_google_not_configured_501(self, mock_settings, auth_client):
        mock_settings.GOOGLE_CLIENT_ID = None

        resp = await auth_client.get(
            "/api/v1/providers/gmail/authorize-url",
            params={"redirect_uri": "http://localhost/callback"},
        )

        assert resp.status_code == 501
        assert "not configured" in resp.json()["detail"].lower()


# ═══════════════════════════════════════════════════════════════════════════
# Send Debug Email (POST /gmail/debug-email)
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestSendDebugEmail:
    @patch("app.api.v1.endpoints.providers.encrypt_credential")
    @patch("app.api.v1.endpoints.providers.decrypt_credential")
    @patch("app.api.v1.endpoints.providers.GmailService")
    async def test_success(
        self, mock_gmail_cls, mock_decrypt, mock_encrypt, auth_client, mock_db
    ):
        cred = _make_gmail_credential()
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(cred))
        mock_decrypt.return_value = "decrypted_token"

        mock_gmail_instance = MagicMock()
        mock_gmail_instance.verify_access = AsyncMock(return_value=True)
        mock_gmail_instance.inject_debug_email = AsyncMock(
            return_value={
                "message_id": "msg1",
                "thread_id": "t1",
                "label_ids": ["INBOX"],
            }
        )
        mock_gmail_instance.get_refreshed_token = MagicMock(return_value=None)
        mock_gmail_cls.return_value = mock_gmail_instance

        resp = await auth_client.post("/api/v1/providers/gmail/debug-email")

        assert resp.status_code == 200
        data = resp.json()
        assert data["message_id"] == "msg1"
        assert data["thread_id"] == "t1"
        assert "INBOX" in data["label_ids"]

    async def test_no_credentials_400(self, auth_client, mock_db):
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(None))

        resp = await auth_client.post("/api/v1/providers/gmail/debug-email")

        assert resp.status_code == 400
        assert "no valid gmail credentials" in resp.json()["detail"].lower()

    @patch("app.api.v1.endpoints.providers.decrypt_credential")
    @patch("app.api.v1.endpoints.providers.GmailService")
    async def test_injection_failure_502(
        self, mock_gmail_cls, mock_decrypt, auth_client, mock_db
    ):
        cred = _make_gmail_credential()
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(cred))
        mock_decrypt.return_value = "decrypted_token"

        mock_gmail_instance = MagicMock()
        mock_gmail_instance.inject_debug_email = AsyncMock(
            side_effect=GmailInjectionError("API error")
        )
        mock_gmail_instance.get_refreshed_token = MagicMock(return_value=None)
        mock_gmail_cls.return_value = mock_gmail_instance

        resp = await auth_client.post("/api/v1/providers/gmail/debug-email")

        assert resp.status_code == 502
        assert "injection failed" in resp.json()["detail"].lower()


# ═══════════════════════════════════════════════════════════════════════════
# Gmail OAuth Callback (POST /gmail/callback)
# ═══════════════════════════════════════════════════════════════════════════


def _mock_httpx_context_manager(mock_http_client):
    """Build an httpx.AsyncClient mock that works as an async context manager."""
    mock_httpx_cls = MagicMock()
    mock_httpx_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_httpx_cls.return_value.__aexit__ = AsyncMock(return_value=None)
    return mock_httpx_cls


def _make_token_response(status_code=200, json_data=None):
    """Create a mock httpx response for the token exchange."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {
        "access_token": "new_access_token",
        "refresh_token": "new_refresh_token",
        "expires_in": 3600,
        "scope": "openid email https://www.googleapis.com/auth/gmail.insert",
    }
    resp.text = "error" if status_code != 200 else "ok"
    return resp


def _make_profile_response(status_code=200, email="user@gmail.com"):
    """Create a mock httpx response for the userinfo endpoint."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = {"email": email}
    return resp


@pytest.mark.asyncio
class TestGmailCallback:
    @patch("app.api.v1.endpoints.providers.build_gmail_credential_scopes")
    @patch("app.api.v1.endpoints.providers.encrypt_credential")
    @patch("app.api.v1.endpoints.providers.GmailService")
    @patch("app.api.v1.endpoints.providers.httpx.AsyncClient")
    @patch("app.api.v1.endpoints.providers.settings")
    async def test_new_credential_success(
        self,
        mock_settings,
        mock_httpx_cls,
        mock_gmail_cls,
        mock_encrypt,
        mock_build_scopes,
        auth_client,
        mock_db,
    ):
        mock_settings.GOOGLE_CLIENT_ID = "client-id"
        mock_settings.GOOGLE_CLIENT_SECRET = "client-secret"

        mock_http_client = AsyncMock()
        token_resp = _make_token_response()
        profile_resp = _make_profile_response()
        mock_http_client.post = AsyncMock(return_value=token_resp)
        mock_http_client.get = AsyncMock(return_value=profile_resp)
        mock_httpx_cls.return_value.__aenter__ = AsyncMock(
            return_value=mock_http_client
        )
        mock_httpx_cls.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_gmail_instance = MagicMock()
        mock_gmail_instance.verify_access = AsyncMock(return_value=True)
        mock_gmail_cls.return_value = mock_gmail_instance

        mock_encrypt.return_value = "encrypted"
        mock_build_scopes.return_value = {
            "granted_scopes": ["openid", "email"],
            "import_label_templates": ["{{source_email}}", "imported"],
        }

        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(None))

        now = datetime.now(timezone.utc)

        async def _populate_on_refresh(obj):
            """Simulate what the DB does after INSERT + refresh."""
            obj.id = 1
            obj.created_at = now
            obj.updated_at = now

        mock_db.refresh = AsyncMock(side_effect=_populate_on_refresh)

        resp = await auth_client.post(
            "/api/v1/providers/gmail/callback",
            json={
                "code": "auth_code",
                "redirect_uri": "http://localhost/callback",
            },
        )

        assert resp.status_code == 201
        data = resp.json()
        assert data["gmail_email"] == "user@gmail.com"
        assert data["is_valid"] is True

    @patch("app.api.v1.endpoints.providers.build_gmail_credential_scopes")
    @patch("app.api.v1.endpoints.providers.encrypt_credential")
    @patch("app.api.v1.endpoints.providers.GmailService")
    @patch("app.api.v1.endpoints.providers.httpx.AsyncClient")
    @patch("app.api.v1.endpoints.providers.settings")
    async def test_update_existing_credential(
        self,
        mock_settings,
        mock_httpx_cls,
        mock_gmail_cls,
        mock_encrypt,
        mock_build_scopes,
        auth_client,
        mock_db,
    ):
        mock_settings.GOOGLE_CLIENT_ID = "client-id"
        mock_settings.GOOGLE_CLIENT_SECRET = "client-secret"

        mock_http_client = AsyncMock()
        token_resp = _make_token_response()
        profile_resp = _make_profile_response()
        mock_http_client.post = AsyncMock(return_value=token_resp)
        mock_http_client.get = AsyncMock(return_value=profile_resp)
        mock_httpx_cls.return_value.__aenter__ = AsyncMock(
            return_value=mock_http_client
        )
        mock_httpx_cls.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_gmail_instance = MagicMock()
        mock_gmail_instance.verify_access = AsyncMock(return_value=True)
        mock_gmail_cls.return_value = mock_gmail_instance

        mock_encrypt.return_value = "encrypted"
        mock_build_scopes.return_value = {
            "granted_scopes": ["openid"],
            "import_label_templates": ["imported"],
        }

        existing = _make_gmail_credential()
        mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(existing))

        resp = await auth_client.post(
            "/api/v1/providers/gmail/callback",
            json={
                "code": "auth_code",
                "redirect_uri": "http://localhost/callback",
            },
        )

        assert resp.status_code == 201
        data = resp.json()
        assert data["gmail_email"] == "user@gmail.com"

    @patch("app.api.v1.endpoints.providers.settings")
    async def test_google_not_configured_501(self, mock_settings, auth_client):
        mock_settings.GOOGLE_CLIENT_ID = None
        mock_settings.GOOGLE_CLIENT_SECRET = None

        resp = await auth_client.post(
            "/api/v1/providers/gmail/callback",
            json={
                "code": "auth_code",
                "redirect_uri": "http://localhost/callback",
            },
        )

        assert resp.status_code == 501
        assert "not configured" in resp.json()["detail"].lower()

    @patch("app.api.v1.endpoints.providers.httpx.AsyncClient")
    @patch("app.api.v1.endpoints.providers.settings")
    async def test_token_exchange_fails_400(
        self, mock_settings, mock_httpx_cls, auth_client
    ):
        mock_settings.GOOGLE_CLIENT_ID = "client-id"
        mock_settings.GOOGLE_CLIENT_SECRET = "client-secret"

        mock_http_client = AsyncMock()
        mock_http_client.post = AsyncMock(
            return_value=_make_token_response(status_code=400, json_data={})
        )
        mock_httpx_cls.return_value.__aenter__ = AsyncMock(
            return_value=mock_http_client
        )
        mock_httpx_cls.return_value.__aexit__ = AsyncMock(return_value=None)

        resp = await auth_client.post(
            "/api/v1/providers/gmail/callback",
            json={
                "code": "bad_code",
                "redirect_uri": "http://localhost/callback",
            },
        )

        assert resp.status_code == 400
        assert "exchange" in resp.json()["detail"].lower()

    @patch("app.api.v1.endpoints.providers.httpx.AsyncClient")
    @patch("app.api.v1.endpoints.providers.settings")
    async def test_no_access_token_returned_400(
        self, mock_settings, mock_httpx_cls, auth_client
    ):
        mock_settings.GOOGLE_CLIENT_ID = "client-id"
        mock_settings.GOOGLE_CLIENT_SECRET = "client-secret"

        mock_http_client = AsyncMock()
        # Token response OK but missing access_token
        token_resp = _make_token_response(
            json_data={"refresh_token": "rt", "expires_in": 3600}
        )
        mock_http_client.post = AsyncMock(return_value=token_resp)
        mock_httpx_cls.return_value.__aenter__ = AsyncMock(
            return_value=mock_http_client
        )
        mock_httpx_cls.return_value.__aexit__ = AsyncMock(return_value=None)

        resp = await auth_client.post(
            "/api/v1/providers/gmail/callback",
            json={
                "code": "auth_code",
                "redirect_uri": "http://localhost/callback",
            },
        )

        assert resp.status_code == 400
        assert "access token" in resp.json()["detail"].lower()

    @patch("app.api.v1.endpoints.providers.GmailService")
    @patch("app.api.v1.endpoints.providers.httpx.AsyncClient")
    @patch("app.api.v1.endpoints.providers.settings")
    async def test_verification_fails_400(
        self, mock_settings, mock_httpx_cls, mock_gmail_cls, auth_client
    ):
        mock_settings.GOOGLE_CLIENT_ID = "client-id"
        mock_settings.GOOGLE_CLIENT_SECRET = "client-secret"

        mock_http_client = AsyncMock()
        mock_http_client.post = AsyncMock(return_value=_make_token_response())
        mock_http_client.get = AsyncMock(return_value=_make_profile_response())
        mock_httpx_cls.return_value.__aenter__ = AsyncMock(
            return_value=mock_http_client
        )
        mock_httpx_cls.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_gmail_instance = MagicMock()
        mock_gmail_instance.verify_access = AsyncMock(return_value=False)
        mock_gmail_cls.return_value = mock_gmail_instance

        resp = await auth_client.post(
            "/api/v1/providers/gmail/callback",
            json={
                "code": "auth_code",
                "redirect_uri": "http://localhost/callback",
            },
        )

        assert resp.status_code == 400
        assert "verify" in resp.json()["detail"].lower()
