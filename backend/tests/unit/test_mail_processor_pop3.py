"""
Unit tests for POP3 fetch, connection testing, and email forwarding in MailProcessor.

These tests cover the methods not exercised by test_mail_processor_imap.py:
  - test_connection() routing to POP3 / IMAP helpers
  - _test_pop3_connection() for POP3_SSL and plain POP3
  - _test_imap_connection() for IMAP_SSL and plain IMAP
  - fetch_emails() delegation to POP3 / IMAP
  - _fetch_pop3_emails() end-to-end: UIDL, skip-seen, max_count, delete, errors
  - forward_email() via STARTTLS and SSL, multipart / plain, error paths
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.database_models import MailProtocol
from app.services.mail_processor import (
    MailProcessor,
    MailFetchError,
    MailForwardError,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_account(
    protocol="pop3_ssl",
    host="pop.example.com",
    port=995,
    username="user@example.com",
    delete_after_forward=False,
    account_id=1,
    max_emails_per_check=50,
):
    """Return a minimal MailAccount-like mock."""
    proto_map = {
        "pop3_ssl": MailProtocol.POP3_SSL,
        "pop3": MailProtocol.POP3,
        "imap_ssl": MailProtocol.IMAP_SSL,
        "imap": MailProtocol.IMAP,
    }
    account = MagicMock()
    account.id = account_id
    account.host = host
    account.port = port
    account.username = username
    account.delete_after_forward = delete_after_forward
    account.protocol = proto_map[protocol]
    account.max_emails_per_check = max_emails_per_check
    return account


# ---------------------------------------------------------------------------
# test_connection – routing
# ---------------------------------------------------------------------------


class TestTestConnection:
    """test_connection() should delegate to POP3 or IMAP helpers."""

    async def test_routes_to_pop3_for_pop3_ssl(self):
        account = _make_account(protocol="pop3_ssl")
        proc = MailProcessor(account, "secret")
        with patch.object(
            proc, "_test_pop3_connection", new_callable=AsyncMock
        ) as mock:
            mock.return_value = (True, "ok")
            result = await proc.test_connection()
        mock.assert_awaited_once()
        assert result == (True, "ok")

    async def test_routes_to_pop3_for_pop3(self):
        account = _make_account(protocol="pop3")
        proc = MailProcessor(account, "secret")
        with patch.object(
            proc, "_test_pop3_connection", new_callable=AsyncMock
        ) as mock:
            mock.return_value = (True, "ok")
            result = await proc.test_connection()
        mock.assert_awaited_once()
        assert result == (True, "ok")

    async def test_routes_to_imap_for_imap_ssl(self):
        account = _make_account(protocol="imap_ssl")
        proc = MailProcessor(account, "secret")
        with patch.object(
            proc, "_test_imap_connection", new_callable=AsyncMock
        ) as mock:
            mock.return_value = (True, "connected")
            result = await proc.test_connection()
        mock.assert_awaited_once()
        assert result == (True, "connected")

    async def test_routes_to_imap_for_imap(self):
        account = _make_account(protocol="imap")
        proc = MailProcessor(account, "secret")
        with patch.object(
            proc, "_test_imap_connection", new_callable=AsyncMock
        ) as mock:
            mock.return_value = (True, "connected")
            result = await proc.test_connection()
        mock.assert_awaited_once()
        assert result == (True, "connected")

    async def test_returns_false_on_unexpected_exception(self):
        account = _make_account(protocol="imap_ssl")
        proc = MailProcessor(account, "secret")
        with patch.object(
            proc, "_test_imap_connection", new_callable=AsyncMock
        ) as mock:
            mock.side_effect = RuntimeError("boom")
            success, msg = await proc.test_connection()
        assert success is False
        assert "boom" in msg


# ---------------------------------------------------------------------------
# _test_pop3_connection
# ---------------------------------------------------------------------------


class TestTestPop3Connection:
    """Unit tests for _test_pop3_connection()."""

    @patch("app.services.mail_processor.poplib")
    async def test_pop3_ssl_success(self, mock_poplib):
        """POP3_SSL: successful connection reports message count."""
        mock_conn = MagicMock()
        mock_conn.stat.return_value = (42, 123456)
        mock_poplib.POP3_SSL.return_value = mock_conn

        account = _make_account(protocol="pop3_ssl")
        proc = MailProcessor(account, "secret")
        success, msg = await proc._test_pop3_connection()

        assert success is True
        assert "42 messages" in msg
        mock_conn.user.assert_called_once_with("user@example.com")
        mock_conn.pass_.assert_called_once_with("secret")
        mock_conn.quit.assert_called_once()

    @patch("app.services.mail_processor.poplib")
    async def test_pop3_plain_success(self, mock_poplib):
        """Plain POP3: uses POP3 (not POP3_SSL)."""
        mock_conn = MagicMock()
        mock_conn.stat.return_value = (10, 5000)
        mock_poplib.POP3.return_value = mock_conn

        account = _make_account(protocol="pop3", port=110)
        proc = MailProcessor(account, "secret")
        success, msg = await proc._test_pop3_connection()

        assert success is True
        assert "10 messages" in msg
        mock_poplib.POP3.assert_called_once()
        mock_poplib.POP3_SSL.assert_not_called()

    @patch("app.services.mail_processor.poplib")
    async def test_pop3_auth_error(self, mock_poplib):
        """Authentication failure returns False with auth message."""
        import poplib as real_poplib

        mock_conn = MagicMock()
        mock_conn.user.side_effect = real_poplib.error_proto("authentication failed")
        mock_poplib.POP3_SSL.return_value = mock_conn
        mock_poplib.error_proto = real_poplib.error_proto

        account = _make_account(protocol="pop3_ssl")
        proc = MailProcessor(account, "secret")
        success, msg = await proc._test_pop3_connection()

        assert success is False
        assert "Authentication failed" in msg

    @patch("app.services.mail_processor.poplib")
    async def test_pop3_protocol_error(self, mock_poplib):
        """Non-auth protocol error returns False with protocol error message."""
        import poplib as real_poplib

        mock_conn = MagicMock()
        mock_conn.user.side_effect = real_poplib.error_proto("some protocol error")
        mock_poplib.POP3_SSL.return_value = mock_conn
        mock_poplib.error_proto = real_poplib.error_proto

        account = _make_account(protocol="pop3_ssl")
        proc = MailProcessor(account, "secret")
        success, msg = await proc._test_pop3_connection()

        assert success is False
        assert "POP3 protocol error" in msg

    @patch("app.services.mail_processor.poplib")
    async def test_pop3_generic_exception(self, mock_poplib):
        """Generic exception returns False with connection-failed message."""
        import poplib as real_poplib

        mock_poplib.error_proto = real_poplib.error_proto
        mock_poplib.POP3_SSL.side_effect = OSError("connection refused")

        account = _make_account(protocol="pop3_ssl")
        proc = MailProcessor(account, "secret")
        success, msg = await proc._test_pop3_connection()

        assert success is False
        assert "Connection failed" in msg


# ---------------------------------------------------------------------------
# _test_imap_connection
# ---------------------------------------------------------------------------


class TestTestImapConnection:
    """Unit tests for _test_imap_connection()."""

    @patch("app.services.mail_processor.aioimaplib")
    async def test_imap_ssl_success(self, mock_aioimaplib):
        """IMAP_SSL: successful connection reports message count."""
        mock_client = AsyncMock()
        mock_aioimaplib.IMAP4_SSL.return_value = mock_client

        # login response
        login_resp = MagicMock()
        login_resp.result = "OK"
        mock_client.login.return_value = login_resp

        # search response with 3 messages
        search_resp = MagicMock()
        search_resp.lines = [b"1 2 3"]
        mock_client.search.return_value = search_resp

        account = _make_account(protocol="imap_ssl", host="imap.example.com", port=993)
        proc = MailProcessor(account, "secret")
        success, msg = await proc._test_imap_connection()

        assert success is True
        assert "3 messages" in msg
        mock_client.wait_hello_from_server.assert_awaited_once()
        mock_client.login.assert_awaited_once()
        mock_client.select.assert_awaited_once_with("INBOX")
        mock_client.logout.assert_awaited_once()

    @patch("app.services.mail_processor.aioimaplib")
    async def test_imap_plain_success(self, mock_aioimaplib):
        """Plain IMAP: uses IMAP4, not IMAP4_SSL."""
        mock_client = AsyncMock()
        mock_aioimaplib.IMAP4.return_value = mock_client

        login_resp = MagicMock()
        login_resp.result = "OK"
        mock_client.login.return_value = login_resp

        search_resp = MagicMock()
        search_resp.lines = [b"1"]
        mock_client.search.return_value = search_resp

        account = _make_account(protocol="imap", host="imap.example.com", port=143)
        proc = MailProcessor(account, "secret")
        success, msg = await proc._test_imap_connection()

        assert success is True
        mock_aioimaplib.IMAP4.assert_called_once()
        mock_aioimaplib.IMAP4_SSL.assert_not_called()

    @patch("app.services.mail_processor.aioimaplib")
    async def test_imap_auth_failure(self, mock_aioimaplib):
        """Authentication failure returns False with auth failure message."""
        mock_client = AsyncMock()
        mock_aioimaplib.IMAP4_SSL.return_value = mock_client

        login_resp = MagicMock()
        login_resp.result = "NO"
        login_resp.lines = ["Invalid credentials"]
        mock_client.login.return_value = login_resp

        account = _make_account(protocol="imap_ssl", host="imap.example.com", port=993)
        proc = MailProcessor(account, "secret")
        success, msg = await proc._test_imap_connection()

        assert success is False
        assert "Authentication failed" in msg

    @patch("app.services.mail_processor.aioimaplib")
    async def test_imap_generic_exception(self, mock_aioimaplib):
        """Generic exception returns False with IMAP-connection-failed message."""
        mock_aioimaplib.IMAP4_SSL.side_effect = OSError("network unreachable")

        account = _make_account(protocol="imap_ssl", host="imap.example.com", port=993)
        proc = MailProcessor(account, "secret")
        success, msg = await proc._test_imap_connection()

        assert success is False
        assert "IMAP connection failed" in msg


# ---------------------------------------------------------------------------
# fetch_emails – routing and defaults
# ---------------------------------------------------------------------------


class TestFetchEmails:
    """fetch_emails() should route and fill defaults correctly."""

    async def test_delegates_to_pop3_for_pop3_ssl(self):
        account = _make_account(protocol="pop3_ssl", max_emails_per_check=25)
        proc = MailProcessor(account, "secret")
        with patch.object(proc, "_fetch_pop3_emails", new_callable=AsyncMock) as mock:
            mock.return_value = ([b"email"], ["uid1"])
            result = await proc.fetch_emails()
        # Should use max_emails_per_check as default
        mock.assert_awaited_once_with(25, set())
        assert result == ([b"email"], ["uid1"])

    async def test_delegates_to_imap_for_imap_ssl(self):
        account = _make_account(protocol="imap_ssl")
        proc = MailProcessor(account, "secret")
        with patch.object(proc, "_fetch_imap_emails", new_callable=AsyncMock) as mock:
            mock.return_value = ([], [])
            await proc.fetch_emails(max_count=10, already_seen_uids={"u1"})
        mock.assert_awaited_once_with(10, {"u1"})

    async def test_uses_max_count_when_provided(self):
        account = _make_account(protocol="pop3", max_emails_per_check=100)
        proc = MailProcessor(account, "secret")
        with patch.object(proc, "_fetch_pop3_emails", new_callable=AsyncMock) as mock:
            mock.return_value = ([], [])
            await proc.fetch_emails(max_count=5)
        mock.assert_awaited_once_with(5, set())

    async def test_uses_max_emails_per_check_when_no_max_count(self):
        account = _make_account(protocol="pop3_ssl", max_emails_per_check=77)
        proc = MailProcessor(account, "secret")
        with patch.object(proc, "_fetch_pop3_emails", new_callable=AsyncMock) as mock:
            mock.return_value = ([], [])
            await proc.fetch_emails()
        mock.assert_awaited_once_with(77, set())


# ---------------------------------------------------------------------------
# _fetch_pop3_emails
# ---------------------------------------------------------------------------


class TestFetchPop3Emails:
    """Unit tests for _fetch_pop3_emails()."""

    def _make_pop3_mock(self, uid_entries, retr_data=None, retr_errors=None):
        """Build a mock POP3 connection.

        Args:
            uid_entries: list of (msg_num, uid_string) pairs
            retr_data: dict mapping msg_num -> bytes to return from retr()
            retr_errors: dict mapping msg_num -> exception for retr()
        """
        mock_conn = MagicMock()
        uidl_lines = [f"{n} {uid}".encode() for n, uid in uid_entries]
        mock_conn.uidl.return_value = (b"+OK", uidl_lines, 0)

        retr_data = retr_data or {}
        retr_errors = retr_errors or {}

        def retr_side_effect(msg_num):
            if msg_num in retr_errors:
                raise retr_errors[msg_num]
            data = retr_data.get(msg_num, b"From: test\r\nSubject: hi\r\n\r\nbody")
            return (b"+OK", data.split(b"\r\n"), len(data))

        mock_conn.retr.side_effect = retr_side_effect
        return mock_conn

    @patch("app.services.mail_processor.poplib")
    async def test_fetch_pop3_ssl_basic(self, mock_poplib):
        """POP3_SSL: fetches messages and returns email data + UIDs."""
        mock_conn = self._make_pop3_mock(
            uid_entries=[(1, "abc"), (2, "def")],
            retr_data={
                1: b"From: a@b.com\r\nSubject: A\r\n\r\nBody A",
                2: b"From: c@d.com\r\nSubject: B\r\n\r\nBody B",
            },
        )
        mock_poplib.POP3_SSL.return_value = mock_conn

        account = _make_account(protocol="pop3_ssl")
        proc = MailProcessor(account, "secret")
        emails, uids = await proc._fetch_pop3_emails(10, set())

        assert len(emails) == 2
        assert uids == ["abc", "def"]
        mock_conn.quit.assert_called_once()

    @patch("app.services.mail_processor.poplib")
    async def test_fetch_pop3_plain(self, mock_poplib):
        """Plain POP3: uses POP3 (not POP3_SSL)."""
        mock_conn = self._make_pop3_mock(uid_entries=[(1, "uid1")])
        mock_poplib.POP3.return_value = mock_conn

        account = _make_account(protocol="pop3", port=110)
        proc = MailProcessor(account, "secret")
        emails, uids = await proc._fetch_pop3_emails(10, set())

        assert len(emails) == 1
        assert uids == ["uid1"]
        mock_poplib.POP3.assert_called_once()
        mock_poplib.POP3_SSL.assert_not_called()

    @patch("app.services.mail_processor.poplib")
    async def test_skips_already_seen_uids(self, mock_poplib):
        """Already-seen UIDs are skipped."""
        mock_conn = self._make_pop3_mock(
            uid_entries=[(1, "seen1"), (2, "new1"), (3, "seen2")]
        )
        mock_poplib.POP3_SSL.return_value = mock_conn

        account = _make_account(protocol="pop3_ssl")
        proc = MailProcessor(account, "secret")
        emails, uids = await proc._fetch_pop3_emails(10, {"seen1", "seen2"})

        assert uids == ["new1"]
        assert len(emails) == 1
        # retr should only be called for msg 2
        mock_conn.retr.assert_called_once_with(2)

    @patch("app.services.mail_processor.poplib")
    async def test_respects_max_count(self, mock_poplib):
        """Only max_count messages are fetched."""
        mock_conn = self._make_pop3_mock(
            uid_entries=[(1, "a"), (2, "b"), (3, "c"), (4, "d")]
        )
        mock_poplib.POP3_SSL.return_value = mock_conn

        account = _make_account(protocol="pop3_ssl")
        proc = MailProcessor(account, "secret")
        emails, uids = await proc._fetch_pop3_emails(2, set())

        assert len(emails) == 2
        assert len(uids) == 2

    @patch("app.services.mail_processor.poplib")
    async def test_no_delete_during_fetch(self, mock_poplib):
        """_fetch_pop3_emails must NOT call dele() regardless of delete_after_forward.

        Deletion is deferred to post_process_pop3() so that only successfully
        forwarded messages are removed from the source mailbox.
        """
        mock_conn = self._make_pop3_mock(uid_entries=[(1, "a"), (2, "b")])
        mock_poplib.POP3_SSL.return_value = mock_conn

        account = _make_account(protocol="pop3_ssl", delete_after_forward=True)
        proc = MailProcessor(account, "secret")
        await proc._fetch_pop3_emails(10, set())

        mock_conn.dele.assert_not_called()

    @patch("app.services.mail_processor.poplib")
    async def test_no_delete_when_disabled(self, mock_poplib):
        """delete_after_forward=False: no dele() calls."""
        mock_conn = self._make_pop3_mock(uid_entries=[(1, "a")])
        mock_poplib.POP3_SSL.return_value = mock_conn

        account = _make_account(protocol="pop3_ssl", delete_after_forward=False)
        proc = MailProcessor(account, "secret")
        await proc._fetch_pop3_emails(10, set())

        mock_conn.dele.assert_not_called()

    @patch("app.services.mail_processor.poplib")
    async def test_individual_retr_error_does_not_abort(self, mock_poplib):
        """A single message retr() failure doesn't stop the entire fetch."""
        mock_conn = self._make_pop3_mock(
            uid_entries=[(1, "a"), (2, "b"), (3, "c")],
            retr_errors={2: Exception("corrupt message")},
        )
        mock_poplib.POP3_SSL.return_value = mock_conn

        account = _make_account(protocol="pop3_ssl")
        proc = MailProcessor(account, "secret")
        emails, uids = await proc._fetch_pop3_emails(10, set())

        # Messages 1 and 3 should still be fetched
        assert len(emails) == 2
        assert "a" in uids
        assert "c" in uids
        assert "b" not in uids

    @patch("app.services.mail_processor.poplib")
    async def test_fetch_does_not_call_dele(self, mock_poplib):
        """_fetch_pop3_emails never calls dele() — deletion is in post_process_pop3."""
        mock_conn = self._make_pop3_mock(uid_entries=[(1, "a")])
        mock_poplib.POP3_SSL.return_value = mock_conn

        account = _make_account(protocol="pop3_ssl", delete_after_forward=True)
        proc = MailProcessor(account, "secret")
        emails, uids = await proc._fetch_pop3_emails(10, set())
        assert len(emails) == 1
        mock_conn.dele.assert_not_called()

    @patch("app.services.mail_processor.poplib")
    async def test_connection_failure_raises_mail_fetch_error(self, mock_poplib):
        """Connection failure raises MailFetchError."""
        mock_poplib.POP3_SSL.side_effect = OSError("connection refused")

        account = _make_account(protocol="pop3_ssl")
        proc = MailProcessor(account, "secret")
        with pytest.raises(MailFetchError, match="POP3 fetch error"):
            await proc._fetch_pop3_emails(10, set())

    @patch("app.services.mail_processor.poplib")
    async def test_empty_mailbox(self, mock_poplib):
        """Empty mailbox returns empty lists."""
        mock_conn = self._make_pop3_mock(uid_entries=[])
        mock_poplib.POP3_SSL.return_value = mock_conn

        account = _make_account(protocol="pop3_ssl")
        proc = MailProcessor(account, "secret")
        emails, uids = await proc._fetch_pop3_emails(10, set())

        assert emails == []
        assert uids == []

    @patch("app.services.mail_processor.poplib")
    async def test_uidl_parsing_handles_extra_whitespace(self, mock_poplib):
        """UIDL entries with extra whitespace in UID are stripped."""
        mock_conn = MagicMock()
        mock_conn.uidl.return_value = (b"+OK", [b"1 uid_with_space  "], 0)
        mock_conn.retr.return_value = (
            b"+OK",
            [b"From: x", b"", b"body"],
            10,
        )
        mock_poplib.POP3_SSL.return_value = mock_conn

        account = _make_account(protocol="pop3_ssl")
        proc = MailProcessor(account, "secret")
        emails, uids = await proc._fetch_pop3_emails(10, set())

        assert uids == ["uid_with_space"]

    @patch("app.services.mail_processor.poplib")
    async def test_malformed_uidl_entry_is_skipped(self, mock_poplib):
        """UIDL entry without a space (malformed) is silently skipped."""
        mock_conn = MagicMock()
        # One malformed entry (no space), one valid entry
        mock_conn.uidl.return_value = (
            b"+OK",
            [b"malformed_no_space", b"2 valid_uid"],
            0,
        )
        mock_conn.retr.return_value = (b"+OK", [b"From: x", b"", b"body"], 10)
        mock_poplib.POP3_SSL.return_value = mock_conn

        account = _make_account(protocol="pop3_ssl")
        proc = MailProcessor(account, "secret")
        emails, uids = await proc._fetch_pop3_emails(10, set())

        # Only the valid entry should be processed
        assert uids == ["valid_uid"]
        assert len(emails) == 1


# ---------------------------------------------------------------------------
# post_process_pop3 tests
# ---------------------------------------------------------------------------


class TestPostProcessPop3:
    """Unit tests for post_process_pop3()."""

    @patch("app.services.mail_processor.poplib")
    async def test_deletes_only_forwarded_uids(self, mock_poplib):
        """Only successfully forwarded UIDs are deleted from the source mailbox."""
        mock_conn = MagicMock()
        mock_conn.uidl.return_value = (b"+OK", [b"1 uid-a", b"2 uid-b", b"3 uid-c"], 0)
        mock_poplib.POP3_SSL.return_value = mock_conn

        account = _make_account(protocol="pop3_ssl", delete_after_forward=True)
        proc = MailProcessor(account, "secret")
        await proc.post_process_pop3(["uid-a", "uid-c"])

        # Only messages 1 and 3 should be deleted (uid-a and uid-c)
        assert mock_conn.dele.call_count == 2
        mock_conn.dele.assert_any_call(1)
        mock_conn.dele.assert_any_call(3)
        mock_conn.quit.assert_called_once()

    @patch("app.services.mail_processor.poplib")
    async def test_noop_when_delete_after_forward_false(self, mock_poplib):
        """post_process_pop3 does nothing when delete_after_forward=False."""
        mock_conn = MagicMock()
        mock_poplib.POP3_SSL.return_value = mock_conn

        account = _make_account(protocol="pop3_ssl", delete_after_forward=False)
        proc = MailProcessor(account, "secret")
        await proc.post_process_pop3(["uid-a"])

        mock_poplib.POP3_SSL.assert_not_called()

    @patch("app.services.mail_processor.poplib")
    async def test_noop_on_empty_uid_list(self, mock_poplib):
        """post_process_pop3 does nothing when the UID list is empty."""
        mock_conn = MagicMock()
        mock_poplib.POP3_SSL.return_value = mock_conn

        account = _make_account(protocol="pop3_ssl", delete_after_forward=True)
        proc = MailProcessor(account, "secret")
        await proc.post_process_pop3([])

        mock_poplib.POP3_SSL.assert_not_called()

    @patch("app.services.mail_processor.poplib")
    async def test_dele_error_does_not_abort(self, mock_poplib):
        """A dele() error is logged but post_process_pop3 does not raise."""
        mock_conn = MagicMock()
        mock_conn.uidl.return_value = (b"+OK", [b"1 uid-a"], 0)
        mock_conn.dele.side_effect = Exception("delete failed")
        mock_poplib.POP3_SSL.return_value = mock_conn

        account = _make_account(protocol="pop3_ssl", delete_after_forward=True)
        proc = MailProcessor(account, "secret")
        await proc.post_process_pop3(["uid-a"])  # must not raise

        mock_conn.quit.assert_called_once()

    @patch("app.services.mail_processor.poplib")
    async def test_connection_error_is_swallowed(self, mock_poplib):
        """A connection failure is logged but does not propagate."""
        mock_poplib.POP3_SSL.side_effect = OSError("connection refused")

        account = _make_account(protocol="pop3_ssl", delete_after_forward=True)
        proc = MailProcessor(account, "secret")
        await proc.post_process_pop3(["uid-a"])  # must not raise





class TestForwardEmail:
    """Unit tests for forward_email()."""

    SMTP_CONFIG = {
        "host": "smtp.example.com",
        "port": 587,
        "username": "sender@example.com",
        "password": "smtp_pass",
        "use_tls": True,
    }

    SMTP_CONFIG_SSL = {
        "host": "smtp.example.com",
        "port": 465,
        "username": "sender@example.com",
        "password": "smtp_pass",
        "use_tls": False,
    }

    SIMPLE_EMAIL = (
        b"From: original@sender.com\r\n"
        b"Date: Mon, 01 Jan 2024 12:00:00 +0000\r\n"
        b"Subject: Test Subject\r\n"
        b"\r\n"
        b"Hello, this is the body."
    )

    MULTIPART_EMAIL = (
        b"From: original@sender.com\r\n"
        b"Date: Mon, 01 Jan 2024 12:00:00 +0000\r\n"
        b"Subject: Multipart Test\r\n"
        b"MIME-Version: 1.0\r\n"
        b'Content-Type: multipart/mixed; boundary="boundary123"\r\n'
        b"\r\n"
        b"--boundary123\r\n"
        b"Content-Type: text/plain; charset=utf-8\r\n"
        b"\r\n"
        b"Plain text body.\r\n"
        b"--boundary123--\r\n"
    )

    @patch("app.services.mail_processor.smtplib")
    async def test_forward_starttls(self, mock_smtplib):
        """STARTTLS path: SMTP + starttls() is used."""
        mock_server = MagicMock()
        mock_smtplib.SMTP.return_value = mock_server

        result = await MailProcessor.forward_email(
            self.SIMPLE_EMAIL, "MyAccount", "dest@example.com", self.SMTP_CONFIG
        )

        assert result is True
        mock_smtplib.SMTP.assert_called_once_with("smtp.example.com", 587, timeout=30)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("sender@example.com", "smtp_pass")
        mock_server.send_message.assert_called_once()
        mock_server.quit.assert_called_once()

    @patch("app.services.mail_processor.smtplib")
    async def test_forward_ssl(self, mock_smtplib):
        """SSL path: SMTP_SSL is used when use_tls=False."""
        mock_server = MagicMock()
        mock_smtplib.SMTP_SSL.return_value = mock_server

        result = await MailProcessor.forward_email(
            self.SIMPLE_EMAIL, "MyAccount", "dest@example.com", self.SMTP_CONFIG_SSL
        )

        assert result is True
        mock_smtplib.SMTP_SSL.assert_called_once_with(
            "smtp.example.com", 465, timeout=30
        )
        mock_server.starttls.assert_not_called()
        mock_server.login.assert_called_once()
        mock_server.send_message.assert_called_once()

    @patch("app.services.mail_processor.smtplib")
    async def test_forward_preserves_subject(self, mock_smtplib):
        """Forwarded email subject includes source account name and original subject."""
        mock_server = MagicMock()
        mock_smtplib.SMTP.return_value = mock_server

        await MailProcessor.forward_email(
            self.SIMPLE_EMAIL, "Work Mail", "dest@example.com", self.SMTP_CONFIG
        )

        sent_msg = mock_server.send_message.call_args[0][0]
        assert "[Fwd from Work Mail]" in sent_msg["Subject"]
        assert "Test Subject" in sent_msg["Subject"]

    @patch("app.services.mail_processor.smtplib")
    async def test_forward_sets_from_and_to(self, mock_smtplib):
        """Forwarded email has correct From/To headers."""
        mock_server = MagicMock()
        mock_smtplib.SMTP.return_value = mock_server

        await MailProcessor.forward_email(
            self.SIMPLE_EMAIL, "Acct", "dest@example.com", self.SMTP_CONFIG
        )

        sent_msg = mock_server.send_message.call_args[0][0]
        assert sent_msg["From"] == "sender@example.com"
        assert sent_msg["To"] == "dest@example.com"

    @patch("app.services.mail_processor.smtplib")
    async def test_forward_multipart_email(self, mock_smtplib):
        """Multipart email: extracts text/plain body."""
        mock_server = MagicMock()
        mock_smtplib.SMTP.return_value = mock_server

        result = await MailProcessor.forward_email(
            self.MULTIPART_EMAIL, "Acct", "dest@example.com", self.SMTP_CONFIG
        )

        assert result is True
        sent_msg = mock_server.send_message.call_args[0][0]
        # Body should contain original header info and plain text
        payload = sent_msg.get_payload()
        assert len(payload) > 0

    @patch("app.services.mail_processor.smtplib")
    async def test_forward_email_body_contains_header_info(self, mock_smtplib):
        """Forwarded body includes original From, Date, Subject, Source Account."""
        mock_server = MagicMock()
        mock_smtplib.SMTP.return_value = mock_server

        await MailProcessor.forward_email(
            self.SIMPLE_EMAIL, "WorkAccount", "dest@example.com", self.SMTP_CONFIG
        )

        sent_msg = mock_server.send_message.call_args[0][0]
        # Get body from the MIME parts
        body_part = sent_msg.get_payload()[0]
        body_text = body_part.get_payload(decode=True).decode("utf-8")

        assert "Originally from: original@sender.com" in body_text
        assert "Source Account: WorkAccount" in body_text
        assert "Hello, this is the body." in body_text

    @patch("app.services.mail_processor.smtplib")
    async def test_forward_smtp_error_raises_forward_error(self, mock_smtplib):
        """SMTP send failure raises MailForwardError."""
        mock_server = MagicMock()
        mock_server.login.side_effect = Exception("auth failed")
        mock_smtplib.SMTP.return_value = mock_server

        with pytest.raises(MailForwardError, match="Forward error"):
            await MailProcessor.forward_email(
                self.SIMPLE_EMAIL, "Acct", "dest@example.com", self.SMTP_CONFIG
            )

    @patch("app.services.mail_processor.smtplib")
    async def test_forward_quit_error_does_not_mask_success(self, mock_smtplib):
        """If quit() fails after successful send, True is still returned."""
        mock_server = MagicMock()
        mock_server.quit.side_effect = Exception("quit error")
        mock_smtplib.SMTP.return_value = mock_server

        result = await MailProcessor.forward_email(
            self.SIMPLE_EMAIL, "Acct", "dest@example.com", self.SMTP_CONFIG
        )

        assert result is True

    @patch("app.services.mail_processor.smtplib")
    async def test_forward_connection_error_raises_forward_error(self, mock_smtplib):
        """SMTP connection failure raises MailForwardError."""
        mock_smtplib.SMTP.side_effect = OSError("connection refused")

        with pytest.raises(MailForwardError, match="Forward error"):
            await MailProcessor.forward_email(
                self.SIMPLE_EMAIL, "Acct", "dest@example.com", self.SMTP_CONFIG
            )

    @patch("app.services.mail_processor.smtplib")
    async def test_forward_email_without_payload(self, mock_smtplib):
        """Email with no payload body is forwarded with just header info."""
        mock_server = MagicMock()
        mock_smtplib.SMTP.return_value = mock_server

        empty_body_email = b"From: x@y.com\r\n" b"Subject: Empty\r\n" b"\r\n"

        result = await MailProcessor.forward_email(
            empty_body_email, "Acct", "dest@example.com", self.SMTP_CONFIG
        )

        assert result is True

    @patch("app.services.mail_processor.smtplib")
    async def test_forward_multipart_no_text_plain(self, mock_smtplib):
        """Multipart email with no text/plain part forwards with empty body."""
        mock_server = MagicMock()
        mock_smtplib.SMTP.return_value = mock_server

        html_only_email = (
            b"From: x@y.com\r\n"
            b"Subject: HTML Only\r\n"
            b"MIME-Version: 1.0\r\n"
            b'Content-Type: multipart/mixed; boundary="bnd"\r\n'
            b"\r\n"
            b"--bnd\r\n"
            b"Content-Type: text/html; charset=utf-8\r\n"
            b"\r\n"
            b"<p>HTML body</p>\r\n"
            b"--bnd--\r\n"
        )

        result = await MailProcessor.forward_email(
            html_only_email, "Acct", "dest@example.com", self.SMTP_CONFIG
        )

        assert result is True
        sent_msg = mock_server.send_message.call_args[0][0]
        body_part = sent_msg.get_payload()[0]
        body_text = body_part.get_payload(decode=True).decode("utf-8")
        # Body should have header info but no HTML content extracted
        assert "Originally from: x@y.com" in body_text
