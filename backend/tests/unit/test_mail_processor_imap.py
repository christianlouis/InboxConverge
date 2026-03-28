"""
Unit tests for the IMAP fetch logic in MailProcessor.

These tests verify that _fetch_imap_emails:
  - Uses a plain SEARCH UNSEEN (not uid("search")) to get sequence numbers
  - Resolves sequence numbers to UIDs via a lightweight FETCH (UID)
  - Uses UID FETCH / UID STORE for all subsequent operations
  - Batches stale-UID re-marking into a single STORE command
  - Does NOT issue a per-message STORE for Seen (RFC822 sets it implicitly)
  - Batches Deleted STORE into a single command when delete_after_forward=True
  - Uses RFC 3501 parenthesised flag syntax, e.g. +FLAGS (\\Seen)
  - Handles an empty UNSEEN result without error
  - Handles individual message fetch failures gracefully
  - Always attempts logout in the finally block
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, call, patch

# ---------------------------------------------------------------------------
# Helpers to build lightweight fakes
# ---------------------------------------------------------------------------


def _make_account(
    protocol="imap_ssl",
    host="imap.example.com",
    port=993,
    username="user@example.com",
    delete_after_forward=False,
    account_id=1,
):
    """Return a minimal MailAccount-like mock."""
    from app.models.database_models import MailProtocol

    account = MagicMock()
    account.id = account_id
    account.host = host
    account.port = port
    account.username = username
    account.delete_after_forward = delete_after_forward
    account.protocol = (
        MailProtocol.IMAP_SSL if protocol == "imap_ssl" else MailProtocol.IMAP
    )
    return account


def _make_imap_response(result="OK", lines=None):
    """Return an object that looks like an aioimaplib ImapResponse."""
    resp = MagicMock()
    resp.result = result
    resp.lines = lines if lines is not None else [b""]
    return resp


def _make_fetch_response(uid_str: str, email_bytes: bytes):
    """
    Simulate the lines that aioimaplib returns for a UID FETCH (RFC822) call.

    The typical structure is:
      [b'<seq> (UID <uid> RFC822 {<size>}', <email_data>, b')']
    """
    header = f"1 (UID {uid_str} RFC822 {{12345}}".encode()
    return _make_imap_response(result="OK", lines=[header, email_bytes, b")"])


def _make_uid_list_response(seq_uid_pairs):
    """
    Simulate the response from fetch(seq_string, "(UID)").

    seq_uid_pairs is a list of (seq_num_str, uid_str) tuples. Each entry
    produces a line like b'1 (UID 42)' which the production code parses with
    a regex.
    """
    lines = [f"{seq} (UID {uid})".encode() for seq, uid in seq_uid_pairs]
    return _make_imap_response(result="OK", lines=lines)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestFetchImapEmailsUidCommands:
    """Verify UID-based command usage in _fetch_imap_emails."""

    @pytest.fixture
    def processor(self):
        from app.services.mail_processor import MailProcessor

        account = _make_account()
        return MailProcessor(account=account, decrypted_password="secret")

    @pytest.fixture
    def mock_imap(self):
        """A mock aioimaplib client whose async methods are AsyncMock."""
        client = MagicMock()
        client.wait_hello_from_server = AsyncMock()
        client.login = AsyncMock()
        client.select = AsyncMock()
        client.search = AsyncMock()
        client.fetch = AsyncMock()
        client.uid = AsyncMock()
        client.logout = AsyncMock()
        return client

    async def test_uses_plain_search_not_uid_search(self, processor, mock_imap):
        """SEARCH must be issued as a plain SEARCH UNSEEN, not via uid()."""
        mock_imap.search.return_value = _make_imap_response(result="OK", lines=[b""])

        with patch(
            "app.services.mail_processor.aioimaplib.IMAP4_SSL",
            return_value=mock_imap,
        ):
            await processor._fetch_imap_emails(10, set())

        # search("UNSEEN") must be called
        mock_imap.search.assert_awaited_once_with("UNSEEN")
        # uid("search", ...) must NOT be called
        search_uid_calls = [
            c for c in mock_imap.uid.call_args_list if c.args[0] == "search"
        ]
        assert search_uid_calls == []

    async def test_no_messages_returns_empty(self, processor, mock_imap):
        """Empty UNSEEN result should return empty lists without error."""
        mock_imap.search.return_value = _make_imap_response(result="OK", lines=[b""])

        with patch(
            "app.services.mail_processor.aioimaplib.IMAP4_SSL",
            return_value=mock_imap,
        ):
            emails, uids = await processor._fetch_imap_emails(10, set())

        assert emails == []
        assert uids == []

    async def test_fetches_new_message_via_uid_fetch(self, processor, mock_imap):
        """New messages should be fetched with UID FETCH, not plain FETCH."""
        raw_email = b"From: sender@example.com\r\nSubject: Test\r\n\r\nBody"

        mock_imap.search.return_value = _make_imap_response(result="OK", lines=[b"42"])
        mock_imap.fetch.return_value = _make_uid_list_response([("42", "42")])

        def uid_side_effect(command, *args):
            if command == "fetch":
                return _make_fetch_response(args[0], raw_email)
            return _make_imap_response()

        mock_imap.uid = AsyncMock(side_effect=uid_side_effect)

        with patch(
            "app.services.mail_processor.aioimaplib.IMAP4_SSL",
            return_value=mock_imap,
        ):
            emails, new_uids = await processor._fetch_imap_emails(10, set())

        assert emails == [raw_email]
        assert new_uids == ["42"]

        # The fetch call should use UID FETCH
        fetch_call = [c for c in mock_imap.uid.call_args_list if c.args[0] == "fetch"]
        assert len(fetch_call) == 1
        assert fetch_call[0] == call("fetch", "42", "(RFC822)")

    async def test_no_per_message_store_for_seen(self, processor, mock_imap):
        """RFC822 implicitly marks \\Seen; no extra STORE per message is needed."""
        raw_email = b"From: a@b.com\r\n\r\nHello"

        mock_imap.search.return_value = _make_imap_response(
            result="OK", lines=[b"10 11 12"]
        )
        mock_imap.fetch.return_value = _make_uid_list_response(
            [("10", "10"), ("11", "11"), ("12", "12")]
        )

        def uid_side_effect(command, *args):
            if command == "fetch":
                uid_str = args[0]
                return _make_fetch_response(uid_str, raw_email)
            return _make_imap_response()

        mock_imap.uid = AsyncMock(side_effect=uid_side_effect)

        with patch(
            "app.services.mail_processor.aioimaplib.IMAP4_SSL",
            return_value=mock_imap,
        ):
            emails, new_uids = await processor._fetch_imap_emails(10, set())

        # No STORE command should have been called (delete_after_forward=False)
        store_calls = [c for c in mock_imap.uid.call_args_list if c.args[0] == "store"]
        assert store_calls == [], "Expected no STORE commands for \\Seen"

        assert len(emails) == 3
        assert new_uids == ["10", "11", "12"]

    async def test_stale_uids_batched_in_single_store(self, processor, mock_imap):
        """UIDs already in already_seen_uids must be re-marked in one batch STORE."""
        # Two messages: one stale (already in DB), one new
        raw_email = b"From: x@y.com\r\n\r\nNew mail"

        mock_imap.search.return_value = _make_imap_response(result="OK", lines=[b"5 6"])
        mock_imap.fetch.return_value = _make_uid_list_response([("5", "5"), ("6", "6")])

        def uid_side_effect(command, *args):
            if command == "fetch":
                return _make_fetch_response(args[0], raw_email)
            return _make_imap_response()

        mock_imap.uid = AsyncMock(side_effect=uid_side_effect)

        with patch(
            "app.services.mail_processor.aioimaplib.IMAP4_SSL",
            return_value=mock_imap,
        ):
            emails, new_uids = await processor._fetch_imap_emails(
                10, already_seen_uids={"5"}  # UID 5 is stale
            )

        # Only UID 6 is new
        assert new_uids == ["6"]
        assert len(emails) == 1

        store_calls = [c for c in mock_imap.uid.call_args_list if c.args[0] == "store"]
        # Exactly one STORE for the stale UID with RFC 3501 parenthesised syntax
        assert len(store_calls) == 1
        assert store_calls[0] == call("store", "5", "+FLAGS", "(\\Seen)")

    async def test_multiple_stale_uids_batched_together(self, processor, mock_imap):
        """Multiple stale UIDs should be sent as a comma-separated set."""
        mock_imap.search.return_value = _make_imap_response(
            result="OK", lines=[b"1 2 3 4"]
        )
        mock_imap.fetch.return_value = _make_uid_list_response(
            [("1", "1"), ("2", "2"), ("3", "3"), ("4", "4")]
        )

        def uid_side_effect(command, *args):
            if command == "fetch":
                return _make_fetch_response(args[0], b"email data")
            return _make_imap_response()

        mock_imap.uid = AsyncMock(side_effect=uid_side_effect)

        with patch(
            "app.services.mail_processor.aioimaplib.IMAP4_SSL",
            return_value=mock_imap,
        ):
            await processor._fetch_imap_emails(10, already_seen_uids={"1", "2"})

        store_calls = [c for c in mock_imap.uid.call_args_list if c.args[0] == "store"]
        assert len(store_calls) == 1
        # The UID set string should contain both stale UIDs (order may vary)
        uid_set_arg = store_calls[0].args[1]
        parts = set(uid_set_arg.split(","))
        assert parts == {"1", "2"}
        # RFC 3501 parenthesised flag syntax
        assert store_calls[0].args[3] == "(\\Seen)"

    async def test_delete_after_forward_uses_single_batch_store(self):
        """delete_after_forward=True must issue one UID STORE \\Deleted command."""
        from app.services.mail_processor import MailProcessor

        account = _make_account(delete_after_forward=True)
        processor = MailProcessor(account=account, decrypted_password="s")

        mock_imap = MagicMock()
        mock_imap.wait_hello_from_server = AsyncMock()
        mock_imap.login = AsyncMock()
        mock_imap.select = AsyncMock()
        mock_imap.expunge = AsyncMock()
        mock_imap.logout = AsyncMock()
        mock_imap.search = AsyncMock(
            return_value=_make_imap_response(result="OK", lines=[b"7 8"])
        )
        mock_imap.fetch = AsyncMock(
            return_value=_make_uid_list_response([("7", "7"), ("8", "8")])
        )

        def uid_side_effect(command, *args):
            if command == "fetch":
                return _make_fetch_response(args[0], b"raw email")
            return _make_imap_response()

        mock_imap.uid = AsyncMock(side_effect=uid_side_effect)

        with patch(
            "app.services.mail_processor.aioimaplib.IMAP4_SSL",
            return_value=mock_imap,
        ):
            emails, new_uids = await processor._fetch_imap_emails(10, set())

        assert new_uids == ["7", "8"]

        store_calls = [c for c in mock_imap.uid.call_args_list if c.args[0] == "store"]
        # Exactly one STORE for deletion covering both UIDs
        assert len(store_calls) == 1
        uid_set_arg = store_calls[0].args[1]
        parts = set(uid_set_arg.split(","))
        assert parts == {"7", "8"}
        assert store_calls[0].args[2] == "+FLAGS"
        # RFC 3501 parenthesised flag syntax
        assert store_calls[0].args[3] == "(\\Deleted)"
        # expunge must also be called
        mock_imap.expunge.assert_awaited_once()

    async def test_individual_fetch_failure_does_not_abort(self, processor, mock_imap):
        """A single message fetch error should be logged but not stop processing."""
        raw_email = b"From: ok@example.com\r\n\r\nOK"

        mock_imap.search.return_value = _make_imap_response(
            result="OK", lines=[b"20 21"]
        )
        mock_imap.fetch.return_value = _make_uid_list_response(
            [("20", "20"), ("21", "21")]
        )

        call_count = {"count": 0}

        def uid_side_effect(command, *args):
            if command == "fetch":
                call_count["count"] += 1
                if call_count["count"] == 1:
                    raise Exception("Connection dropped by server")
                return _make_fetch_response(args[0], raw_email)
            return _make_imap_response()

        mock_imap.uid = AsyncMock(side_effect=uid_side_effect)

        with patch(
            "app.services.mail_processor.aioimaplib.IMAP4_SSL",
            return_value=mock_imap,
        ):
            emails, new_uids = await processor._fetch_imap_emails(10, set())

        # Second message should still be processed
        assert len(emails) == 1
        assert new_uids == ["21"]

    async def test_logout_called_even_on_connection_error(self, processor, mock_imap):
        """logout() must be attempted even when the connection drops mid-session."""
        mock_imap.search = AsyncMock(side_effect=Exception("BYE server gone"))

        with patch(
            "app.services.mail_processor.aioimaplib.IMAP4_SSL",
            return_value=mock_imap,
        ):
            from app.services.mail_processor import MailFetchError

            with pytest.raises(MailFetchError):
                await processor._fetch_imap_emails(10, set())

        mock_imap.logout.assert_awaited_once()

    async def test_logout_failure_does_not_mask_error(self, processor, mock_imap):
        """If logout itself raises, the original MailFetchError should propagate."""
        mock_imap.search = AsyncMock(side_effect=Exception("server gone"))
        mock_imap.logout = AsyncMock(side_effect=Exception("logout also failed"))

        with patch(
            "app.services.mail_processor.aioimaplib.IMAP4_SSL",
            return_value=mock_imap,
        ):
            from app.services.mail_processor import MailFetchError

            with pytest.raises(MailFetchError):
                await processor._fetch_imap_emails(10, set())

    async def test_respects_max_count_limit(self, processor, mock_imap):
        """Only max_count messages should be processed."""
        raw_email = b"From: a@b.com\r\n\r\nHi"

        mock_imap.search.return_value = _make_imap_response(
            result="OK", lines=[b"1 2 3 4 5"]
        )
        # After max_count=3, only seq 1,2,3 are resolved to UIDs
        mock_imap.fetch.return_value = _make_uid_list_response(
            [("1", "1"), ("2", "2"), ("3", "3")]
        )

        def uid_side_effect(command, *args):
            if command == "fetch":
                return _make_fetch_response(args[0], raw_email)
            return _make_imap_response()

        mock_imap.uid = AsyncMock(side_effect=uid_side_effect)

        with patch(
            "app.services.mail_processor.aioimaplib.IMAP4_SSL",
            return_value=mock_imap,
        ):
            emails, new_uids = await processor._fetch_imap_emails(3, set())

        assert len(emails) == 3
        assert new_uids == ["1", "2", "3"]
        # fetch for UIDs should have been called with the first 3 seq numbers
        mock_imap.fetch.assert_awaited_once_with("1,2,3", "(UID)")

    async def test_plain_imap_uses_imap4_not_ssl(self):
        """Non-SSL IMAP accounts must use IMAP4, not IMAP4_SSL."""
        from app.services.mail_processor import MailProcessor

        account = _make_account(protocol="imap")
        processor = MailProcessor(account=account, decrypted_password="pw")

        mock_imap = MagicMock()
        mock_imap.wait_hello_from_server = AsyncMock()
        mock_imap.login = AsyncMock()
        mock_imap.select = AsyncMock()
        mock_imap.logout = AsyncMock()
        mock_imap.search = AsyncMock(
            return_value=_make_imap_response(result="OK", lines=[b""])
        )
        mock_imap.uid = AsyncMock(
            return_value=_make_imap_response(result="OK", lines=[b""])
        )

        with patch(
            "app.services.mail_processor.aioimaplib.IMAP4",
            return_value=mock_imap,
        ) as mock_cls:
            await processor._fetch_imap_emails(10, set())
            mock_cls.assert_called_once()

    async def test_whitespace_only_rfc822_body_is_skipped(self, processor, mock_imap):
        """A UID FETCH that returns only whitespace bytes must not be added to results.

        T-Online (and potentially other servers) can return RFC822 responses
        whose body is just CR LF or other whitespace.  The extraction loop
        must treat these as absent email data, not as a valid message.
        """
        # Simulate a server that returns b"\r\n" instead of real email bytes
        whitespace_response = _make_imap_response(
            result="OK",
            lines=[b"1 (UID 99 RFC822 {2}", b"\r\n", b")"],
        )

        mock_imap.search.return_value = _make_imap_response(result="OK", lines=[b"99"])
        mock_imap.fetch.return_value = _make_uid_list_response([("99", "99")])

        mock_imap.uid = AsyncMock(
            side_effect=lambda cmd, *args: (
                whitespace_response if cmd == "fetch" else _make_imap_response()
            )
        )

        with patch(
            "app.services.mail_processor.aioimaplib.IMAP4_SSL",
            return_value=mock_imap,
        ):
            emails, new_uids = await processor._fetch_imap_emails(10, set())

        # Whitespace-only response must not produce a message
        assert emails == []
        assert new_uids == []

    async def test_empty_bytes_rfc822_body_is_skipped(self, processor, mock_imap):
        """A UID FETCH that returns b'' as the body must not be added to results."""
        empty_response = _make_imap_response(
            result="OK",
            lines=[b"1 (UID 77 RFC822 {0}", b"", b")"],
        )

        mock_imap.search.return_value = _make_imap_response(result="OK", lines=[b"77"])
        mock_imap.fetch.return_value = _make_uid_list_response([("77", "77")])

        mock_imap.uid = AsyncMock(
            side_effect=lambda cmd, *args: (
                empty_response if cmd == "fetch" else _make_imap_response()
            )
        )

        with patch(
            "app.services.mail_processor.aioimaplib.IMAP4_SSL",
            return_value=mock_imap,
        ):
            emails, new_uids = await processor._fetch_imap_emails(10, set())

        assert emails == []
        assert new_uids == []
