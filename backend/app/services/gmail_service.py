"""
Gmail API service for injecting emails directly into Gmail.

Uses the Gmail API's users.messages.insert() method to inject emails
into a user's Gmail account, preserving original headers and metadata.
This is preferred over SMTP forwarding as it doesn't modify the email.
"""

import asyncio
import base64
import logging
import textwrap
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.utils import format_datetime
from typing import Optional, Dict, Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

# Gmail API scopes needed for email injection
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.insert",
    "https://www.googleapis.com/auth/gmail.labels",
    "https://www.googleapis.com/auth/gmail.readonly",
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
        self._initial_access_token = access_token
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
            error_msg = (
                f"Gmail API error: {e.reason if hasattr(e, 'reason') else str(e)}"
            )
            logger.error(error_msg)
            # Surface 401 so callers can mark credentials as invalid
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
        loop = asyncio.get_event_loop()

        try:
            result = await loop.run_in_executor(
                None,
                lambda: self.service.users().getProfile(userId="me").execute(),
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
        loop = asyncio.get_event_loop()

        try:
            result = await loop.run_in_executor(
                None,
                lambda: self.service.users().getProfile(userId="me").execute(),
            )
            return result.get("emailAddress")
        except Exception as e:
            logger.error(f"Failed to get Gmail email address: {e}")
            return None

    async def get_or_create_label(self, name: str) -> str:
        """
        Return the Gmail label ID for a label with the given name.

        Lists the user's existing labels and returns the ID of the first
        match (case-insensitive).  If no matching label is found, a new
        label is created and its ID is returned.

        Args:
            name: Human-readable label name (e.g. "test", "imported").

        Returns:
            Gmail label ID string (e.g. "Label_1234567890").

        Raises:
            GmailInjectionError: If the Gmail API call fails.
        """
        loop = asyncio.get_event_loop()

        try:
            labels_resp = await loop.run_in_executor(
                None,
                lambda: self.service.users().labels().list(userId="me").execute(),
            )
            for label in labels_resp.get("labels", []):
                if label.get("name", "").lower() == name.lower():
                    return label["id"]

            # Label not found – create it
            created = await loop.run_in_executor(
                None,
                lambda: self.service.users()
                .labels()
                .create(userId="me", body={"name": name})
                .execute(),
            )
            logger.info(f"Created Gmail label '{name}' with id={created['id']}")
            return created["id"]

        except HttpError as e:
            error_msg = f"Gmail API error while managing label '{name}': {e.reason if hasattr(e, 'reason') else str(e)}"
            logger.error(error_msg)
            raise GmailInjectionError(error_msg)
        except Exception as e:
            error_msg = f"Failed to get/create Gmail label '{name}': {str(e)}"
            logger.error(error_msg)
            raise GmailInjectionError(error_msg)

    async def inject_debug_email(
        self,
        recipient_email: str,
    ) -> Dict[str, Any]:
        """
        Inject a debug/test email into the user's Gmail inbox.

        The message is made to appear as if it was sent by
        christian@docuelevate.org on the current date.  It is placed in
        the inbox and tagged with the custom labels "test" and "imported"
        so it is easy to identify and clean up.

        Args:
            recipient_email: The Gmail address to deliver the message to
                (the authenticated user's address).

        Returns:
            Dict with message_id, thread_id, and label_ids.

        Raises:
            GmailInjectionError: If injection or label management fails.
        """
        now = datetime.now(timezone.utc)
        date_str = now.strftime("%d %B %Y")  # e.g. "25 March 2026"

        subject = f"Test Import – {date_str}"

        body = textwrap.dedent(f"""\
            Hi there,

            This is an automated test message injected via the Gmail API to
            confirm that the import pipeline is working correctly.

            Date:   {date_str}
            Source: DocuElevate Integration Test

            If you can see this message in your inbox it means that Gmail API
            delivery is functioning as expected.  Feel free to delete it.

            Best regards,
            Christian Krakau-Louis
            DocuElevate
            """)

        msg = MIMEText(body, "plain", "utf-8")
        msg["From"] = "Christian Krakau-Louis <christian@docuelevate.org>"
        msg["To"] = recipient_email
        msg["Subject"] = subject
        msg["Date"] = format_datetime(now)
        msg["Message-ID"] = f"<debug-{now.strftime('%Y%m%d%H%M%S')}@docuelevate.org>"

        raw_bytes = msg.as_bytes()

        # Resolve label IDs (create labels if they don't exist yet)
        test_label_id = await self.get_or_create_label("test")
        imported_label_id = await self.get_or_create_label("imported")

        label_ids = ["INBOX", test_label_id, imported_label_id]

        return await self.inject_email(
            raw_email=raw_bytes,
            label_ids=label_ids,
            source_account_name="debug",
        )

    def get_refreshed_token(self) -> Optional[Dict[str, Any]]:
        """
        Return the current access token and expiry if the token was refreshed
        since this service instance was created.

        The google-auth library auto-refreshes the access token when an API
        call is made with an expired token.  Call this after inject_email() to
        check whether a refresh happened and persist the new token.

        Returns:
            Dict with ``access_token`` and ``expiry`` (datetime | None), or
            None if the token has not changed from the one passed to __init__.
        """
        current_token = self.credentials.token
        if current_token and current_token != self._initial_access_token:
            return {
                "access_token": current_token,
                "expiry": self.credentials.expiry,
            }
        return None
