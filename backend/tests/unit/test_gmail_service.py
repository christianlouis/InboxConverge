"""
Unit tests for Gmail service module.
"""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from googleapiclient.errors import HttpError

from app.services.gmail_service import GmailService, GmailInjectionError, GMAIL_SCOPES
from app.utils.gmail_labels import (
    DEFAULT_IMPORT_LABEL_TEMPLATES,
    SOURCE_EMAIL_LABEL_TEMPLATE,
    build_gmail_credential_scopes,
    extract_granted_scopes,
    extract_import_label_templates,
    render_import_labels,
)


class TestGmailService:
    """Test Gmail API service"""

    def test_gmail_scopes(self):
        """Test that required Gmail scopes are defined"""
        assert "https://www.googleapis.com/auth/gmail.insert" in GMAIL_SCOPES
        assert "https://www.googleapis.com/auth/gmail.labels" in GMAIL_SCOPES

    def test_init_creates_credentials(self):
        """Test that GmailService initializes with credentials"""
        service = GmailService(
            access_token="test-access-token",
            refresh_token="test-refresh-token",
            client_id="test-client-id",
            client_secret="test-client-secret",
        )

        assert service.credentials is not None
        assert service.credentials.token == "test-access-token"
        assert service.credentials.refresh_token == "test-refresh-token"
        assert service.credentials.client_id == "test-client-id"
        assert service.credentials.client_secret == "test-client-secret"

    def test_init_without_refresh_token(self):
        """Test initialization without refresh token"""
        service = GmailService(access_token="test-access-token")

        assert service.credentials is not None
        assert service.credentials.token == "test-access-token"
        assert service.credentials.refresh_token is None

    def test_service_lazy_initialization(self):
        """Test that the API service is not created until accessed"""
        service = GmailService(access_token="test-access-token")
        assert service._service is None

    @pytest.mark.asyncio
    async def test_inject_email_success(self):
        """Test successful email injection"""
        service = GmailService(access_token="test-access-token")

        mock_api = MagicMock()
        mock_api.users().messages().insert().execute.return_value = {
            "id": "msg123",
            "threadId": "thread456",
            "labelIds": ["INBOX"],
        }
        service._service = mock_api

        result = await service.inject_email(
            raw_email=b"From: test@example.com\r\nSubject: Test\r\n\r\nHello",
            label_ids=["INBOX"],
            source_account_name="Test Account",
        )

        assert result["message_id"] == "msg123"
        assert result["thread_id"] == "thread456"
        assert "INBOX" in result["label_ids"]

    @pytest.mark.asyncio
    async def test_inject_email_default_labels(self):
        """Test that INBOX is used as default label"""
        service = GmailService(access_token="test-access-token")

        mock_api = MagicMock()
        mock_api.users().messages().insert().execute.return_value = {
            "id": "msg123",
            "threadId": "thread456",
            "labelIds": ["INBOX"],
        }
        service._service = mock_api

        # No label_ids specified - should default to INBOX
        result = await service.inject_email(
            raw_email=b"From: test@example.com\r\nSubject: Test\r\n\r\nHello",
        )

        assert result["message_id"] == "msg123"

    @pytest.mark.asyncio
    async def test_inject_email_api_error(self):
        """Test that GmailInjectionError is raised on API error"""
        service = GmailService(access_token="test-access-token")

        mock_api = MagicMock()
        mock_api.users().messages().insert().execute.side_effect = Exception(
            "API Error"
        )
        service._service = mock_api

        with pytest.raises(GmailInjectionError, match="Failed to inject email"):
            await service.inject_email(
                raw_email=b"From: test@example.com\r\nSubject: Test\r\n\r\nHello",
            )

    @pytest.mark.asyncio
    async def test_verify_access_success(self):
        """Test successful access verification"""
        service = GmailService(access_token="test-access-token")

        mock_api = MagicMock()
        mock_api.users().getProfile().execute.return_value = {
            "emailAddress": "test@gmail.com",
        }
        service._service = mock_api

        result = await service.verify_access()
        assert result is True

    @pytest.mark.asyncio
    async def test_verify_access_failure(self):
        """Test failed access verification"""
        service = GmailService(access_token="bad-token")

        mock_api = MagicMock()
        mock_api.users().getProfile().execute.side_effect = Exception("Invalid token")
        service._service = mock_api

        result = await service.verify_access()
        assert result is False

    @pytest.mark.asyncio
    async def test_get_email_address_success(self):
        """Test getting email address"""
        service = GmailService(access_token="test-access-token")

        mock_api = MagicMock()
        mock_api.users().getProfile().execute.return_value = {
            "emailAddress": "user@gmail.com",
        }
        service._service = mock_api

        email = await service.get_email_address()
        assert email == "user@gmail.com"

    @pytest.mark.asyncio
    async def test_get_email_address_failure(self):
        """Test getting email address when API fails"""
        service = GmailService(access_token="bad-token")

        mock_api = MagicMock()
        mock_api.users().getProfile().execute.side_effect = Exception("Error")
        service._service = mock_api

        email = await service.get_email_address()
        assert email is None

    def test_gmail_label_metadata_helpers(self):
        """Test Gmail metadata extraction remains backward compatible."""
        scopes = build_gmail_credential_scopes(
            ["scope-a", "scope-b"],
            [SOURCE_EMAIL_LABEL_TEMPLATE, "Imported", " imported "],
        )

        assert extract_granted_scopes(scopes) == ["scope-a", "scope-b"]
        assert extract_import_label_templates(scopes) == [
            SOURCE_EMAIL_LABEL_TEMPLATE,
            "Imported",
        ]
        assert (
            extract_import_label_templates(["legacy-scope"])
            == DEFAULT_IMPORT_LABEL_TEMPLATES
        )

    def test_render_import_labels_uses_source_email_template(self):
        """Test that source email templates render to the source mailbox address."""
        rendered = render_import_labels(
            [SOURCE_EMAIL_LABEL_TEMPLATE, "Imported", ""],
            "source@example.com",
        )

        assert rendered == ["source@example.com", "Imported"]

    @pytest.mark.asyncio
    async def test_build_import_label_ids_creates_configured_labels(self):
        """Test that configured import labels are created and added alongside INBOX."""
        service = GmailService(access_token="test-access-token")
        service.get_or_create_label = AsyncMock(
            side_effect=["Label-source", "Label-imported"]
        )  # type: ignore[method-assign]

        label_ids = await service.build_import_label_ids(
            import_label_templates=[SOURCE_EMAIL_LABEL_TEMPLATE, "imported"],
            source_email="source@example.com",
        )

        assert label_ids == ["INBOX", "Label-source", "Label-imported"]

    # ------------------------------------------------------------------
    # Helper for HttpError construction
    # ------------------------------------------------------------------
    @staticmethod
    def _make_http_error(
        status_code: int = 401, reason: str = "Unauthorized"
    ) -> HttpError:
        resp = MagicMock()
        resp.status = status_code
        resp.reason = reason
        content = json.dumps({"error": {"message": reason}}).encode()
        return HttpError(resp, content, uri="https://gmail.googleapis.com/test")

    # ------------------------------------------------------------------
    # inject_email – HttpError branch
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_inject_email_http_error(self):
        """HttpError in inject_email is caught and re-raised as GmailInjectionError."""
        service = GmailService(access_token="test-access-token")

        mock_api = MagicMock()
        mock_api.users().messages().insert().execute.side_effect = (
            self._make_http_error(403, "Forbidden")
        )
        service._service = mock_api

        with pytest.raises(GmailInjectionError, match="Gmail API error"):
            await service.inject_email(
                raw_email=b"From: a@b.com\r\nSubject: X\r\n\r\nBody",
            )

    # ------------------------------------------------------------------
    # get_or_create_label – existing label found
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_get_or_create_label_existing(self):
        """Returns ID of an existing label matched case-insensitively."""
        service = GmailService(access_token="test-access-token")

        mock_api = MagicMock()
        mock_api.users().labels().list().execute.return_value = {
            "labels": [
                {"id": "Label_1", "name": "imported"},
                {"id": "INBOX", "name": "INBOX"},
            ]
        }
        service._service = mock_api

        label_id = await service.get_or_create_label("Imported")
        assert label_id == "Label_1"

    # ------------------------------------------------------------------
    # get_or_create_label – label not found, creates new one
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_get_or_create_label_creates_new(self):
        """Creates a new label when no existing label matches."""
        service = GmailService(access_token="test-access-token")

        mock_api = MagicMock()
        mock_api.users().labels().list().execute.return_value = {
            "labels": [{"id": "INBOX", "name": "INBOX"}]
        }
        mock_api.users().labels().create().execute.return_value = {
            "id": "Label_new",
            "name": "new-label",
        }
        service._service = mock_api

        label_id = await service.get_or_create_label("new-label")
        assert label_id == "Label_new"

    # ------------------------------------------------------------------
    # get_or_create_label – HttpError handling
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_get_or_create_label_http_error(self):
        """HttpError during label list raises GmailInjectionError."""
        service = GmailService(access_token="test-access-token")

        mock_api = MagicMock()
        mock_api.users().labels().list().execute.side_effect = self._make_http_error(
            500, "Internal Server Error"
        )
        service._service = mock_api

        with pytest.raises(GmailInjectionError, match="Gmail API error"):
            await service.get_or_create_label("test")

    # ------------------------------------------------------------------
    # get_or_create_label – generic Exception handling
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_get_or_create_label_generic_exception(self):
        """Generic exception during label management raises GmailInjectionError."""
        service = GmailService(access_token="test-access-token")

        mock_api = MagicMock()
        mock_api.users().labels().list().execute.side_effect = RuntimeError("boom")
        service._service = mock_api

        with pytest.raises(GmailInjectionError, match="Failed to get/create"):
            await service.get_or_create_label("oops")

    # ------------------------------------------------------------------
    # inject_debug_email – full flow
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_inject_debug_email(self):
        """inject_debug_email creates labels and injects a test email."""
        service = GmailService(access_token="test-access-token")

        service.build_import_label_ids = AsyncMock(  # type: ignore[method-assign]
            return_value=["INBOX", "Label_imported"]
        )
        service.get_or_create_label = AsyncMock(  # type: ignore[method-assign]
            return_value="Label_test"
        )
        service.inject_email = AsyncMock(  # type: ignore[method-assign]
            return_value={
                "message_id": "msg1",
                "thread_id": "t1",
                "label_ids": ["INBOX", "Label_imported", "Label_test"],
            }
        )

        result = await service.inject_debug_email("user@gmail.com")

        assert result["message_id"] == "msg1"
        assert "Label_test" in result["label_ids"]
        service.build_import_label_ids.assert_awaited_once()
        service.get_or_create_label.assert_awaited_once_with("test")
        service.inject_email.assert_awaited_once()
        # The test label should have been appended to label_ids
        call_kwargs = service.inject_email.call_args
        assert "Label_test" in call_kwargs.kwargs["label_ids"]

    # ------------------------------------------------------------------
    # inject_debug_email – test label already present in import labels
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_inject_debug_email_test_label_already_present(self):
        """inject_debug_email does not duplicate the test label."""
        service = GmailService(access_token="test-access-token")

        service.build_import_label_ids = AsyncMock(  # type: ignore[method-assign]
            return_value=["INBOX", "Label_test"]
        )
        service.get_or_create_label = AsyncMock(  # type: ignore[method-assign]
            return_value="Label_test"
        )
        service.inject_email = AsyncMock(  # type: ignore[method-assign]
            return_value={
                "message_id": "msg2",
                "thread_id": "t2",
                "label_ids": ["INBOX", "Label_test"],
            }
        )

        result = await service.inject_debug_email("user@gmail.com")

        assert result["message_id"] == "msg2"
        call_kwargs = service.inject_email.call_args
        # Label_test should appear only once
        assert call_kwargs.kwargs["label_ids"].count("Label_test") == 1

    # ------------------------------------------------------------------
    # get_refreshed_token – token was NOT refreshed
    # ------------------------------------------------------------------
    def test_get_refreshed_token_no_change(self):
        """Returns None when the token has not changed."""
        service = GmailService(access_token="original-token")
        assert service.get_refreshed_token() is None

    # ------------------------------------------------------------------
    # get_refreshed_token – token was refreshed
    # ------------------------------------------------------------------
    def test_get_refreshed_token_changed(self):
        """Returns new token info when the token was refreshed."""
        service = GmailService(access_token="original-token")

        # Simulate an automatic token refresh by mutating credentials
        new_expiry = datetime(2099, 1, 1, tzinfo=timezone.utc)
        service.credentials.token = "new-refreshed-token"
        service.credentials.expiry = new_expiry

        result = service.get_refreshed_token()
        assert result is not None
        assert result["access_token"] == "new-refreshed-token"
        assert result["expiry"] == new_expiry

    # ------------------------------------------------------------------
    # service property – lazy init builds the service
    # ------------------------------------------------------------------
    def test_service_property_builds_service(self):
        """Accessing .service triggers googleapiclient.discovery.build."""
        with patch("app.services.gmail_service.build") as mock_build:
            mock_build.return_value = MagicMock()
            service = GmailService(access_token="test-access-token")
            assert service._service is None

            api = service.service  # trigger lazy init

            mock_build.assert_called_once_with(
                "gmail", "v1", credentials=service.credentials, cache_discovery=False
            )
            assert api is mock_build.return_value
            # Second access should NOT call build again
            _ = service.service
            mock_build.assert_called_once()

    # ------------------------------------------------------------------
    # _tz_aware_expiry – timezone normalisation helper
    # ------------------------------------------------------------------
    def test_tz_aware_expiry_naive_becomes_utc(self):
        """A naive datetime is made tz-aware (UTC)."""
        naive = datetime(2026, 6, 1, 12, 0, 0)  # no tzinfo
        result = GmailService._tz_aware_expiry(naive)
        assert result is not None
        assert result.tzinfo is not None
        assert result.utcoffset().total_seconds() == 0
        assert result.replace(tzinfo=None) == naive

    def test_tz_aware_expiry_aware_unchanged(self):
        """An already tz-aware datetime is returned as-is."""
        aware = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        result = GmailService._tz_aware_expiry(aware)
        assert result is aware

    def test_tz_aware_expiry_none_unchanged(self):
        """None is returned unchanged."""
        assert GmailService._tz_aware_expiry(None) is None

    # ------------------------------------------------------------------
    # get_refreshed_token – naive expiry is normalised to UTC
    # ------------------------------------------------------------------
    def test_get_refreshed_token_naive_expiry_becomes_utc(self):
        """get_refreshed_token converts a naive expiry from google-auth to UTC-aware."""
        service = GmailService(access_token="original-token")

        # google-auth sets credentials.expiry as naive UTC
        naive_expiry = datetime(2099, 1, 1, 0, 0, 0)  # no tzinfo
        service.credentials.token = "new-refreshed-token"
        service.credentials.expiry = naive_expiry

        result = service.get_refreshed_token()
        assert result is not None
        expiry = result["expiry"]
        assert expiry is not None
        assert expiry.tzinfo is not None, "expiry must be tz-aware for DB storage"
        assert expiry.utcoffset().total_seconds() == 0
        assert expiry.replace(tzinfo=None) == naive_expiry

    # ------------------------------------------------------------------
    # proactive_refresh – naive expiry is normalised to UTC
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_proactive_refresh_naive_expiry_becomes_utc(self):
        """proactive_refresh converts a naive expiry from google-auth to UTC-aware."""
        service = GmailService(
            access_token="old-token",
            refresh_token="refresh-token",
        )

        naive_expiry = datetime(2099, 6, 1, 0, 0, 0)  # no tzinfo

        def _fake_refresh(_request):
            service.credentials.token = "new-token"
            service.credentials.expiry = naive_expiry

        with patch.object(service.credentials, "refresh", side_effect=_fake_refresh):
            result = await service.proactive_refresh()

        assert result["access_token"] == "new-token"
        expiry = result["expiry"]
        assert expiry is not None
        assert expiry.tzinfo is not None, "expiry must be tz-aware for DB storage"
        assert expiry.utcoffset().total_seconds() == 0
        assert expiry.replace(tzinfo=None) == naive_expiry
