"""
Unit tests for the OAuth / auth service (services/auth_service.py).

External HTTP calls are mocked via httpx.  No real network or DB needed.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

from app.services.auth_service import OAuthService
from app.models.database_models import User

# ── helpers ──────────────────────────────────────────────────────────────────


def _make_user(id: int = 1, email: str = "user@example.com") -> MagicMock:
    u = MagicMock(spec=User)
    u.id = id
    u.email = email
    return u


def _mock_token_response(
    access_token: str = "access123", refresh_token: str = "refresh456"
):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": 3600,
        "scope": "openid email profile",
    }
    return resp


def _mock_user_info_response(
    email: str = "user@google.com",
    name: str = "Test User",
    google_id: str = "g123",
    verified: bool = True,
):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "email": email,
        "name": name,
        "id": google_id,
        "picture": "https://example.com/pic.jpg",
        "verified_email": verified,
    }
    return resp


# ── OAuthService.get_google_user_info ────────────────────────────────────────


class TestGetGoogleUserInfo:
    async def test_success(self):
        svc = OAuthService()
        token_resp = _mock_token_response()
        user_info_resp = _mock_user_info_response()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=token_resp)
        mock_client.get = AsyncMock(return_value=user_info_resp)

        with patch(
            "app.services.auth_service.httpx.AsyncClient", return_value=mock_client
        ):
            result = await svc.get_google_user_info(
                code="authcode", redirect_uri="http://localhost/callback"
            )

        assert result["email"] == "user@google.com"
        assert result["google_id"] == "g123"
        assert result["verified_email"] is True
        assert result["access_token"] == "access123"

    async def test_token_exchange_fails(self):
        svc = OAuthService()
        bad_resp = MagicMock()
        bad_resp.status_code = 400
        bad_resp.text = "bad_request"

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=bad_resp)

        with patch(
            "app.services.auth_service.httpx.AsyncClient", return_value=mock_client
        ):
            with pytest.raises(HTTPException) as exc_info:
                await svc.get_google_user_info(
                    code="bad", redirect_uri="http://localhost"
                )
        assert exc_info.value.status_code == 400

    async def test_no_access_token_in_response(self):
        svc = OAuthService()
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {}  # no access_token

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=resp)

        with patch(
            "app.services.auth_service.httpx.AsyncClient", return_value=mock_client
        ):
            with pytest.raises(HTTPException) as exc_info:
                await svc.get_google_user_info(
                    code="c", redirect_uri="http://localhost"
                )
        assert exc_info.value.status_code == 400

    async def test_user_info_fetch_fails(self):
        svc = OAuthService()
        token_resp = _mock_token_response()
        bad_info = MagicMock()
        bad_info.status_code = 500
        bad_info.text = "server error"

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=token_resp)
        mock_client.get = AsyncMock(return_value=bad_info)

        with patch(
            "app.services.auth_service.httpx.AsyncClient", return_value=mock_client
        ):
            with pytest.raises(HTTPException) as exc_info:
                await svc.get_google_user_info(
                    code="c", redirect_uri="http://localhost"
                )
        assert exc_info.value.status_code == 400

    async def test_unexpected_exception_becomes_500(self):
        svc = OAuthService()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=RuntimeError("network down"))

        with patch(
            "app.services.auth_service.httpx.AsyncClient", return_value=mock_client
        ):
            with pytest.raises(HTTPException) as exc_info:
                await svc.get_google_user_info(
                    code="c", redirect_uri="http://localhost"
                )
        assert exc_info.value.status_code == 500


# ── OAuthService.create_tokens_for_user ──────────────────────────────────────


class TestCreateTokensForUser:
    def test_returns_all_fields(self):
        user = _make_user(id=7)
        result = OAuthService.create_tokens_for_user(user)
        assert "access_token" in result
        assert "refresh_token" in result
        assert result["token_type"] == "bearer"

    def test_access_token_is_string(self):
        user = _make_user(id=3)
        result = OAuthService.create_tokens_for_user(user)
        assert isinstance(result["access_token"], str)
        assert len(result["access_token"]) > 0

    def test_refresh_token_is_string(self):
        user = _make_user(id=5)
        result = OAuthService.create_tokens_for_user(user)
        assert isinstance(result["refresh_token"], str)
        assert len(result["refresh_token"]) > 0

    def test_different_users_get_different_tokens(self):
        u1 = _make_user(id=1)
        u2 = _make_user(id=2)
        tokens1 = OAuthService.create_tokens_for_user(u1)
        tokens2 = OAuthService.create_tokens_for_user(u2)
        assert tokens1["access_token"] != tokens2["access_token"]
