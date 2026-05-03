"""
Unit tests for the DNS 8.8.8.8 fallback resolver in mail_processor.py.

Covers:
  - _build_dns_query() produces a valid DNS A-record packet
  - _parse_dns_a_response() extracts the first A record correctly
  - _query_google_dns_sync() sends UDP query to 8.8.8.8 and returns an IPv4
  - _resolve_ipv4_sync() falls through to 8.8.8.8 when system DNS and cache fail
  - _resolve_ipv4_sync() caches the 8.8.8.8 result for subsequent calls
"""

import socket
import struct
from unittest.mock import MagicMock, patch


from app.services.mail_processor import (
    _build_dns_query,
    _parse_dns_a_response,
    _query_google_dns_sync,
    _resolve_ipv4_sync,
    _dns_cache,
    _dns_cache_lock,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_dns_response(txid: int, ip: str) -> bytes:
    """Craft a minimal valid DNS A-record response for the given IP."""
    flags = 0x8180  # response, recursion available
    qdcount = 1
    ancount = 1
    header = struct.pack(">HHHHHH", txid, flags, qdcount, ancount, 0, 0)
    # Question: dummy single-label name "x" + QTYPE=A + QCLASS=IN
    qname = b"\x01x\x00"
    question = qname + struct.pack(">HH", 1, 1)
    # Answer: pointer to question name (0xC00C), TYPE=A, CLASS=IN, TTL, RDLEN=4, IP
    octets = tuple(int(o) for o in ip.split("."))
    answer = struct.pack(">HHHiH", 0xC00C, 1, 1, 300, 4) + bytes(octets)
    return header + question + answer


# ---------------------------------------------------------------------------
# _build_dns_query
# ---------------------------------------------------------------------------


class TestBuildDnsQuery:
    def test_contains_hostname_labels(self):
        data = _build_dns_query("pop.example.com")
        # "pop" label should appear: length byte 3 followed by b"pop"
        assert b"\x03pop" in data

    def test_qtype_a_and_class_in(self):
        data = _build_dns_query("mail.example.com")
        # Last 4 bytes of question: QTYPE=0x0001, QCLASS=0x0001
        assert data[-4:] == b"\x00\x01\x00\x01"

    def test_transaction_id_is_0xAB12(self):
        data = _build_dns_query("x.example.com")
        txid = struct.unpack(">H", data[:2])[0]
        assert txid == 0xAB12


# ---------------------------------------------------------------------------
# _parse_dns_a_response
# ---------------------------------------------------------------------------


class TestParseDnsAResponse:
    def test_extracts_ip_from_valid_response(self):
        response = _make_dns_response(0xAB12, "1.2.3.4")
        result = _parse_dns_a_response(response, "example.com")
        assert result == "1.2.3.4"

    def test_returns_none_for_wrong_txid(self):
        response = _make_dns_response(0x1234, "1.2.3.4")
        result = _parse_dns_a_response(response, "example.com")
        assert result is None

    def test_returns_none_for_short_data(self):
        assert _parse_dns_a_response(b"\x00\x01", "example.com") is None

    def test_returns_none_when_no_answers(self):
        # Build a header with ancount=0
        header = struct.pack(">HHHHHH", 0xAB12, 0x8180, 0, 0, 0, 0)
        assert _parse_dns_a_response(header, "x") is None


# ---------------------------------------------------------------------------
# _query_google_dns_sync
# ---------------------------------------------------------------------------


class TestQueryGoogleDnsSync:
    def test_returns_ip_on_success(self):
        response = _make_dns_response(0xAB12, "5.6.7.8")

        mock_sock = MagicMock()
        mock_sock.recvfrom.return_value = (response, ("8.8.8.8", 53))

        with patch("socket.socket", return_value=mock_sock):
            result = _query_google_dns_sync("pop.example.com")

        assert result == "5.6.7.8"
        mock_sock.sendto.assert_called_once()

    def test_returns_none_on_socket_error(self):
        with patch("socket.socket", side_effect=OSError("network down")):
            result = _query_google_dns_sync("pop.example.com")
        assert result is None

    def test_returns_none_on_timeout(self):
        mock_sock = MagicMock()
        mock_sock.recvfrom.side_effect = socket.timeout("timed out")
        with patch("socket.socket", return_value=mock_sock):
            result = _query_google_dns_sync("pop.example.com")
        assert result is None


# ---------------------------------------------------------------------------
# _resolve_ipv4_sync  — 8.8.8.8 fallback path
# ---------------------------------------------------------------------------


class TestResolveIpv4SyncGoogleFallback:
    def setup_method(self):
        """Clear the DNS cache before each test to avoid state bleed."""
        with _dns_cache_lock:
            _dns_cache.clear()

    def test_falls_through_to_google_when_system_dns_and_cache_fail(self):
        with (
            patch(
                "socket.getaddrinfo",
                side_effect=OSError("Name or service not known"),
            ),
            patch(
                "app.services.mail_processor._query_google_dns_sync",
                return_value="9.10.11.12",
            ) as mock_google,
            patch(
                "app.services.mail_processor.settings.DNS_CACHE_FALLBACK_ENABLED",
                False,
            ),
        ):
            result = _resolve_ipv4_sync("pop.web.de", 995)

        assert result == "9.10.11.12"
        mock_google.assert_called_once_with("pop.web.de")

    def test_google_result_is_cached(self):
        with (
            patch(
                "socket.getaddrinfo",
                side_effect=OSError("Name or service not known"),
            ),
            patch(
                "app.services.mail_processor._query_google_dns_sync",
                return_value="9.10.11.12",
            ),
            patch(
                "app.services.mail_processor.settings.DNS_CACHE_FALLBACK_ENABLED",
                True,
            ),
        ):
            _resolve_ipv4_sync("pop.web.de", 995)

        with _dns_cache_lock:
            cached = _dns_cache.get(("pop.web.de", 995))
        assert cached == "9.10.11.12"

    def test_returns_none_when_all_strategies_fail(self):
        with (
            patch(
                "socket.getaddrinfo",
                side_effect=OSError("Name or service not known"),
            ),
            patch(
                "app.services.mail_processor._query_google_dns_sync",
                return_value=None,
            ),
            patch(
                "app.services.mail_processor.settings.DNS_CACHE_FALLBACK_ENABLED",
                False,
            ),
        ):
            result = _resolve_ipv4_sync("nonexistent.invalid", 995)

        assert result is None

    def test_system_dns_success_skips_google(self):
        with (
            patch(
                "socket.getaddrinfo",
                return_value=[(None, None, None, None, ("1.2.3.4", 995))],
            ),
            patch(
                "app.services.mail_processor._query_google_dns_sync",
            ) as mock_google,
            patch(
                "app.services.mail_processor.settings.DNS_CACHE_FALLBACK_ENABLED",
                False,
            ),
        ):
            result = _resolve_ipv4_sync("pop.example.com", 995)

        assert result == "1.2.3.4"
        mock_google.assert_not_called()
