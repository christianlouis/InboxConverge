"""
Gmail API service for injecting emails directly into Gmail.

Uses the Gmail API's users.messages.insert() method to inject emails
into a user's Gmail account, preserving original headers and metadata.
This is preferred over SMTP forwarding as it doesn't modify the email.
"""
import base64
import logging
from typing import Optional, Dict, Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

# Gmail API scopes needed for email injection
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.insert",
    "https://www.googleapis.com/auth/gmail.labels",
]


class GmailInjectionError(Exception):
    """Raised when Gmail API injection fails"""
    pass


class GmailService:
    """
    Service for injecting emails into Gmail via the Gmail API.

    Uses users.messages.insert() which places emails directly into
    the user's mailbox without sending them through SMTP.
    """

    def __init__(
        self,
        access_token: str,
        refresh_token: Optional[str] = None,
        token_uri: str = "https://oauth2.googleapis.com/token",
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
    ):
        """
        Initialize Gmail service with OAuth2 credentials.

        Args:
            access_token: Valid OAuth2 access token
            refresh_token: OAuth2 refresh token for automatic renewal
            token_uri: OAuth2 token endpoint
            client_id: Google OAuth2 client ID
            client_secret: Google OAuth2 client secret
        """
        self.credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri=token_uri,
            client_id=client_id,
            client_secret=client_secret,
            scopes=GMAIL_SCOPES,
        )
        self._service = None

    @property
    def service(self):
        """Lazy-initialize the Gmail API service."""
        if self._service is None:
            self._service = build("gmail", "v1", credentials=self.credentials)
        return self._service

    async def inject_email(
        self,
        raw_email: bytes,
        label_ids: Optional[list] = None,
        source_account_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Inject a raw email into the user's Gmail account.

        Uses users.messages.insert() to place the email directly
        into the mailbox. The email appears as if it was received
        normally, preserving all original headers.

        Args:
            raw_email: Raw email bytes (RFC 2822 format)
            label_ids: Gmail label IDs to apply (defaults to ["INBOX"])
            source_account_name: Optional name for logging

        Returns:
            Dict with message id and thread id

        Raises:
            GmailInjectionError: If injection fails
        """
        import asyncio

        if label_ids is None:
            label_ids = ["INBOX"]

        # Base64url encode the raw email
        encoded_message = base64.urlsafe_b64encode(raw_email).decode("utf-8")

        message_body = {
            "raw": encoded_message,
            "labelIds": label_ids,
        }

        loop = asyncio.get_event_loop()

        try:
            result = await loop.run_in_executor(
                None,
                lambda: self.service.users()
                .messages()
                .insert(userId="me", body=message_body)
                .execute(),
            )

            logger.info(
                f"Injected email into Gmail: id={result.get('id')}"
                f"{f' from {source_account_name}' if source_account_name else ''}"
            )

            return {
                "message_id": result.get("id"),
                "thread_id": result.get("threadId"),
                "label_ids": result.get("labelIds", []),
            }

        except HttpError as e:
            error_msg = f"Gmail API error: {e.reason if hasattr(e, 'reason') else str(e)}"
            logger.error(error_msg)
            raise GmailInjectionError(error_msg)
        except Exception as e:
            error_msg = f"Failed to inject email into Gmail: {str(e)}"
            logger.error(error_msg)
            raise GmailInjectionError(error_msg)

    async def verify_access(self) -> bool:
        """
        Verify that the Gmail API credentials are valid.

        Returns:
            True if credentials are valid and can access Gmail
        """
        import asyncio

        loop = asyncio.get_event_loop()

        try:
            result = await loop.run_in_executor(
                None,
                lambda: self.service.users()
                .getProfile(userId="me")
                .execute(),
            )
            email = result.get("emailAddress", "unknown")
            logger.info(f"Gmail API access verified for: {email}")
            return True
        except Exception as e:
            logger.error(f"Gmail API access verification failed: {e}")
            return False

    async def get_email_address(self) -> Optional[str]:
        """
        Get the email address associated with the Gmail credentials.

        Returns:
            Email address string or None if unavailable
        """
        import asyncio

        loop = asyncio.get_event_loop()

        try:
            result = await loop.run_in_executor(
                None,
                lambda: self.service.users()
                .getProfile(userId="me")
                .execute(),
            )
            return result.get("emailAddress")
        except Exception as e:
            logger.error(f"Failed to get Gmail email address: {e}")
            return None
