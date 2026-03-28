"""
Mail processing service for fetching and forwarding emails.
Supports both POP3 and IMAP protocols with secure connections.
"""

import asyncio
import poplib
import smtplib
import ssl
from email import parser
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate, make_msgid
from typing import List, Dict, Any, Optional, Set, Tuple
import logging
from aioimaplib import aioimaplib

from app.models.database_models import MailAccount, MailProtocol

logger = logging.getLogger(__name__)


class MailConnectionError(Exception):
    """Raised when unable to connect to mail server"""

    pass


class MailAuthenticationError(Exception):
    """Raised when authentication fails"""

    pass


class MailFetchError(Exception):
    """Raised when fetching emails fails"""

    pass


class MailForwardError(Exception):
    """Raised when forwarding email fails"""

    pass


class MailProcessor:
    """Handles mail fetching and forwarding operations"""

    def __init__(self, account: MailAccount, decrypted_password: str):
        self.account = account
        self.password = decrypted_password

    async def test_connection(self) -> Tuple[bool, str]:
        """
        Test connection to mail server.
        Returns (success, message)
        """
        try:
            if self.account.protocol in [MailProtocol.POP3, MailProtocol.POP3_SSL]:
                return await self._test_pop3_connection()
            else:
                return await self._test_imap_connection()
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False, str(e)

    async def _test_pop3_connection(self) -> Tuple[bool, str]:
        """Test POP3 connection"""
        try:
            loop = asyncio.get_event_loop()

            # Run blocking POP3 operations in thread pool
            def connect_pop3():
                if self.account.protocol == MailProtocol.POP3_SSL:
                    context = ssl.create_default_context()
                    pop_conn = poplib.POP3_SSL(
                        self.account.host,
                        self.account.port,
                        context=context,
                        timeout=10,
                    )
                else:
                    pop_conn = poplib.POP3(
                        self.account.host, self.account.port, timeout=10
                    )

                # Try authentication
                pop_conn.user(self.account.username)
                pop_conn.pass_(self.password)

                # Get mailbox stats
                message_count, mailbox_size = pop_conn.stat()

                pop_conn.quit()
                return message_count, mailbox_size

            message_count, mailbox_size = await loop.run_in_executor(None, connect_pop3)

            return True, f"Connection successful. {message_count} messages in mailbox."

        except poplib.error_proto as e:
            error_msg = str(e)
            if "authentication" in error_msg.lower() or "auth" in error_msg.lower():
                return False, f"Authentication failed: {error_msg}"
            return False, f"POP3 protocol error: {error_msg}"
        except Exception as e:
            return False, f"Connection failed: {str(e)}"

    async def _test_imap_connection(self) -> Tuple[bool, str]:
        """Test IMAP connection"""
        try:
            # Create IMAP client
            if self.account.protocol == MailProtocol.IMAP_SSL:
                imap_client = aioimaplib.IMAP4_SSL(
                    host=self.account.host, port=self.account.port, timeout=10
                )
            else:
                imap_client = aioimaplib.IMAP4(
                    host=self.account.host, port=self.account.port, timeout=10
                )

            await imap_client.wait_hello_from_server()

            # Authenticate
            response = await imap_client.login(self.account.username, self.password)

            if response.result != "OK":
                return False, f"Authentication failed: {response.lines}"

            # Select inbox
            await imap_client.select("INBOX")

            # Get message count
            response = await imap_client.search("ALL")
            message_ids = response.lines[0].split()
            message_count = len(message_ids)

            await imap_client.logout()

            return True, f"Connection successful. {message_count} messages in mailbox."

        except Exception as e:
            return False, f"IMAP connection failed: {str(e)}"

    async def fetch_emails(
        self,
        max_count: Optional[int] = None,
        already_seen_uids: Optional[Set[str]] = None,
    ) -> Tuple[List[bytes], List[str]]:
        """
        Fetch emails from the mail server.

        Args:
            max_count: Maximum number of messages to fetch.
            already_seen_uids: Set of message UIDs that have already been
                processed and should be skipped.

        Returns:
            A tuple of (raw_email_bytes_list, new_uid_strings_list).
            The caller should persist the new UIDs to prevent re-processing.
        """
        effective_max: int = max_count if max_count is not None else self.account.max_emails_per_check  # type: ignore[assignment]
        seen: Set[str] = already_seen_uids or set()

        if self.account.protocol in [MailProtocol.POP3, MailProtocol.POP3_SSL]:
            return await self._fetch_pop3_emails(effective_max, seen)
        else:
            return await self._fetch_imap_emails(effective_max, seen)

    async def _fetch_pop3_emails(
        self, max_count: int, already_seen_uids: Set[str]
    ) -> Tuple[List[bytes], List[str]]:
        """Fetch emails via POP3, skipping already-downloaded UIDs."""
        emails: List[bytes] = []
        new_uids: List[str] = []

        try:
            loop = asyncio.get_event_loop()

            def fetch_pop3() -> Tuple[List[bytes], List[str]]:
                # Connect
                if self.account.protocol == MailProtocol.POP3_SSL:
                    context = ssl.create_default_context()
                    pop_conn = poplib.POP3_SSL(
                        str(self.account.host),
                        int(self.account.port),
                        context=context,
                        timeout=30,
                    )
                else:
                    pop_conn = poplib.POP3(  # type: ignore[assignment]
                        str(self.account.host), int(self.account.port), timeout=30
                    )

                # Authenticate
                pop_conn.user(str(self.account.username))
                pop_conn.pass_(self.password)

                # Retrieve UIDL map: {msg_number: uid_string}
                uidl_response = pop_conn.uidl()
                uid_map: Dict[int, str] = {}
                for entry in uidl_response[1]:
                    parts = entry.decode().split(" ", 1)
                    if len(parts) == 2:
                        uid_map[int(parts[0])] = parts[1].strip()

                num_messages = len(uid_map)
                logger.info(
                    f"Found {num_messages} messages for account {self.account.id}"
                )

                fetched: List[bytes] = []
                fetched_uids: List[str] = []
                messages_to_delete: List[int] = []
                fetched_count = 0

                for msg_num, uid in uid_map.items():
                    if fetched_count >= max_count:
                        break

                    # Skip messages we already processed
                    if uid in already_seen_uids:
                        logger.debug(
                            f"Skipping already-downloaded message {uid} "
                            f"for account {self.account.id}"
                        )
                        continue

                    try:
                        response, lines, octets = pop_conn.retr(msg_num)
                        email_data = b"\r\n".join(lines)
                        fetched.append(email_data)
                        fetched_uids.append(uid)
                        messages_to_delete.append(msg_num)
                        fetched_count += 1
                        logger.info(
                            f"Retrieved message {msg_num} (uid={uid}) "
                            f"from account {self.account.id}"
                        )
                    except Exception as e:
                        logger.error(f"Error retrieving message {msg_num}: {e}")

                # Delete messages if configured
                if self.account.delete_after_forward:
                    for msg_id in messages_to_delete:
                        try:
                            pop_conn.dele(msg_id)
                        except Exception as e:
                            logger.error(f"Error deleting message {msg_id}: {e}")

                pop_conn.quit()
                return fetched, fetched_uids

            emails, new_uids = await loop.run_in_executor(None, fetch_pop3)

        except Exception as e:
            logger.error(f"Error fetching POP3 emails: {e}")
            raise MailFetchError(f"POP3 fetch error: {str(e)}")

        return emails, new_uids

    async def _fetch_imap_emails(
        self, max_count: int, already_seen_uids: Set[str]
    ) -> Tuple[List[bytes], List[str]]:
        """Fetch emails via IMAP, marking each message \\Seen to prevent re-fetch."""
        emails: List[bytes] = []
        new_uids: List[str] = []

        try:
            # Create IMAP client
            if self.account.protocol == MailProtocol.IMAP_SSL:
                imap_client = aioimaplib.IMAP4_SSL(
                    host=self.account.host, port=self.account.port, timeout=30
                )
            else:
                imap_client = aioimaplib.IMAP4(
                    host=self.account.host, port=self.account.port, timeout=30
                )

            await imap_client.wait_hello_from_server()
            await imap_client.login(self.account.username, self.password)
            await imap_client.select("INBOX")

            # Search for unseen messages only
            response = await imap_client.search("UNSEEN")
            message_ids = response.lines[0].split()

            # Limit to max_count
            message_ids = message_ids[:max_count]

            logger.info(
                f"Found {len(message_ids)} unread messages for account {self.account.id}"
            )

            # Fetch each message
            for msg_id in message_ids:
                uid_str = msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id)

                # Skip messages already tracked in our DB
                if uid_str in already_seen_uids:
                    logger.debug(
                        f"Skipping already-processed IMAP message {uid_str} "
                        f"for account {self.account.id}"
                    )
                    # Still mark as Seen so it doesn't show up in UNSEEN searches
                    await imap_client.store(msg_id, "+FLAGS", "\\Seen")
                    continue

                try:
                    response = await imap_client.fetch(msg_id, "(RFC822)")

                    # Extract email data from response
                    email_data = None
                    for line in response.lines:
                        if isinstance(line, bytes) and b"RFC822" in line:
                            # Find the email content
                            start_idx = line.find(b"{")
                            if start_idx != -1:
                                # Email data is in the next parts
                                continue
                        elif isinstance(line, bytes) and not line.startswith(b"*"):
                            email_data = line
                            break

                    if email_data:
                        emails.append(email_data)
                        new_uids.append(uid_str)

                        # Always mark as Seen after fetching so the message is
                        # not picked up again on the next UNSEEN search.
                        await imap_client.store(msg_id, "+FLAGS", "\\Seen")

                        if self.account.delete_after_forward:
                            await imap_client.store(msg_id, "+FLAGS", "\\Deleted")

                except Exception as e:
                    logger.error(f"Error fetching message {msg_id}: {e}")

            # Expunge deleted messages
            if self.account.delete_after_forward:
                await imap_client.expunge()

            await imap_client.logout()

        except Exception as e:
            logger.error(f"Error fetching IMAP emails: {e}")
            raise MailFetchError(f"IMAP fetch error: {str(e)}")

        return emails, new_uids

    @staticmethod
    async def forward_email(
        email_data: bytes,
        source_account_name: str,
        destination: str,
        smtp_config: Dict[str, Any],
    ) -> bool:
        """
        Forward an email to the destination address.

        Args:
            email_data: Raw email bytes
            source_account_name: Name of source account for labeling
            destination: Destination email address
            smtp_config: SMTP configuration dict with keys:
                - host: SMTP host
                - port: SMTP port
                - username: SMTP username
                - password: SMTP password
                - use_tls: Whether to use STARTTLS

        Returns:
            True if successful, False otherwise
        """
        try:
            loop = asyncio.get_event_loop()

            def send_email():
                # Parse the email
                msg = parser.BytesParser().parsebytes(email_data)

                # Create forwarding message
                forward_msg = MIMEMultipart("mixed")
                forward_msg["From"] = smtp_config["username"]
                forward_msg["To"] = destination
                forward_msg["Date"] = formatdate(localtime=True)
                forward_msg["Message-ID"] = make_msgid()

                # Preserve original subject with prefix
                original_subject = msg.get("Subject", "No Subject")
                forward_msg["Subject"] = (
                    f"[Fwd from {source_account_name}] {original_subject}"
                )

                # Add original headers
                header_info = f"Originally from: {msg.get('From', 'Unknown')}\n"
                header_info += f"Original Date: {msg.get('Date', 'Unknown')}\n"
                header_info += f"Original Subject: {original_subject}\n"
                header_info += f"Source Account: {source_account_name}\n"
                header_info += "-" * 50 + "\n\n"

                # Get email body
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode(
                                "utf-8", errors="ignore"
                            )
                            break
                else:
                    payload = msg.get_payload(decode=True)
                    if payload:
                        body = payload.decode("utf-8", errors="ignore")

                # Combine header and body
                full_body = header_info + body
                forward_msg.attach(MIMEText(full_body, "plain", "utf-8"))

                # Send via SMTP
                if smtp_config.get("use_tls", True):
                    server = smtplib.SMTP(
                        smtp_config["host"], smtp_config["port"], timeout=30
                    )
                    server.starttls()
                else:
                    server = smtplib.SMTP_SSL(
                        smtp_config["host"], smtp_config["port"], timeout=30
                    )

                try:
                    server.login(smtp_config["username"], smtp_config["password"])
                    server.send_message(forward_msg)
                    logger.info(f"Successfully forwarded email to {destination}")
                    return True
                finally:
                    try:
                        server.quit()
                    except Exception as e:
                        logger.warning(f"Error closing SMTP connection: {e}")

            return await loop.run_in_executor(None, send_email)

        except Exception as e:
            logger.error(f"Error forwarding email: {e}")
            raise MailForwardError(f"Forward error: {str(e)}")


class MailServerAutoDetect:
    """Auto-detect mail server settings based on email domain"""

    # Common mail server configurations
    KNOWN_PROVIDERS: Dict[str, Dict[str, Any]] = {
        "gmail.com": {
            "name": "Gmail",
            "pop3_ssl": {"host": "pop.gmail.com", "port": 995},
            "imap_ssl": {"host": "imap.gmail.com", "port": 993},
        },
        "googlemail.com": {
            "name": "Gmail",
            "pop3_ssl": {"host": "pop.gmail.com", "port": 995},
            "imap_ssl": {"host": "imap.gmail.com", "port": 993},
        },
        "outlook.com": {
            "name": "Outlook.com",
            "pop3_ssl": {"host": "outlook.office365.com", "port": 995},
            "imap_ssl": {"host": "outlook.office365.com", "port": 993},
        },
        "hotmail.com": {
            "name": "Hotmail",
            "pop3_ssl": {"host": "outlook.office365.com", "port": 995},
            "imap_ssl": {"host": "outlook.office365.com", "port": 993},
        },
        "live.com": {
            "name": "Live",
            "pop3_ssl": {"host": "outlook.office365.com", "port": 995},
            "imap_ssl": {"host": "outlook.office365.com", "port": 993},
        },
        "msn.com": {
            "name": "MSN",
            "pop3_ssl": {"host": "outlook.office365.com", "port": 995},
            "imap_ssl": {"host": "outlook.office365.com", "port": 993},
        },
        "outlook.de": {
            "name": "Outlook.de",
            "pop3_ssl": {"host": "outlook.office365.com", "port": 995},
            "imap_ssl": {"host": "outlook.office365.com", "port": 993},
        },
        "gmx.com": {
            "name": "GMX",
            "pop3_ssl": {"host": "pop.gmx.com", "port": 995},
            "imap_ssl": {"host": "imap.gmx.com", "port": 993},
        },
        "gmx.de": {
            "name": "GMX",
            "pop3_ssl": {"host": "pop.gmx.net", "port": 995},
            "imap_ssl": {"host": "imap.gmx.net", "port": 993},
        },
        "gmx.net": {
            "name": "GMX",
            "pop3_ssl": {"host": "pop.gmx.net", "port": 995},
            "imap_ssl": {"host": "imap.gmx.net", "port": 993},
        },
        "gmx.at": {
            "name": "GMX",
            "pop3_ssl": {"host": "pop.gmx.net", "port": 995},
            "imap_ssl": {"host": "imap.gmx.net", "port": 993},
        },
        "gmx.ch": {
            "name": "GMX",
            "pop3_ssl": {"host": "pop.gmx.net", "port": 995},
            "imap_ssl": {"host": "imap.gmx.net", "port": 993},
        },
        "web.de": {
            "name": "WEB.DE",
            "pop3_ssl": {"host": "pop3.web.de", "port": 995},
            "imap_ssl": {"host": "imap.web.de", "port": 993},
        },
        "t-online.de": {
            "name": "T-Online",
            "pop3_ssl": {"host": "securepop.t-online.de", "port": 995},
            "imap_ssl": {"host": "secureimap.t-online.de", "port": 993},
        },
        "yahoo.com": {
            "name": "Yahoo",
            "pop3_ssl": {"host": "pop.mail.yahoo.com", "port": 995},
            "imap_ssl": {"host": "imap.mail.yahoo.com", "port": 993},
        },
        "yahoo.de": {
            "name": "Yahoo",
            "pop3_ssl": {"host": "pop.mail.yahoo.com", "port": 995},
            "imap_ssl": {"host": "imap.mail.yahoo.com", "port": 993},
        },
        "yahoo.co.uk": {
            "name": "Yahoo",
            "pop3_ssl": {"host": "pop.mail.yahoo.com", "port": 995},
            "imap_ssl": {"host": "imap.mail.yahoo.com", "port": 993},
        },
        "ymail.com": {
            "name": "Yahoo",
            "pop3_ssl": {"host": "pop.mail.yahoo.com", "port": 995},
            "imap_ssl": {"host": "imap.mail.yahoo.com", "port": 993},
        },
        "aol.com": {
            "name": "AOL",
            "pop3_ssl": {"host": "pop.aol.com", "port": 995},
            "imap_ssl": {"host": "imap.aol.com", "port": 993},
        },
        "aim.com": {
            "name": "AOL",
            "pop3_ssl": {"host": "pop.aol.com", "port": 995},
            "imap_ssl": {"host": "imap.aol.com", "port": 993},
        },
        "online.de": {
            "name": "1&1 / IONOS",
            "pop3_ssl": {"host": "pop.ionos.de", "port": 995},
            "imap_ssl": {"host": "imap.ionos.de", "port": 993},
        },
        "onlinehome.de": {
            "name": "1&1 / IONOS",
            "pop3_ssl": {"host": "pop.ionos.de", "port": 995},
            "imap_ssl": {"host": "imap.ionos.de", "port": 993},
        },
        "1und1.de": {
            "name": "1&1 / IONOS",
            "pop3_ssl": {"host": "pop.ionos.de", "port": 995},
            "imap_ssl": {"host": "imap.ionos.de", "port": 993},
        },
        "freenet.de": {
            "name": "Freenet",
            "pop3_ssl": {"host": "mx.freenet.de", "port": 995},
            "imap_ssl": {"host": "mx.freenet.de", "port": 993},
        },
        "posteo.de": {
            "name": "Posteo",
            "imap_ssl": {"host": "posteo.de", "port": 993},
        },
        "posteo.net": {
            "name": "Posteo",
            "imap_ssl": {"host": "posteo.de", "port": 993},
        },
        "icloud.com": {
            "name": "iCloud",
            "imap_ssl": {"host": "imap.mail.me.com", "port": 993},
        },
        "me.com": {
            "name": "iCloud",
            "imap_ssl": {"host": "imap.mail.me.com", "port": 993},
        },
        "mac.com": {
            "name": "iCloud",
            "imap_ssl": {"host": "imap.mail.me.com", "port": 993},
        },
        "mail.de": {
            "name": "mail.de",
            "pop3_ssl": {"host": "pop.mail.de", "port": 995},
            "imap_ssl": {"host": "imap.mail.de", "port": 993},
        },
        "proton.me": {
            "name": "Proton Mail",
            "imap_ssl": {"host": "127.0.0.1", "port": 1143},
            "pop3_ssl": {"host": "127.0.0.1", "port": 1144},
        },
        "protonmail.com": {
            "name": "Proton Mail",
            "imap_ssl": {"host": "127.0.0.1", "port": 1143},
            "pop3_ssl": {"host": "127.0.0.1", "port": 1144},
        },
        "protonmail.ch": {
            "name": "Proton Mail",
            "imap_ssl": {"host": "127.0.0.1", "port": 1143},
            "pop3_ssl": {"host": "127.0.0.1", "port": 1144},
        },
        "pm.me": {
            "name": "Proton Mail",
            "imap_ssl": {"host": "127.0.0.1", "port": 1143},
            "pop3_ssl": {"host": "127.0.0.1", "port": 1144},
        },
    }

    @classmethod
    def detect(cls, email_address: str) -> List[Dict[str, Any]]:
        """
        Detect mail server settings for an email address.
        Returns list of possible configurations.
        """
        domain = email_address.split("@")[-1].lower()

        suggestions = []

        # Check if we have a known provider
        if domain in cls.KNOWN_PROVIDERS:
            provider = cls.KNOWN_PROVIDERS[domain]

            # Add POP3 SSL suggestion
            if "pop3_ssl" in provider:
                suggestions.append(
                    {
                        "protocol": "pop3_ssl",
                        "provider_name": provider["name"],
                        "host": provider["pop3_ssl"]["host"],
                        "port": provider["pop3_ssl"]["port"],
                        "use_ssl": True,
                        "use_tls": False,
                    }
                )

            # Add IMAP SSL suggestion
            if "imap_ssl" in provider:
                suggestions.append(
                    {
                        "protocol": "imap_ssl",
                        "provider_name": provider["name"],
                        "host": provider["imap_ssl"]["host"],
                        "port": provider["imap_ssl"]["port"],
                        "use_ssl": True,
                        "use_tls": False,
                    }
                )
        else:
            # Generic suggestions based on common patterns
            suggestions.extend(
                [
                    {
                        "protocol": "pop3_ssl",
                        "provider_name": "Generic",
                        "host": f"pop.{domain}",
                        "port": 995,
                        "use_ssl": True,
                        "use_tls": False,
                    },
                    {
                        "protocol": "pop3_ssl",
                        "provider_name": "Generic",
                        "host": f"pop3.{domain}",
                        "port": 995,
                        "use_ssl": True,
                        "use_tls": False,
                    },
                    {
                        "protocol": "imap_ssl",
                        "provider_name": "Generic",
                        "host": f"imap.{domain}",
                        "port": 993,
                        "use_ssl": True,
                        "use_tls": False,
                    },
                    {
                        "protocol": "imap_ssl",
                        "provider_name": "Generic",
                        "host": f"mail.{domain}",
                        "port": 993,
                        "use_ssl": True,
                        "use_tls": False,
                    },
                ]
            )

        return suggestions
