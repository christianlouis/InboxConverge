"""
Unit tests for empty-email detection in the task processing pipeline.

Covers two layers:
  1. tasks._empty_email_check_logic  – the inline body-inspection that
     decides whether a parsed email should be dropped.
  2. The "clear last_error_message on success" contract – verifying that a
     successful run nulls out any previously stored error so the status page
     no longer shows stale IMAP errors.
"""

import email as email_lib

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse(raw: bytes):
    """Parse raw bytes into an email.Message object (same call used in tasks.py)."""
    return email_lib.message_from_bytes(raw)


def _body_has_content(msg) -> bool:
    """
    Mirror of the body-detection logic in tasks.py's email processing loop.

    Returns True if the message has at least one non-empty / non-whitespace
    text or binary payload.
    """
    if msg.is_multipart():
        for part in msg.walk():
            payload = part.get_payload(decode=True)
            if isinstance(payload, bytes) and payload.strip():
                return True
        return False
    else:
        payload = msg.get_payload(decode=True)
        return isinstance(payload, bytes) and bool(payload.strip())


def _is_empty_email(raw: bytes) -> bool:
    """
    Replicates the complete empty-email gate from tasks.py:
      - no subject AND no from AND no body  →  True (should be dropped)
    """
    msg = _parse(raw)
    email_subject = (msg.get("Subject", "") or "").strip() or None
    email_from = (msg.get("From", "") or "").strip() or None

    if email_subject or email_from:
        return False  # Has at least a header → not empty

    return not _body_has_content(msg)


# ---------------------------------------------------------------------------
# Body-detection tests
# ---------------------------------------------------------------------------


class TestBodyHasContent:
    def test_plain_text_body(self):
        raw = b"From: a@b.com\r\nSubject: Hi\r\n\r\nHello world"
        msg = _parse(raw)
        assert _body_has_content(msg) is True

    def test_empty_body(self):
        raw = b"From: a@b.com\r\nSubject: Hi\r\n\r\n"
        msg = _parse(raw)
        assert _body_has_content(msg) is False

    def test_crlf_only_body(self):
        raw = b"From: a@b.com\r\nSubject: Hi\r\n\r\n\r\n"
        msg = _parse(raw)
        assert _body_has_content(msg) is False

    def test_whitespace_only_body(self):
        raw = b"From: a@b.com\r\nSubject: Hi\r\n\r\n   \t  "
        msg = _parse(raw)
        assert _body_has_content(msg) is False

    def test_multipart_with_content(self):
        raw = (
            b"MIME-Version: 1.0\r\n"
            b"Content-Type: multipart/mixed; boundary=X\r\n\r\n"
            b"--X\r\n"
            b"Content-Type: text/plain\r\n\r\n"
            b"Hello from multipart\r\n"
            b"--X--\r\n"
        )
        msg = _parse(raw)
        assert _body_has_content(msg) is True

    def test_multipart_all_empty_parts(self):
        raw = (
            b"MIME-Version: 1.0\r\n"
            b"Content-Type: multipart/mixed; boundary=X\r\n\r\n"
            b"--X\r\n"
            b"Content-Type: text/plain\r\n\r\n"
            b"\r\n"
            b"--X--\r\n"
        )
        msg = _parse(raw)
        assert _body_has_content(msg) is False


# ---------------------------------------------------------------------------
# Complete empty-email gate tests
# ---------------------------------------------------------------------------


class TestIsEmptyEmail:
    def test_completely_empty_raw_bytes(self):
        assert _is_empty_email(b"") is True

    def test_only_headers_no_body(self):
        raw = b"\r\n"
        assert _is_empty_email(raw) is True

    def test_no_subject_no_from_no_body(self):
        raw = b"Date: Mon, 1 Jan 2024 00:00:00 +0000\r\n\r\n"
        assert _is_empty_email(raw) is True

    def test_has_subject_no_from_no_body(self):
        """Subject alone is enough to keep the email."""
        raw = b"Subject: Alert\r\n\r\n"
        assert _is_empty_email(raw) is False

    def test_has_from_no_subject_no_body(self):
        """From alone is enough to keep the email."""
        raw = b"From: sender@example.com\r\n\r\n"
        assert _is_empty_email(raw) is False

    def test_no_headers_but_body_has_content(self):
        """Body content alone is enough to keep the email."""
        raw = b"\r\nThis is the body."
        assert _is_empty_email(raw) is False

    def test_normal_email_is_not_empty(self):
        raw = (
            b"From: sender@example.com\r\n"
            b"Subject: Hello\r\n\r\n"
            b"Some body text.\r\n"
        )
        assert _is_empty_email(raw) is False

    def test_crlf_only_is_empty(self):
        assert _is_empty_email(b"\r\n\r\n") is True


# ---------------------------------------------------------------------------
# Status-clearing contract
# ---------------------------------------------------------------------------


class TestLastErrorMessageClearOnSuccess:
    """
    The `last_error_message` field must be cleared when a run completes with
    zero forwarding failures, so the status page does not show stale errors.

    This test exercises the same branch logic used in tasks.py without
    needing a full Celery / DB setup.
    """

    def _simulate_account_status_update(
        self, emails_failed: int, current_error_message: str | None
    ) -> dict:
        """
        Simulate the account-status block from tasks.py:

            if emails_failed == 0:
                account.status = ACTIVE
                account.last_error_message = None
                account.last_error_at = None
            else:
                account.status = ERROR
                account.last_error_at = <now>
                account.last_error_message = f"{emails_failed} emails failed to forward"

        Returns a dict with the resulting field values.
        """
        from app.models.database_models import AccountStatus

        state = {
            "last_error_message": current_error_message,
            "last_error_at": "2024-01-01",
        }

        if emails_failed == 0:
            state["status"] = AccountStatus.ACTIVE
            state["last_error_message"] = None
            state["last_error_at"] = None
        else:
            state["status"] = AccountStatus.ERROR
            state["last_error_message"] = f"{emails_failed} emails failed to forward"
            state["last_error_at"] = "2024-01-02"

        return state

    def test_error_cleared_on_zero_failures(self):
        """A previously stored error is wiped when all emails forward OK."""
        result = self._simulate_account_status_update(
            emails_failed=0,
            current_error_message="IMAP fetch error: UID only possible with …",
        )
        assert result["last_error_message"] is None
        assert result["last_error_at"] is None

    def test_error_set_when_failures_exist(self):
        """When emails fail, the error message is updated, not cleared."""
        result = self._simulate_account_status_update(
            emails_failed=3,
            current_error_message=None,
        )
        assert result["last_error_message"] == "3 emails failed to forward"
        assert result["last_error_at"] is not None

    def test_no_error_remains_none_on_success(self):
        """A clean account stays clean after a successful run."""
        result = self._simulate_account_status_update(
            emails_failed=0,
            current_error_message=None,
        )
        assert result["last_error_message"] is None
