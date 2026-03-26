"""
Unit tests for Gmail service module.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
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
