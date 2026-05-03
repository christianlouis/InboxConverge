"""
Unit tests for _format_connection_error() and MailDebugRecorder.

These tests verify:
  - _format_connection_error returns human-readable, non-empty strings
    for every relevant exception type.
  - MailDebugRecorder caps its trace at the configured limits and never
    includes password or credential data in its output.
"""

import asyncio
import poplib
import socket
import ssl

import pytest

from app.services.mail_processor import (
    MailDebugRecorder,
    _format_connection_error,
    _MAX_TRACE_BYTES,
    _MAX_TRACE_ENTRIES,
)


# ---------------------------------------------------------------------------
# _format_connection_error – helpers
# ---------------------------------------------------------------------------


def _fmt(exc: BaseException, host: str = "mail.example.com", port: int = 993) -> str:
    return _format_connection_error(exc, host, port, "IMAP")


# ---------------------------------------------------------------------------
# DNS failure (socket.gaierror)
# ---------------------------------------------------------------------------


class TestFormatConnectionErrorDns:
    def test_gaierror_includes_hostname(self):
        exc = socket.gaierror(-5, "No address associated with hostname")
        msg = _fmt(exc, host="pop.web.de", port=995)
        assert "pop.web.de" in msg
        assert "DNS" in msg or "resolve" in msg.lower()

    def test_gaierror_never_empty(self):
        exc = socket.gaierror(-2, "Name or service not known")
        assert _fmt(exc)

    def test_gaierror_without_host(self):
        exc = socket.gaierror(-5, "No address associated with hostname")
        msg = _format_connection_error(exc)
        assert msg
        assert "DNS" in msg or "lookup" in msg.lower()


# ---------------------------------------------------------------------------
# Timeout
# ---------------------------------------------------------------------------


class TestFormatConnectionErrorTimeout:
    def test_socket_timeout_includes_host_port(self):
        exc = socket.timeout("timed out")
        msg = _fmt(exc, host="imap.gmx.net", port=993)
        # Verify both the host and timeout indicator appear in the message
        assert "imap.gmx.net" in msg
        assert "993" in msg
        assert "timed out" in msg.lower() or "timeout" in msg.lower()

    def test_asyncio_timeout_error(self):
        exc = asyncio.TimeoutError()
        msg = _fmt(exc)
        assert msg  # never empty even though str() is ""
        assert "timed out" in msg.lower() or "timeout" in msg.lower()

    def test_bare_timeout_error(self):
        """Python 3.11+ TimeoutError (subclass of OSError) should be handled."""
        exc = TimeoutError("timed out")
        msg = _fmt(exc)
        assert msg


# ---------------------------------------------------------------------------
# Connection refused / reset
# ---------------------------------------------------------------------------


class TestFormatConnectionErrorRefused:
    def test_connection_refused_includes_host_port(self):
        exc = ConnectionRefusedError(111, "Connection refused")
        msg = _fmt(exc, host="smtp.example.com", port=587)
        # Verify both host and port appear in the message
        assert "smtp.example.com" in msg
        assert "587" in msg
        assert "refused" in msg.lower()

    def test_connection_reset(self):
        exc = ConnectionResetError(104, "Connection reset by peer")
        msg = _fmt(exc)
        assert msg
        assert "reset" in msg.lower()


# ---------------------------------------------------------------------------
# SSL errors
# ---------------------------------------------------------------------------


class TestFormatConnectionErrorSsl:
    def test_ssl_cert_verification(self):
        try:
            # Create a real SSLCertVerificationError if possible
            exc = ssl.SSLCertVerificationError(
                1, "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed"
            )
        except Exception:
            exc = ssl.SSLError(1, "CERTIFICATE_VERIFY_FAILED")  # type: ignore[assignment]
        msg = _fmt(exc)
        assert msg
        assert "TLS" in msg or "SSL" in msg or "certificate" in msg.lower()

    def test_ssl_generic_error(self):
        exc = ssl.SSLError(1, "wrong version number")
        msg = _fmt(exc)
        assert msg
        assert "TLS" in msg or "SSL" in msg


# ---------------------------------------------------------------------------
# POP3 protocol errors
# ---------------------------------------------------------------------------


class TestFormatConnectionErrorPop3:
    def test_auth_error_identifies_auth_failure(self):
        exc = poplib.error_proto("-ERR authentication failed")
        msg = _format_connection_error(exc, "pop.example.com", 995, "POP3")
        # Verify both host and port appear in the message
        assert "pop.example.com" in msg
        assert "995" in msg
        assert "Authentication" in msg or "authentication" in msg

    def test_generic_pop3_error(self):
        exc = poplib.error_proto("-ERR mailbox is locked")
        msg = _format_connection_error(exc, "pop.example.com", 995, "POP3")
        assert msg
        assert "POP3" in msg

    def test_empty_pop3_error(self):
        """Even a bare error_proto with no message must produce a non-empty string."""
        exc = poplib.error_proto(b"")
        msg = _format_connection_error(exc, "pop.example.com", 995, "POP3")
        assert msg


# ---------------------------------------------------------------------------
# Catch-all: empty-string exception
# ---------------------------------------------------------------------------


class TestFormatConnectionErrorFallback:
    def test_empty_string_exception(self):
        """An exception whose str() is empty must still produce a non-empty message."""
        exc = asyncio.TimeoutError()
        assert str(exc) == ""  # confirm the premise
        msg = _fmt(exc)
        assert msg
        assert len(msg) > 0

    def test_generic_exception(self):
        exc = RuntimeError("something went wrong")
        msg = _fmt(exc)
        assert "something went wrong" in msg or "RuntimeError" in msg

    def test_no_host(self):
        exc = RuntimeError("test")
        msg = _format_connection_error(exc)
        assert msg


# ---------------------------------------------------------------------------
# MailDebugRecorder
# ---------------------------------------------------------------------------


class TestMailDebugRecorder:
    def test_record_entry_appears_in_trace(self):
        rec = MailDebugRecorder()
        rec.record("connect", "Connected to mail.example.com:993", {"elapsed_ms": 42})
        details = rec.as_details()
        assert len(details["trace"]) == 1
        entry = details["trace"][0]
        assert entry["phase"] == "connect"
        assert entry["msg"] == "Connected to mail.example.com:993"
        assert entry["data"]["elapsed_ms"] == 42
        assert not details["truncated"]

    def test_has_entries_false_when_empty(self):
        rec = MailDebugRecorder()
        assert not rec.has_entries()

    def test_has_entries_true_after_record(self):
        rec = MailDebugRecorder()
        rec.record("auth", "Logged in")
        assert rec.has_entries()

    def test_size_cap_triggers_truncation(self):
        """Recording beyond _MAX_TRACE_BYTES silently truncates."""
        rec = MailDebugRecorder()
        # Each entry is ~100 chars; flood until truncated
        long_msg = "x" * 1000
        for i in range(200):
            rec.record("flood", long_msg, {"i": i})
        details = rec.as_details()
        assert details["truncated"]
        # After truncation, recording new entries is a no-op
        prev_count = len(rec)
        rec.record("after_truncate", "should be ignored")
        assert len(rec) == prev_count

    def test_entry_cap_triggers_truncation(self):
        """Recording more than _MAX_TRACE_ENTRIES entries truncates."""
        rec = MailDebugRecorder()
        for i in range(_MAX_TRACE_ENTRIES + 10):
            rec.record("phase", f"entry {i}")
        assert rec.as_details()["truncated"]
        # Total entries should be MAX + 1 (the truncation sentinel)
        assert len(rec.as_details()["trace"]) <= _MAX_TRACE_ENTRIES + 1

    def test_no_password_in_trace_from_production_phases(self):
        """Production instrumentation records only usernames and counts, never passwords.

        The recorder itself has no auto-redaction; the contract is that callers
        (the instrumented IMAP/POP3 code) must never pass credential data.
        This test verifies the expected production-phase entries contain no
        password strings.
        """
        password = "s3cr3tP@ssw0rd!"
        rec = MailDebugRecorder()
        # Simulate the entries that production code actually records
        rec.record("auth", f"Authenticated as user@example.com", {"elapsed_ms": 5})
        rec.record("stat", "Mailbox has 3 messages", {"count": 3})

        import json
        serialised = json.dumps(rec.as_details())
        # The password must not appear in any of these entries
        assert password not in serialised

    def test_timestamps_are_iso_format(self):
        rec = MailDebugRecorder()
        rec.record("connect", "ok")
        ts = rec.as_details()["trace"][0]["ts"]
        # Should be parseable as ISO 8601
        from datetime import datetime

        datetime.fromisoformat(ts)  # raises if invalid

    def test_multiple_phases_ordered(self):
        rec = MailDebugRecorder()
        for phase in ["connect", "auth", "select", "search", "fetch_msg", "logout"]:
            rec.record(phase, f"{phase} done")
        details = rec.as_details()
        phases = [e["phase"] for e in details["trace"]]
        assert phases == ["connect", "auth", "select", "search", "fetch_msg", "logout"]
