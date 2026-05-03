"""
Mail processing service for fetching and forwarding emails.
Supports both POP3 and IMAP protocols with secure connections.
"""

import asyncio
import poplib
import re
import smtplib
import socket
import ssl
import struct
import threading
import time as _time
from datetime import datetime, timezone
from email import parser
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate, make_msgid
from typing import List, Dict, Any, Optional, Set, Tuple
import logging
from aioimaplib import aioimaplib

from app.core.config import settings
from app.models.database_models import MailAccount, MailProtocol

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# DNS resolution cache
# ---------------------------------------------------------------------------
# Maps (host, port) -> last-known IPv4 address.  Protected by a threading.Lock
# so it is safe to read/write from both async code and thread-pool executors.
_dns_cache: Dict[Tuple[str, int], str] = {}
_dns_cache_lock = threading.Lock()


def _get_cached_ipv4(host: str, port: int) -> Optional[str]:
    with _dns_cache_lock:
        return _dns_cache.get((host, port))


def _set_cached_ipv4(host: str, port: int, ipv4: str) -> None:
    with _dns_cache_lock:
        _dns_cache[(host, port)] = ipv4


# ---------------------------------------------------------------------------
# DNS fallback via Google 8.8.8.8
# ---------------------------------------------------------------------------
# When both the system resolver and the local cache fail we send a raw DNS
# A-record query directly to 8.8.8.8:53.  This requires no extra dependencies
# and keeps mail flowing even when /etc/resolv.conf points at a temporarily
# unreachable resolver.

_GOOGLE_DNS = "8.8.8.8"
_DNS_PORT = 53
_DNS_TIMEOUT = 3.0  # seconds


def _build_dns_query(hostname: str) -> bytes:
    """Build a minimal DNS A-record query packet for *hostname*."""
    txid = 0xAB12  # arbitrary fixed transaction ID – we parse by TID match
    flags = 0x0100  # standard query, recursion desired
    header = struct.pack(">HHHHHH", txid, flags, 1, 0, 0, 0)
    # Encode hostname as DNS labels: each label is length + bytes, terminated by 0x00
    qname = b""
    for label in hostname.rstrip(".").split("."):
        encoded = label.encode()
        qname += struct.pack("B", len(encoded)) + encoded
    qname += b"\x00"
    question = qname + struct.pack(">HH", 1, 1)  # QTYPE=A, QCLASS=IN
    return header + question


def _parse_dns_a_response(data: bytes, hostname: str) -> Optional[str]:
    """Extract the first A-record IPv4 address from a raw DNS response packet."""
    if len(data) < 12:
        return None
    txid, flags, qdcount, ancount = struct.unpack(">HHHH", data[:8])
    if txid != 0xAB12 or ancount == 0:
        return None
    # Skip the header (12 bytes) and question section.
    pos = 12
    # Skip QDCOUNT questions: each is QNAME + QTYPE(2) + QCLASS(2)
    for _ in range(qdcount):
        while pos < len(data) and data[pos] != 0:
            if data[pos] & 0xC0 == 0xC0:  # compression pointer
                pos += 2
                break
            pos += 1 + data[pos]
        else:
            pos += 1  # null terminator
        pos += 4  # skip QTYPE + QCLASS
    # Parse answer records
    for _ in range(ancount):
        if pos >= len(data):
            break
        # Skip NAME field (may be a compression pointer or a label sequence)
        if data[pos] & 0xC0 == 0xC0:
            pos += 2
        else:
            while pos < len(data) and data[pos] != 0:
                pos += 1 + data[pos]
            pos += 1
        if pos + 10 > len(data):
            break
        rtype, rclass, ttl, rdlength = struct.unpack(">HHIH", data[pos : pos + 10])
        pos += 10
        if rtype == 1 and rdlength == 4:  # A record
            return "%d.%d.%d.%d" % tuple(data[pos : pos + 4])
        pos += rdlength
    return None


def _query_google_dns_sync(hostname: str) -> Optional[str]:
    """Blocking: send a DNS A-record query to 8.8.8.8 and return the IPv4 address."""
    try:
        query = _build_dns_query(hostname)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(_DNS_TIMEOUT)
        try:
            sock.sendto(query, (_GOOGLE_DNS, _DNS_PORT))
            data, _ = sock.recvfrom(512)
        finally:
            sock.close()
        return _parse_dns_a_response(data, hostname)
    except Exception:
        return None


async def _query_google_dns_async(hostname: str) -> Optional[str]:
    """Async: run :func:`_query_google_dns_sync` in the default executor."""
    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(None, _query_google_dns_sync, hostname)
    except Exception:
        return None


async def _resolve_ipv4(host: str, port: int) -> Optional[str]:
    """Async: resolve *host* to an IPv4 address using AF_INET getaddrinfo.

    Resolution order:
    1. System resolver (AF_INET getaddrinfo) — result is cached on success.
    2. Local DNS cache (last successful system-resolver result for this host).
    3. Google public DNS (8.8.8.8) — used when both system resolver and cache
       are unavailable.  Result is cached so subsequent calls benefit too.

    Returns None only when all three strategies fail.
    """
    try:
        loop = asyncio.get_running_loop()
        infos = await loop.getaddrinfo(
            host, port, family=socket.AF_INET, type=socket.SOCK_STREAM
        )
        if infos:
            ipv4 = infos[0][4][0]
            if settings.DNS_CACHE_FALLBACK_ENABLED:
                _set_cached_ipv4(host, port, ipv4)
            return ipv4
    except OSError:
        if settings.DNS_CACHE_FALLBACK_ENABLED:
            cached = _get_cached_ipv4(host, port)
            if cached:
                logger.info(
                    "DNS resolution failed for %s:%s; using cached IPv4 %s",
                    host,
                    port,
                    cached,
                )
                return cached
        # Last resort: query 8.8.8.8 directly
        google_ip = await _query_google_dns_async(host)
        if google_ip:
            logger.info(
                "System DNS failed for %s:%s; resolved via 8.8.8.8 → %s",
                host,
                port,
                google_ip,
            )
            if settings.DNS_CACHE_FALLBACK_ENABLED:
                _set_cached_ipv4(host, port, google_ip)
            return google_ip
    return None


def _resolve_ipv4_sync(host: str, port: int) -> Optional[str]:
    """Sync counterpart of :func:`_resolve_ipv4` for use inside thread-pool executors.

    Identical resolution order: system resolver → local cache → 8.8.8.8.
    """
    try:
        infos = socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM)
        if infos:
            ipv4 = infos[0][4][0]
            if settings.DNS_CACHE_FALLBACK_ENABLED:
                _set_cached_ipv4(host, port, ipv4)
            return ipv4
    except OSError:
        if settings.DNS_CACHE_FALLBACK_ENABLED:
            cached = _get_cached_ipv4(host, port)
            if cached:
                logger.info(
                    "DNS resolution failed for %s:%s; using cached IPv4 %s",
                    host,
                    port,
                    cached,
                )
                return cached
        # Last resort: query 8.8.8.8 directly
        google_ip = _query_google_dns_sync(host)
        if google_ip:
            logger.info(
                "System DNS failed for %s:%s; resolved via 8.8.8.8 → %s",
                host,
                port,
                google_ip,
            )
            if settings.DNS_CACHE_FALLBACK_ENABLED:
                _set_cached_ipv4(host, port, google_ip)
            return google_ip
    return None


# ---------------------------------------------------------------------------
# IPv4-preferring POP3 helpers
# ---------------------------------------------------------------------------


class _POP3WithIPv4Pref(poplib.POP3):
    """POP3 variant that connects to a pre-resolved IPv4 address.

    The original *host* is preserved on ``self.host`` so that any code that
    inspects the host name after construction still sees the human-readable
    server name rather than a raw IP.
    """

    def __init__(
        self,
        host: str,
        port: int = 110,
        timeout: int = 30,
        *,
        _ipv4_addr: str = "",
    ) -> None:
        self._ipv4_addr = _ipv4_addr
        super().__init__(host, port, timeout)

    def _create_socket(self, timeout: Any) -> socket.socket:  # type: ignore[override]
        if self._ipv4_addr:
            return socket.create_connection((self._ipv4_addr, self.port), timeout)
        return super()._create_socket(timeout)


class _POP3SSLWithIPv4Pref(poplib.POP3_SSL):
    """POP3_SSL that connects to a pre-resolved IPv4 address while retaining
    the original hostname for TLS SNI and certificate verification.

    ``poplib.POP3_SSL.__init__`` calls ``POP3.__init__`` (which calls
    ``_create_socket``) and afterwards wraps the socket with
    ``context.wrap_socket(sock, server_hostname=self.host)``.  Because
    ``self.host`` is still the original hostname, TLS verification is correct
    even though ``_create_socket`` connects to the IPv4 address.
    """

    def __init__(
        self,
        host: str,
        port: int = 995,
        timeout: int = 30,
        context: Optional[ssl.SSLContext] = None,
        *,
        _ipv4_addr: str = "",
    ) -> None:
        self._ipv4_addr = _ipv4_addr
        super().__init__(host, port, timeout=timeout, context=context)

    def _create_socket(self, timeout: Any) -> socket.socket:  # type: ignore[override]
        if self._ipv4_addr:
            return socket.create_connection((self._ipv4_addr, self.port), timeout)
        return super()._create_socket(timeout)


def _make_pop3_conn(
    protocol: MailProtocol,
    host: str,
    port: int,
    context: Optional[ssl.SSLContext],
    timeout: int,
    ipv4: Optional[str],
) -> poplib.POP3:
    """Factory: return a POP3 (or POP3_SSL) connection, preferring IPv4.

    When *ipv4* is provided and differs from *host* (i.e. the caller pre-
    resolved a hostname to an IPv4 address), the IPv4-preferring subclasses are
    used so the TCP connection goes to the IPv4 address while TLS SNI still
    uses the original hostname.  Otherwise the standard poplib classes are used
    directly (which preserves all existing mock-based unit-test behaviour).
    """
    use_ipv4 = bool(ipv4 and ipv4 != host)
    if protocol == MailProtocol.POP3_SSL:
        if use_ipv4:
            return _POP3SSLWithIPv4Pref(
                host, port, timeout=timeout, context=context, _ipv4_addr=ipv4 or ""
            )
        return poplib.POP3_SSL(host, port, context=context, timeout=timeout)
    else:
        if use_ipv4:
            return _POP3WithIPv4Pref(host, port, timeout=timeout, _ipv4_addr=ipv4 or "")
        return poplib.POP3(host, port, timeout=timeout)


# ---------------------------------------------------------------------------
# IPv4-preferring IMAP helper
# ---------------------------------------------------------------------------


class _IMAP4SSLwithSNI(aioimaplib.IMAP4_SSL):
    """IMAP4_SSL variant that connects to a pre-resolved IPv4 address but uses
    the original hostname for TLS SNI and certificate verification.

    ``asyncio.create_connection`` normally derives ``server_hostname`` from the
    ``host`` argument when an SSL context is supplied.  By passing the IPv4
    address as *host* and the original hostname as ``server_hostname`` we get
    an IPv4-only TCP path without breaking TLS hostname checks.

    ``_original_host`` **must** be set before ``super().__init__`` is called
    because the parent constructor calls ``create_client`` synchronously.
    """

    def __init__(
        self,
        ipv4_addr: str,
        original_host: str,
        port: int,
        timeout: float = 30.0,
    ) -> None:
        self._original_host = original_host
        super().__init__(host=ipv4_addr, port=port, timeout=timeout)

    def create_client(  # type: ignore[override]
        self,
        host: str,
        port: int,
        loop,
        conn_lost_cb=None,
        ssl_context: Optional[ssl.SSLContext] = None,
    ) -> None:
        if ssl_context is None:
            ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        active_loop = loop if loop is not None else asyncio.get_running_loop()
        self.protocol = aioimaplib.IMAP4ClientProtocol(active_loop, conn_lost_cb)
        self._client_task = active_loop.create_task(
            active_loop.create_connection(
                lambda: self.protocol,
                host,
                port,
                ssl=ssl_context,
                server_hostname=self._original_host,
            )
        )


async def _make_imap_client(
    protocol: MailProtocol,
    host: str,
    port: int,
    timeout: float = 30.0,
) -> aioimaplib.IMAP4:
    """Async factory: return an IMAP4 (or IMAP4_SSL) client, preferring IPv4.

    Resolves *host* to an IPv4 address via :func:`_resolve_ipv4` (which caches
    successful lookups and can fall back to the cache on transient DNS errors).
    When a different IPv4 address is found the appropriate IPv4-preferring
    subclass is returned; otherwise the standard aioimaplib classes are used
    directly, which preserves existing mock-based unit-test behaviour.
    """
    ipv4 = await _resolve_ipv4(host, port)
    use_ipv4 = bool(ipv4 and ipv4 != host)
    if protocol == MailProtocol.IMAP_SSL:
        if use_ipv4:
            return _IMAP4SSLwithSNI(ipv4 or host, host, port, timeout=timeout)
        return aioimaplib.IMAP4_SSL(host=host, port=port, timeout=timeout)
    else:
        return aioimaplib.IMAP4(
            host=ipv4 if use_ipv4 else host, port=port, timeout=timeout
        )


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


# ---------------------------------------------------------------------------
# Transient-error detection (used by retry logic)
# ---------------------------------------------------------------------------

#: Maximum number of attempts for a POP3/IMAP connection.
_MAX_FETCH_ATTEMPTS = 3
#: Seconds to wait between retry attempts (fixed back-off).
_FETCH_RETRY_DELAY = 5.0


def _is_transient_error(exc: BaseException) -> bool:
    """Return True for errors that are safe to retry (network glitches, EOF).

    Authentication errors and protocol-level rejections should NOT be retried
    as they will fail on every attempt regardless.
    """
    # EOF from POP3 server (connection dropped during or just after SSL handshake)
    if isinstance(exc, poplib.error_proto):
        msg = str(exc).lower()
        return "eof" in msg or "timed out" in msg
    # Network timeout (sync or async)
    if isinstance(exc, (socket.timeout, asyncio.TimeoutError, TimeoutError)):
        return True
    # Server dropped the connection
    if isinstance(exc, (ConnectionResetError, ConnectionAbortedError)):
        return True
    # IMAP server aborted the session
    try:
        if isinstance(exc, aioimaplib.Abort):
            return True
    except TypeError:
        pass
    return False


def _format_connection_error(
    exc: BaseException,
    host: str = "",
    port: int = 0,
    protocol: str = "",
) -> str:
    """Return a human-readable error message for a mail connection failure.

    Never returns an empty string – always includes the exception type as a
    fallback so the dashboard always shows an actionable message.
    """
    loc = f"{host}:{port}" if host else ""
    proto = f"{protocol} " if protocol else ""

    # DNS resolution failure (socket.gaierror is a subclass of OSError)
    if isinstance(exc, socket.gaierror):
        # errno -3 / EAI_AGAIN means the DNS server is temporarily unavailable --
        # this is a transient infrastructure error, not a misconfigured address.
        if exc.args[0] == socket.EAI_AGAIN:
            if host:
                return (
                    f"Temporary DNS failure while resolving '{host}' --"
                    f" the DNS server may be temporarily unavailable ({exc})"
                )
            return f"Temporary DNS failure: {exc}"
        if host:
            return (
                f"Could not resolve hostname '{host}' — check that the server "
                f"address is correct (DNS lookup failed: {exc})"
            )
        return f"DNS lookup failed: {exc}"

    # Connection / operation timeout
    if isinstance(exc, (socket.timeout, asyncio.TimeoutError, TimeoutError)):
        if loc:
            return (
                f"{proto}connection to {loc} timed out — the server may be "
                f"slow or blocking connections"
            )
        return f"{proto}connection timed out"

    # Connection refused by the server
    if isinstance(exc, ConnectionRefusedError):
        if loc:
            return (
                f"Connection refused by {loc} — check that the host and port "
                f"are correct and the server is running"
            )
        return f"Connection refused: {exc}"

    # Server closed the connection unexpectedly
    if isinstance(exc, ConnectionResetError):
        if loc:
            return f"Connection reset by {loc} — the server closed the connection unexpectedly"
        return f"Connection reset: {exc}"

    # TLS certificate verification failure
    if isinstance(exc, ssl.SSLCertVerificationError):
        reason = getattr(exc, "reason", "") or str(exc)
        if loc:
            return f"TLS certificate verification failed for {loc}: {reason}"
        return f"TLS certificate verification failed: {reason}"

    # Generic TLS/SSL error
    if isinstance(exc, ssl.SSLError):
        reason = getattr(exc, "reason", "") or str(exc)
        if loc:
            return f"TLS/SSL error connecting to {loc}: {reason}"
        return f"TLS/SSL error: {reason}"

    # POP3 protocol error (auth rejection, server-side error, etc.)
    if isinstance(exc, poplib.error_proto):
        msg = str(exc).strip() or repr(exc)
        msg_lower = msg.lower()
        if any(
            k in msg_lower
            for k in (
                "auth",
                "login",
                "password",
                "user",
                "pass",
                "invalid",
                "denied",
                "failed",
            )
        ):
            if loc:
                return f"Authentication rejected by {loc}: {msg}"
            return f"POP3 authentication failed: {msg}"
        if loc:
            return f"POP3 server {loc} returned an error: {msg}"
        return f"POP3 error: {msg}"

    # IMAP connection aborted by the server
    try:
        if isinstance(exc, aioimaplib.Abort):
            msg = str(exc).strip() or "server closed the connection"
            if loc:
                return f"IMAP connection to {loc} was aborted: {msg}"
            return f"IMAP connection aborted: {msg}"
    except TypeError:
        # aioimaplib may be mocked in tests, making Abort a non-type
        pass

    # Generic OSError with an OS-level error code
    if isinstance(exc, OSError) and exc.errno:
        strerror = exc.strerror or str(exc)
        if loc:
            return f"Network error connecting to {loc}: {strerror}"
        return f"Network error: {strerror}"

    # Catch-all: produce a non-empty string regardless of the exception type
    msg = str(exc).strip()
    if not msg:
        # Some exceptions (e.g. bare asyncio.TimeoutError) have no message
        msg = type(exc).__name__
    if loc:
        return f"{proto}error communicating with {loc}: {msg}"
    return f"{type(exc).__name__}: {msg or repr(exc)}"


# Maximum number of entries / bytes kept in a single debug trace
_MAX_TRACE_ENTRIES = 200
_MAX_TRACE_BYTES = 65_536  # 64 KiB


class MailDebugRecorder:
    """Collects a structured trace of an IMAP/POP3 connection for debug display.

    Thread-safe for list.append() calls thanks to the CPython GIL.  The
    recorder is passed into :class:`MailProcessor` when
    ``account.debug_logging`` is True and persisted as a
    ``ProcessingLog`` row with ``level="DEBUG"`` at the end of the run.
    """

    def __init__(self) -> None:
        self._entries: List[Dict[str, Any]] = []
        self._total_bytes: int = 0
        self._truncated: bool = False

    def record(
        self,
        phase: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Append a trace entry (no-op once the size cap is reached)."""
        if self._truncated:
            return
        entry: Dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "phase": phase,
            "msg": message,
        }
        if data:
            entry["data"] = data
        try:
            entry_bytes = len(str(entry))
        except Exception:
            entry_bytes = 256  # conservative fallback
        if (
            len(self._entries) >= _MAX_TRACE_ENTRIES
            or self._total_bytes + entry_bytes > _MAX_TRACE_BYTES
        ):
            self._entries.append(
                {
                    "ts": entry["ts"],
                    "phase": "truncated",
                    "msg": (
                        f"Trace truncated after {len(self._entries)} entries "
                        f"(size limit {_MAX_TRACE_BYTES // 1024} KiB reached)"
                    ),
                }
            )
            self._truncated = True
            return
        self._entries.append(entry)
        self._total_bytes += entry_bytes

    def has_entries(self) -> bool:
        return bool(self._entries)

    def __len__(self) -> int:
        return len(self._entries)

    def as_details(self) -> Dict[str, Any]:
        """Return the trace as a dict suitable for storage in error_details."""
        return {"trace": self._entries, "truncated": self._truncated}


class MailProcessor:
    """Handles mail fetching and forwarding operations"""

    def __init__(
        self,
        account: MailAccount,
        decrypted_password: str,
        debug_recorder: Optional[MailDebugRecorder] = None,
    ):
        self.account = account
        self.password = decrypted_password
        self._debug = debug_recorder

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
            loop = asyncio.get_running_loop()
            _dbg = self._debug
            _host = str(self.account.host)
            _port = int(self.account.port)
            _protocol = self.account.protocol

            # Run blocking POP3 operations in thread pool
            def connect_pop3():
                _t0 = _time.monotonic()
                _ipv4 = _resolve_ipv4_sync(_host, _port)
                _ctx = (
                    ssl.create_default_context()
                    if _protocol == MailProtocol.POP3_SSL
                    else None
                )
                pop_conn = _make_pop3_conn(_protocol, _host, _port, _ctx, 10, _ipv4)
                if _dbg:
                    _dbg.record(
                        "connect",
                        f"Connected to {_host}:{_port} "
                        f"({'SSL' if _protocol == MailProtocol.POP3_SSL else 'plain'})"
                        + (f" via {_ipv4}" if _ipv4 and _ipv4 != _host else ""),
                        {"elapsed_ms": round((_time.monotonic() - _t0) * 1000)},
                    )

                # Try authentication
                _t1 = _time.monotonic()
                pop_conn.user(self.account.username)
                pop_conn.pass_(self.password)
                if _dbg:
                    _dbg.record(
                        "auth",
                        f"Authenticated as {self.account.username}",
                        {"elapsed_ms": round((_time.monotonic() - _t1) * 1000)},
                    )

                # Get mailbox stats
                message_count, mailbox_size = pop_conn.stat()
                if _dbg:
                    _dbg.record(
                        "stat",
                        f"Mailbox has {message_count} messages ({mailbox_size} bytes)",
                    )
                pop_conn.quit()
                return message_count, mailbox_size

            message_count, mailbox_size = await loop.run_in_executor(None, connect_pop3)

            return True, f"Connection successful. {message_count} messages in mailbox."

        except Exception as e:
            return (
                False,
                _format_connection_error(
                    e,
                    str(self.account.host),
                    int(self.account.port),
                    "POP3",
                ),
            )

    async def _test_imap_connection(self) -> Tuple[bool, str]:
        """Test IMAP connection"""
        try:
            host = str(self.account.host)
            port = int(self.account.port)
            imap_client = await _make_imap_client(
                self.account.protocol, host, port, timeout=10
            )

            _t0 = _time.monotonic()
            await imap_client.wait_hello_from_server()
            if self._debug:
                self._debug.record(
                    "connect",
                    f"Connected to {self.account.host}:{self.account.port} "
                    f"({'SSL' if self.account.protocol == MailProtocol.IMAP_SSL else 'plain'})",
                    {"elapsed_ms": round((_time.monotonic() - _t0) * 1000)},
                )

            # Authenticate
            _t1 = _time.monotonic()
            response = await imap_client.login(self.account.username, self.password)

            if response.result != "OK":
                return (
                    False,
                    f"Authentication rejected by {self.account.host}:{self.account.port}: "
                    f"{response.lines}",
                )
            if self._debug:
                self._debug.record(
                    "auth",
                    f"Authenticated as {self.account.username}",
                    {"elapsed_ms": round((_time.monotonic() - _t1) * 1000)},
                )

            # Select inbox
            await imap_client.select("INBOX")
            if self._debug:
                self._debug.record("select", "Selected INBOX")

            # Get message count
            response = await imap_client.search("ALL")
            message_ids = response.lines[0].split()
            message_count = len(message_ids)
            if self._debug:
                self._debug.record(
                    "search",
                    f"INBOX contains {message_count} messages",
                )

            await imap_client.logout()
            if self._debug:
                self._debug.record("logout", "Logged out successfully")

            return True, f"Connection successful. {message_count} messages in mailbox."

        except Exception as e:
            return (
                False,
                _format_connection_error(
                    e,
                    str(self.account.host),
                    int(self.account.port),
                    "IMAP",
                ),
            )

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
            # POP3 already carries its own retry loop inside _fetch_pop3_emails.
            return await self._fetch_pop3_emails(effective_max, seen)

        # IMAP: retry transient errors up to _MAX_FETCH_ATTEMPTS times.
        last_exc: BaseException = RuntimeError("no attempts made")
        for _attempt in range(1, _MAX_FETCH_ATTEMPTS + 1):
            try:
                return await self._fetch_imap_emails(effective_max, seen)
            except MailFetchError as e:
                last_exc = e
                # Peek at the original cause to decide whether to retry.
                cause = e.__cause__ or e
                if _attempt < _MAX_FETCH_ATTEMPTS and _is_transient_error(cause):
                    logger.warning(
                        "Transient IMAP error on attempt %d/%d for account %s: %s; retrying in %.0f s",
                        _attempt,
                        _MAX_FETCH_ATTEMPTS,
                        self.account.id,
                        e,
                        _FETCH_RETRY_DELAY,
                    )
                    await asyncio.sleep(_FETCH_RETRY_DELAY)
                else:
                    break
        raise last_exc

    async def _fetch_pop3_emails(
        self, max_count: int, already_seen_uids: Set[str]
    ) -> Tuple[List[bytes], List[str]]:
        """Fetch emails via POP3, skipping already-downloaded UIDs."""
        emails: List[bytes] = []
        new_uids: List[str] = []

        loop = asyncio.get_running_loop()
        _dbg = self._debug  # capture for thread-pool closure
        _host = str(self.account.host)
        _port = int(self.account.port)
        _protocol = self.account.protocol

        def fetch_pop3() -> Tuple[List[bytes], List[str]]:
            _t_conn = _time.monotonic()
            # Connect – prefer IPv4 to avoid ENETUNREACH on IPv6-only paths
            _ipv4 = _resolve_ipv4_sync(_host, _port)
            _ctx = (
                ssl.create_default_context()
                if _protocol == MailProtocol.POP3_SSL
                else None
            )
            pop_conn = _make_pop3_conn(_protocol, _host, _port, _ctx, 30, _ipv4)
            if _dbg:
                _dbg.record(
                    "connect",
                    f"Connected to {_host}:{_port} "
                    f"({'SSL' if _protocol == MailProtocol.POP3_SSL else 'plain'})"
                    + (f" via {_ipv4}" if _ipv4 and _ipv4 != _host else ""),
                    {"elapsed_ms": round((_time.monotonic() - _t_conn) * 1000)},
                )

            # Authenticate
            _t_auth = _time.monotonic()
            pop_conn.user(str(self.account.username))
            pop_conn.pass_(self.password)
            if _dbg:
                _dbg.record(
                    "auth",
                    f"Authenticated as {self.account.username}",
                    {"elapsed_ms": round((_time.monotonic() - _t_auth) * 1000)},
                )

            # Retrieve UIDL map: {msg_number: uid_string}
            uidl_response = pop_conn.uidl()
            uid_map: Dict[int, str] = {}
            for entry in uidl_response[1]:
                parts = entry.decode().split(" ", 1)
                if len(parts) == 2:
                    uid_map[int(parts[0])] = parts[1].strip()

            num_messages = len(uid_map)
            if _dbg:
                _dbg.record(
                    "uidl",
                    f"Mailbox contains {num_messages} messages; "
                    f"{len(already_seen_uids)} already downloaded",
                    {"total": num_messages, "already_seen": len(already_seen_uids)},
                )
            logger.info(f"Found {num_messages} messages for account {self.account.id}")

            fetched: List[bytes] = []
            fetched_uids: List[str] = []
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
                    _t_msg = _time.monotonic()
                    response, lines, octets = pop_conn.retr(msg_num)
                    email_data = b"\r\n".join(lines)
                    fetched.append(email_data)
                    fetched_uids.append(uid)
                    fetched_count += 1
                    elapsed = round((_time.monotonic() - _t_msg) * 1000)
                    logger.info(
                        f"Retrieved message {msg_num} (uid={uid}) "
                        f"from account {self.account.id}"
                    )
                    if _dbg:
                        _dbg.record(
                            "fetch_msg",
                            f"Fetched message {msg_num} (uid={uid}): "
                            f"{len(email_data)} bytes",
                            {
                                "msg_num": msg_num,
                                "uid": uid,
                                "size_bytes": len(email_data),
                                "elapsed_ms": elapsed,
                            },
                        )
                except Exception as e:
                    logger.error(f"Error retrieving message {msg_num}: {e}")
                    if _dbg:
                        _dbg.record(
                            "fetch_error",
                            f"Failed to retrieve message {msg_num} (uid={uid}): {e}",
                            {"msg_num": msg_num, "uid": uid},
                        )

            pop_conn.quit()
            if _dbg:
                _dbg.record(
                    "quit",
                    f"Disconnected — fetched {fetched_count} new message(s)",
                    {"fetched": fetched_count},
                )
            return fetched, fetched_uids

        # Retry loop: transient errors (EOF, timeout, connection reset) are
        # retried up to _MAX_FETCH_ATTEMPTS times with a short fixed delay.
        last_exc: BaseException = RuntimeError("no attempts made")
        for _attempt in range(1, _MAX_FETCH_ATTEMPTS + 1):
            try:
                emails, new_uids = await loop.run_in_executor(None, fetch_pop3)
                return emails, new_uids
            except Exception as e:
                last_exc = e
                if _attempt < _MAX_FETCH_ATTEMPTS and _is_transient_error(e):
                    logger.warning(
                        "Transient POP3 error on attempt %d/%d for account %s: %s; retrying in %.0f s",
                        _attempt,
                        _MAX_FETCH_ATTEMPTS,
                        self.account.id,
                        e,
                        _FETCH_RETRY_DELAY,
                    )
                    await asyncio.sleep(_FETCH_RETRY_DELAY)
                else:
                    break

        logger.error(f"Error fetching POP3 emails: {last_exc}")
        raise MailFetchError(
            _format_connection_error(
                last_exc,
                str(self.account.host),
                int(self.account.port),
                "POP3",
            )
        )

    async def _fetch_imap_emails(
        self, max_count: int, already_seen_uids: Set[str]
    ) -> Tuple[List[bytes], List[str]]:
        """Fetch emails via IMAP using UID-based commands.

        UIDs are stable identifiers that do not change when other messages are
        expunged, unlike IMAP sequence numbers.  Sequence-number-based FETCH /
        STORE commands can target the wrong message mid-session and cause
        servers to report "Too many invalid IMAP commands" (as seen with
        t-online).  This implementation:

        * Uses a plain ``SEARCH UNSEEN`` to retrieve sequence numbers, then a
          lightweight ``FETCH (UID)`` to resolve them to stable UIDs.
          (``aioimaplib``'s ``.uid()`` wrapper does not support ``SEARCH``.)
        * Uses ``UID FETCH`` and ``UID STORE`` for all subsequent operations.
        * Re-marks already-processed UIDs as \\Seen in a single batch command
          instead of one STORE per message.
        * Relies on the implicit \\Seen flag set by RFC822 FETCH so no
          additional per-message STORE is needed for newly fetched mail.
        * Batches the \\Deleted STORE into a single command when
          ``delete_after_forward`` is enabled.
        * Uses RFC 3501–compliant parenthesised flag syntax, e.g.
          ``+FLAGS (\\Seen)``, required by strict servers such as T-Online.
        """
        emails: List[bytes] = []
        new_uids: List[str] = []

        imap_client = None
        try:
            # Create IMAP client, preferring IPv4 to avoid ENETUNREACH on IPv6-only paths
            imap_client = await _make_imap_client(
                self.account.protocol,
                str(self.account.host),
                int(self.account.port),
                timeout=30,
            )

            _t_conn = _time.monotonic()
            await imap_client.wait_hello_from_server()
            if self._debug:
                self._debug.record(
                    "connect",
                    f"Connected to {self.account.host}:{self.account.port} "
                    f"({'SSL' if self.account.protocol == MailProtocol.IMAP_SSL else 'plain'})",
                    {"elapsed_ms": round((_time.monotonic() - _t_conn) * 1000)},
                )

            _t_auth = _time.monotonic()
            await imap_client.login(self.account.username, self.password)
            if self._debug:
                self._debug.record(
                    "auth",
                    f"Authenticated as {self.account.username}",
                    {"elapsed_ms": round((_time.monotonic() - _t_auth) * 1000)},
                )

            await imap_client.select("INBOX")
            if self._debug:
                self._debug.record("select", "Selected INBOX")

            # Step 1: Standard sequence-based SEARCH for UNSEEN messages.
            # aioimaplib's .uid() wrapper explicitly blocks "search", so we
            # use the plain SEARCH command and resolve to UIDs in step 2.
            _t_search = _time.monotonic()
            response = await imap_client.search("UNSEEN")
            if (
                response.result != "OK"
                or not response.lines
                or not response.lines[0].strip()
            ):
                if self._debug:
                    self._debug.record(
                        "search",
                        "SEARCH UNSEEN returned 0 messages",
                        {"elapsed_ms": round((_time.monotonic() - _t_search) * 1000)},
                    )
                logger.info(f"Found 0 unread messages for account {self.account.id}")
                # logout is handled by the finally block below
                return emails, new_uids

            seq_nums: List[bytes] = response.lines[0].split()
            if not seq_nums:
                if self._debug:
                    self._debug.record(
                        "search",
                        "SEARCH UNSEEN returned 0 messages",
                        {"elapsed_ms": round((_time.monotonic() - _t_search) * 1000)},
                    )
                logger.info(f"Found 0 unread messages for account {self.account.id}")
                return emails, new_uids

            if self._debug:
                self._debug.record(
                    "search",
                    f"SEARCH UNSEEN found {len(seq_nums)} message(s); "
                    f"limiting to {min(len(seq_nums), max_count)}",
                    {
                        "total_unseen": len(seq_nums),
                        "max_count": max_count,
                        "elapsed_ms": round((_time.monotonic() - _t_search) * 1000),
                    },
                )

            # Limit to max_count before doing any further work.
            seq_nums = seq_nums[:max_count]

            # Step 2: Resolve sequence numbers to stable UIDs with a
            # lightweight FETCH (UID) so all subsequent commands are UID-based.
            seq_string = b",".join(seq_nums).decode()
            uid_resp = await imap_client.fetch(seq_string, "(UID)")

            # Step 3: Parse UIDs from response lines.
            # Each line looks like: b'1 (UID 42)'
            all_unseen_uids: List[bytes] = []
            for line in uid_resp.lines:
                if isinstance(line, bytes):
                    m = re.search(rb"\bUID\s+(\d+)", line)
                    if m:
                        all_unseen_uids.append(m.group(1))

            logger.info(
                f"Found {len(all_unseen_uids)} unread messages for account "
                f"{self.account.id}"
            )
            if self._debug:
                self._debug.record(
                    "fetch_uids",
                    f"Resolved {len(all_unseen_uids)} UID(s); "
                    f"{len(already_seen_uids)} already downloaded",
                    {
                        "uids": [u.decode() for u in all_unseen_uids[:10]],
                        "already_seen": len(already_seen_uids),
                    },
                )

            # Step 4: Split into stale UIDs (already in our DB but still
            # UNSEEN on the server — e.g. a previous STORE failed) and
            # genuinely new UIDs.
            stale_uid_bytes: List[bytes] = []
            uids_to_fetch: List[bytes] = []
            for uid in all_unseen_uids:
                uid_str = uid.decode() if isinstance(uid, bytes) else str(uid)
                if uid_str in already_seen_uids:
                    stale_uid_bytes.append(uid)
                else:
                    uids_to_fetch.append(uid)

            if self._debug and stale_uid_bytes:
                self._debug.record(
                    "stale_uids",
                    f"Re-marking {len(stale_uid_bytes)} stale UID(s) as \\Seen "
                    f"(already downloaded but still UNSEEN on server)",
                    {"count": len(stale_uid_bytes)},
                )

            # Re-mark stale UIDs as \Seen in a single batch STORE command so
            # they stop appearing in UNSEEN searches without consuming one
            # round-trip per message.
            # RFC 3501 requires parentheses around flag names: +FLAGS (\Seen).
            if stale_uid_bytes:
                uid_set = b",".join(stale_uid_bytes).decode()
                try:
                    await imap_client.uid("store", uid_set, "+FLAGS", "(\\Seen)")
                except Exception as e:
                    logger.warning(
                        f"Failed to re-mark stale messages as \\Seen for account "
                        f"{self.account.id}: {e}"
                    )

            # Fetch each new message using BODY.PEEK[] so the \Seen flag is NOT
            # set implicitly.  Successfully forwarded messages are marked \Seen
            # (and optionally \Deleted) afterwards via post_process_imap().
            # This ensures that emails which fail to forward remain \Unseen and
            # are therefore retried on the next SEARCH UNSEEN run.
            for uid in uids_to_fetch:
                uid_str = uid.decode() if isinstance(uid, bytes) else str(uid)
                try:
                    _t_msg = _time.monotonic()
                    fetch_response = await imap_client.uid(
                        "fetch", uid_str, "(BODY.PEEK[])"
                    )

                    # Extract raw email bytes from the FETCH response lines.
                    # A UID FETCH response looks like:
                    #   [b'<seq> (UID <uid> BODY[] {<size>}', <email_bytes>, b')']
                    # Skip the status/header line (contains "BODY[" or "RFC822")
                    # and grab the first substantive bytes value.
                    #
                    # aioimaplib stores IMAP literal data (the actual email
                    # content) as bytearray, not bytes.  We must accept both
                    # types; bytes() converts bytearray so the rest of the
                    # pipeline always receives plain bytes.
                    email_data: Optional[bytes] = None
                    for line in fetch_response.lines:
                        if not isinstance(line, (bytes, bytearray)):
                            continue
                        if b"RFC822" in line or b"BODY[" in line:
                            continue
                        if line.startswith(b"*"):
                            continue
                        if line in (b")", b""):
                            continue
                        email_data = bytes(line)
                        break

                    if email_data and email_data.strip():
                        elapsed = round((_time.monotonic() - _t_msg) * 1000)
                        emails.append(email_data)
                        new_uids.append(uid_str)
                        if self._debug:
                            self._debug.record(
                                "fetch_msg",
                                f"Fetched UID {uid_str}: {len(email_data)} bytes",
                                {
                                    "uid": uid_str,
                                    "size_bytes": len(email_data),
                                    "elapsed_ms": elapsed,
                                },
                            )
                    else:
                        logger.warning(
                            f"No email data extracted for UID {uid_str} on "
                            f"account {self.account.id} "
                            f"(raw bytes: {len(email_data) if email_data else 0}); "
                            "this may indicate a server-side error producing empty "
                            "IMAP responses"
                        )
                        if self._debug:
                            self._debug.record(
                                "fetch_empty",
                                f"UID {uid_str} returned empty body — skipped",
                                {
                                    "uid": uid_str,
                                    "raw_bytes": len(email_data) if email_data else 0,
                                },
                            )

                except Exception as e:
                    logger.error(
                        f"Error fetching message UID {uid_str} for account "
                        f"{self.account.id}: {e}"
                    )
                    if self._debug:
                        self._debug.record(
                            "fetch_error",
                            f"Failed to fetch UID {uid_str}: {e}",
                            {"uid": uid_str},
                        )

        except MailFetchError:
            raise
        except Exception as e:
            logger.error(
                f"Error fetching IMAP emails for account {self.account.id}: {e}"
            )
            if self._debug:
                self._debug.record(
                    "error",
                    f"Fatal error: {_format_connection_error(e, str(self.account.host), int(self.account.port), 'IMAP')}",
                )
            raise MailFetchError(
                _format_connection_error(
                    e,
                    str(self.account.host),
                    int(self.account.port),
                    "IMAP",
                )
            ) from e
        finally:
            # Always attempt a clean logout.  If the server already sent BYE
            # the logout call will fail silently rather than masking the real
            # error.
            if imap_client is not None:
                try:
                    await imap_client.logout()
                    if self._debug:
                        self._debug.record("logout", "Logged out successfully")
                except Exception:
                    pass

        return emails, new_uids

    async def post_process_imap(self, successfully_forwarded_uids: List[str]) -> None:
        """Mark successfully forwarded IMAP messages as \\Seen and optionally delete.

        Because fetch uses ``BODY.PEEK[]`` (which does NOT set \\Seen), this
        step is required so successfully processed messages stop appearing in
        ``SEARCH UNSEEN``.  Messages that failed to forward are intentionally
        left \\Unseen so they are retried on the next processing run.

        If ``delete_after_forward`` is enabled, the messages are also flagged
        \\Deleted and the mailbox is expunged.
        """
        if not successfully_forwarded_uids:
            return

        imap_client = None
        try:
            imap_client = await _make_imap_client(
                self.account.protocol,
                str(self.account.host),
                int(self.account.port),
                timeout=30,
            )

            await imap_client.wait_hello_from_server()
            await imap_client.login(self.account.username, self.password)
            await imap_client.select("INBOX")

            uid_set = ",".join(successfully_forwarded_uids)

            # Mark as \Seen so they no longer appear in SEARCH UNSEEN.
            await imap_client.uid("store", uid_set, "+FLAGS", "(\\Seen)")

            if self.account.delete_after_forward:
                await imap_client.uid("store", uid_set, "+FLAGS", "(\\Deleted)")
                await imap_client.expunge()

        except Exception as e:
            logger.warning(
                "Failed to post-process IMAP messages for account %s: %s",
                self.account.id,
                e,
            )
        finally:
            if imap_client is not None:
                try:
                    await imap_client.logout()
                except Exception:
                    pass

    async def post_process_pop3(self, successfully_forwarded_uids: List[str]) -> None:
        """Delete successfully forwarded POP3 messages from the source mailbox.

        Opens a fresh POP3 session, maps stable UIDs back to current message
        numbers via UIDL, and deletes only the messages that were successfully
        forwarded.  Messages that failed to forward are intentionally left on
        the server so they are retried on the next processing run.

        This method is a no-op when ``delete_after_forward`` is ``False``.
        """
        if not successfully_forwarded_uids or not self.account.delete_after_forward:
            return

        loop = asyncio.get_running_loop()
        uid_set = set(successfully_forwarded_uids)
        _host = str(self.account.host)
        _port = int(self.account.port)
        _protocol = self.account.protocol

        def _delete_pop3() -> None:
            _ipv4 = _resolve_ipv4_sync(_host, _port)
            _ctx = (
                ssl.create_default_context()
                if _protocol == MailProtocol.POP3_SSL
                else None
            )
            pop_conn: poplib.POP3 = _make_pop3_conn(
                _protocol, _host, _port, _ctx, 30, _ipv4
            )

            pop_conn.user(str(self.account.username))
            pop_conn.pass_(self.password)

            uidl_response = pop_conn.uidl()
            for entry in uidl_response[1]:
                parts = entry.decode().split(" ", 1)
                if len(parts) != 2:
                    continue
                msg_num = int(parts[0])
                uid = parts[1].strip()
                if uid in uid_set:
                    try:
                        pop_conn.dele(msg_num)
                    except Exception as e:
                        logger.error(
                            "Error deleting POP3 message %s (uid=%s) "
                            "for account %s: %s",
                            msg_num,
                            uid,
                            self.account.id,
                            e,
                        )

            pop_conn.quit()

        try:
            await loop.run_in_executor(None, _delete_pop3)
        except Exception as e:
            logger.warning(
                "Failed to delete POP3 messages for account %s: %s",
                self.account.id,
                e,
            )

    async def post_process_messages(
        self, successfully_forwarded_uids: List[str]
    ) -> None:
        """Post-process successfully forwarded messages.

        Routes to the protocol-specific post-processor:
        * IMAP: marks messages \\Seen (and \\Deleted + expunges if configured).
        * POP3: deletes messages from the source mailbox if configured.

        Must be called *after* the forwarding loop so that messages which
        failed to forward remain untouched in the source mailbox and are
        retried on the next run.
        """
        if self.account.protocol in [MailProtocol.POP3, MailProtocol.POP3_SSL]:
            await self.post_process_pop3(successfully_forwarded_uids)
        else:
            await self.post_process_imap(successfully_forwarded_uids)

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
            loop = asyncio.get_running_loop()

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
