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

from app.services.mail_processor import MailProcessor, MailFetchError

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
        assert fetch_call[0] == call("fetch", "42", "(BODY.PEEK[])")

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

    async def test_fetch_does_not_delete_after_forward(self):
        """_fetch_imap_emails must NOT issue \\Deleted STORE even when delete_after_forward=True.

        Deletion is deferred to post_process_imap() so that only successfully
        forwarded messages are removed from the source mailbox.
        """
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

        # No STORE for \\Deleted should be issued during fetch
        delete_store_calls = [
            c
            for c in mock_imap.uid.call_args_list
            if c.args[0] == "store" and "(\\Deleted)" in c.args
        ]
        assert delete_store_calls == [], "fetch must not delete messages"
        # expunge must NOT be called during fetch either
        mock_imap.expunge.assert_not_awaited()

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

    async def test_bytearray_literal_data_is_accepted(self, processor, mock_imap):
        """aioimaplib stores IMAP literal data as bytearray, not bytes.

        This is the root cause of emails appearing empty on IMAP servers such
        as T-Online and GMX: the extraction loop previously skipped bytearray
        objects because ``isinstance(bytearray(...), bytes)`` is False.

        The fix accepts both bytes and bytearray and converts to bytes so the
        rest of the pipeline receives plain bytes as expected.
        """
        raw_email = b"From: user@t-online.de\r\nSubject: Real email\r\n\r\nBody"
        # aioimaplib returns the RFC822 literal as bytearray in response.lines
        bytearray_response = _make_imap_response(
            result="OK",
            lines=[
                b"1 (UID 55 RFC822 {%d}" % len(raw_email),
                bytearray(raw_email),
                b")",
            ],
        )

        mock_imap.search.return_value = _make_imap_response(result="OK", lines=[b"55"])
        mock_imap.fetch.return_value = _make_uid_list_response([("55", "55")])

        mock_imap.uid = AsyncMock(
            side_effect=lambda cmd, *args: (
                bytearray_response if cmd == "fetch" else _make_imap_response()
            )
        )

        with patch(
            "app.services.mail_processor.aioimaplib.IMAP4_SSL",
            return_value=mock_imap,
        ):
            emails, new_uids = await processor._fetch_imap_emails(10, set())

        # The email must be extracted and returned as plain bytes
        assert new_uids == ["55"]
        assert len(emails) == 1
        assert emails[0] == raw_email
        assert isinstance(emails[0], bytes)

    async def test_bytearray_whitespace_literal_is_skipped(self, processor, mock_imap):
        """A bytearray literal that is whitespace-only must still be rejected."""
        bytearray_ws_response = _make_imap_response(
            result="OK",
            lines=[b"1 (UID 56 RFC822 {2}", bytearray(b"\r\n"), b")"],
        )

        mock_imap.search.return_value = _make_imap_response(result="OK", lines=[b"56"])
        mock_imap.fetch.return_value = _make_uid_list_response([("56", "56")])

        mock_imap.uid = AsyncMock(
            side_effect=lambda cmd, *args: (
                bytearray_ws_response if cmd == "fetch" else _make_imap_response()
            )
        )

        with patch(
            "app.services.mail_processor.aioimaplib.IMAP4_SSL",
            return_value=mock_imap,
        ):
            emails, new_uids = await processor._fetch_imap_emails(10, set())

        assert emails == []
        assert new_uids == []


# ---------------------------------------------------------------------------
# Additional edge-case tests for remaining branch coverage
# ---------------------------------------------------------------------------


class TestFetchImapEdgeCases:
    """Tests for edge cases in _fetch_imap_emails not covered above."""

    async def test_search_ok_but_empty_split_returns_empty(self):
        """If SEARCH UNSEEN returns OK but lines[0].split() is empty, return []."""
        account = _make_account()
        processor = MailProcessor(account, "secret")

        mock_imap = AsyncMock()
        mock_imap.wait_hello_from_server = AsyncMock()
        mock_imap.login = AsyncMock(return_value=_make_imap_response("OK"))
        mock_imap.select = AsyncMock(return_value=_make_imap_response("OK"))
        # lines[0] is a non-empty string with only spaces => split() returns []
        mock_imap.search = AsyncMock(
            return_value=_make_imap_response("OK", lines=[b"   "])
        )
        mock_imap.logout = AsyncMock()

        with patch(
            "app.services.mail_processor.aioimaplib.IMAP4_SSL",
            return_value=mock_imap,
        ):
            emails, new_uids = await processor._fetch_imap_emails(10, set())

        assert emails == []
        assert new_uids == []

    async def test_stale_uid_store_failure_is_non_fatal(self):
        """If the UID STORE to re-mark stale UIDs fails, processing continues."""
        account = _make_account()
        processor = MailProcessor(account, "secret")

        mock_imap = AsyncMock()
        mock_imap.wait_hello_from_server = AsyncMock()
        mock_imap.login = AsyncMock(return_value=_make_imap_response("OK"))
        mock_imap.select = AsyncMock(return_value=_make_imap_response("OK"))
        mock_imap.search = AsyncMock(
            return_value=_make_imap_response("OK", lines=[b"1"])
        )
        mock_imap.fetch = AsyncMock(
            return_value=_make_uid_list_response([("1", "100")])
        )

        async def uid_side_effect(cmd, *args):
            if cmd == "store":
                raise Exception("store failed")
            return _make_imap_response("OK")

        mock_imap.uid = AsyncMock(side_effect=uid_side_effect)
        mock_imap.logout = AsyncMock()

        with patch(
            "app.services.mail_processor.aioimaplib.IMAP4_SSL",
            return_value=mock_imap,
        ):
            emails, new_uids = await processor._fetch_imap_emails(10, {"100"})

        assert emails == []
        assert new_uids == []

    async def test_delete_failure_is_non_fatal(self):
        """If batch UID STORE \\Deleted fails, emails are still returned."""
        email_bytes = b"From: a@b.com\r\nSubject: hi\r\n\r\nbody"
        account = _make_account(delete_after_forward=True)
        processor = MailProcessor(account, "secret")

        mock_imap = AsyncMock()
        mock_imap.wait_hello_from_server = AsyncMock()
        mock_imap.login = AsyncMock(return_value=_make_imap_response("OK"))
        mock_imap.select = AsyncMock(return_value=_make_imap_response("OK"))
        mock_imap.search = AsyncMock(
            return_value=_make_imap_response("OK", lines=[b"1"])
        )
        mock_imap.fetch = AsyncMock(return_value=_make_uid_list_response([("1", "42")]))

        async def uid_side_effect(cmd, *args):
            if cmd == "fetch":
                return _make_fetch_response("42", email_bytes)
            if cmd == "store":
                raise Exception("delete failed")
            return _make_imap_response("OK")

        mock_imap.uid = AsyncMock(side_effect=uid_side_effect)
        mock_imap.logout = AsyncMock()

        with patch(
            "app.services.mail_processor.aioimaplib.IMAP4_SSL",
            return_value=mock_imap,
        ):
            emails, new_uids = await processor._fetch_imap_emails(10, set())

        assert len(emails) == 1
        assert new_uids == ["42"]

    async def test_mail_fetch_error_is_re_raised_directly(self):
        """A MailFetchError raised inside the try block is re-raised, not wrapped."""
        account = _make_account()
        processor = MailProcessor(account, "secret")

        mock_imap = AsyncMock()
        mock_imap.wait_hello_from_server = AsyncMock()
        mock_imap.login = AsyncMock(side_effect=MailFetchError("inner error"))
        mock_imap.logout = AsyncMock()

        with patch(
            "app.services.mail_processor.aioimaplib.IMAP4_SSL",
            return_value=mock_imap,
        ):
            with pytest.raises(MailFetchError, match="inner error"):
                await processor._fetch_imap_emails(10, set())

    async def test_response_lines_with_star_prefix_are_skipped(self):
        """Response lines starting with b'*' are filtered out."""
        email_bytes = b"From: a@b.com\r\nSubject: test\r\n\r\nbody"
        account = _make_account()
        processor = MailProcessor(account, "secret")

        mock_imap = AsyncMock()
        mock_imap.wait_hello_from_server = AsyncMock()
        mock_imap.login = AsyncMock(return_value=_make_imap_response("OK"))
        mock_imap.select = AsyncMock(return_value=_make_imap_response("OK"))
        mock_imap.search = AsyncMock(
            return_value=_make_imap_response("OK", lines=[b"1"])
        )
        mock_imap.fetch = AsyncMock(return_value=_make_uid_list_response([("1", "99")]))

        fetch_resp = _make_imap_response(
            "OK",
            lines=[
                b"1 (UID 99 RFC822 {100}",  # header containing RFC822
                "some string line",  # non-bytes/bytearray => skipped
                b"* extra info",  # starts with * => skipped
                email_bytes,  # actual data
                b")",  # closing paren => skipped
            ],
        )

        async def uid_side_effect(cmd, *args):
            if cmd == "fetch":
                return fetch_resp
            return _make_imap_response("OK")

        mock_imap.uid = AsyncMock(side_effect=uid_side_effect)
        mock_imap.logout = AsyncMock()

        with patch(
            "app.services.mail_processor.aioimaplib.IMAP4_SSL",
            return_value=mock_imap,
        ):
            emails, new_uids = await processor._fetch_imap_emails(10, set())

        assert len(emails) == 1
        assert emails[0] == email_bytes
        assert new_uids == ["99"]


# ---------------------------------------------------------------------------
# post_process_imap tests
# ---------------------------------------------------------------------------


class TestPostProcessImap:
    """Tests for the post_process_imap() method."""

    def _make_processor(self, delete_after_forward=False, protocol="imap_ssl"):
        from app.services.mail_processor import MailProcessor

        account = _make_account(
            delete_after_forward=delete_after_forward, protocol=protocol
        )
        return MailProcessor(account=account, decrypted_password="secret")

    def _mock_imap_client(self):
        client = MagicMock()
        client.wait_hello_from_server = AsyncMock()
        client.login = AsyncMock()
        client.select = AsyncMock()
        client.uid = AsyncMock(return_value=_make_imap_response())
        client.expunge = AsyncMock()
        client.logout = AsyncMock()
        return client

    async def test_marks_seen_without_delete(self):
        """post_process_imap marks UIDs \\Seen when delete_after_forward=False."""
        processor = self._make_processor(delete_after_forward=False)
        mock_imap = self._mock_imap_client()

        with patch(
            "app.services.mail_processor.aioimaplib.IMAP4_SSL",
            return_value=mock_imap,
        ):
            await processor.post_process_imap(["10", "11"])

        store_calls = [c for c in mock_imap.uid.call_args_list if c.args[0] == "store"]
        assert len(store_calls) == 1
        assert set(store_calls[0].args[1].split(",")) == {"10", "11"}
        assert store_calls[0].args[3] == "(\\Seen)"
        mock_imap.expunge.assert_not_awaited()

    async def test_marks_seen_and_deleted_with_delete(self):
        """post_process_imap marks \\Seen + \\Deleted and expunges when configured."""
        processor = self._make_processor(delete_after_forward=True)
        mock_imap = self._mock_imap_client()

        with patch(
            "app.services.mail_processor.aioimaplib.IMAP4_SSL",
            return_value=mock_imap,
        ):
            await processor.post_process_imap(["5", "6"])

        store_calls = [c for c in mock_imap.uid.call_args_list if c.args[0] == "store"]
        assert len(store_calls) == 2
        flags_used = {c.args[3] for c in store_calls}
        assert "(\\Seen)" in flags_used
        assert "(\\Deleted)" in flags_used
        mock_imap.expunge.assert_awaited_once()

    async def test_noop_on_empty_uid_list(self):
        """post_process_imap does nothing when the UID list is empty."""
        processor = self._make_processor()
        mock_imap = self._mock_imap_client()

        with patch(
            "app.services.mail_processor.aioimaplib.IMAP4_SSL",
            return_value=mock_imap,
        ):
            await processor.post_process_imap([])

        mock_imap.login.assert_not_awaited()

    async def test_exception_is_swallowed_and_logged(self):
        """post_process_imap catches exceptions and does not propagate them."""
        processor = self._make_processor()
        mock_imap = self._mock_imap_client()
        mock_imap.login = AsyncMock(side_effect=OSError("connection refused"))

        with patch(
            "app.services.mail_processor.aioimaplib.IMAP4_SSL",
            return_value=mock_imap,
        ):
            await processor.post_process_imap(["1"])  # must not raise

        mock_imap.logout.assert_awaited_once()

    async def test_uses_imap4_for_non_ssl(self):
        """Plain IMAP accounts must use IMAP4, not IMAP4_SSL."""
        from app.services.mail_processor import MailProcessor

        account = _make_account(protocol="imap")
        processor = MailProcessor(account=account, decrypted_password="pw")
        mock_imap = MagicMock()
        mock_imap.wait_hello_from_server = AsyncMock()
        mock_imap.login = AsyncMock()
        mock_imap.select = AsyncMock()
        mock_imap.uid = AsyncMock(return_value=_make_imap_response())
        mock_imap.logout = AsyncMock()

        with patch(
            "app.services.mail_processor.aioimaplib.IMAP4",
            return_value=mock_imap,
        ) as mock_cls, patch(
            "app.services.mail_processor.aioimaplib.IMAP4_SSL"
        ) as mock_ssl_cls:
            await processor.post_process_imap(["1"])
            mock_cls.assert_called_once()
            mock_ssl_cls.assert_not_called()

    async def test_logout_called_even_on_error(self):
        """logout() is called in the finally block even when an exception occurs."""
        processor = self._make_processor()
        mock_imap = self._mock_imap_client()
        mock_imap.uid = AsyncMock(side_effect=Exception("store failed"))

        with patch(
            "app.services.mail_processor.aioimaplib.IMAP4_SSL",
            return_value=mock_imap,
        ):
            await processor.post_process_imap(["99"])

        mock_imap.logout.assert_awaited_once()


# ---------------------------------------------------------------------------
# post_process_messages routing test
# ---------------------------------------------------------------------------


class TestPostProcessMessages:
    """post_process_messages() routes to the correct protocol handler."""

    async def test_routes_to_imap_for_imap_ssl(self):
        from app.services.mail_processor import MailProcessor

        account = _make_account(protocol="imap_ssl")
        processor = MailProcessor(account=account, decrypted_password="pw")
        with patch.object(
            processor, "post_process_imap", new_callable=AsyncMock
        ) as mock_imap, patch.object(
            processor, "post_process_pop3", new_callable=AsyncMock
        ) as mock_pop3:
            await processor.post_process_messages(["1", "2"])
            mock_imap.assert_awaited_once_with(["1", "2"])
            mock_pop3.assert_not_awaited()

    async def test_routes_to_pop3_for_pop3_ssl(self):
        from app.services.mail_processor import MailProcessor, MailProcessor

        account = _make_account(protocol="imap_ssl")
        account.protocol = __import__(
            "app.models.database_models", fromlist=["MailProtocol"]
        ).MailProtocol.POP3_SSL
        processor = MailProcessor(account=account, decrypted_password="pw")
        with patch.object(
            processor, "post_process_pop3", new_callable=AsyncMock
        ) as mock_pop3, patch.object(
            processor, "post_process_imap", new_callable=AsyncMock
        ) as mock_imap:
            await processor.post_process_messages(["a"])
            mock_pop3.assert_awaited_once_with(["a"])
            mock_imap.assert_not_awaited()

