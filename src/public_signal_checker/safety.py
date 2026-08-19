"""URL validation and destination authorization.

This module treats every URL as untrusted. It permits only http/https and
blocks destinations that are not globally routable public addresses.

Limitation: authorization inspects DNS answers before the HTTP client
connects. A resolver answer can change between that check and the TCP/TLS
handshake (DNS rebinding / TOCTOU). This local CLI does not pin connections
to pre-resolved addresses. See SECURITY.md.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

from public_signal_checker.models import SignalCheckerError

ALLOWED_SCHEMES = frozenset({"http", "https"})

BLOCKED_HOSTS = frozenset(
    {
        "localhost",
        "localhost.localdomain",
        "ip6-localhost",
        "ip6-loopback",
        "metadata.google.internal",
    }
)

BLOCKED_HOST_SUFFIXES = (
    ".localhost",
    ".local",
    ".internal",
    ".intranet",
    ".corp",
    ".home",
    ".lan",
    ".localdomain",
    ".private",
    ".test",
    ".invalid",
    ".example",
)

_UNSAFE_TARGET_MESSAGE = "The URL is not a permitted public HTTP(S) target."


class UnsafeURLError(SignalCheckerError):
    """Raised when a URL is invalid, unsupported, or not a public target."""


def authorize_url(url: str) -> str:
    """Validate *url* and authorize its destination before any request.

    Returns the original URL string if authorization succeeds.
    """
    if not isinstance(url, str) or not url.strip():
        raise UnsafeURLError("The URL is invalid.")

    candidate = url.strip()
    if "\x00" in candidate:
        raise UnsafeURLError("The URL is invalid.")

    try:
        parsed = urlparse(candidate)
    except ValueError as exc:
        raise UnsafeURLError("The URL is invalid.") from exc

    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        raise UnsafeURLError("Unsupported URL scheme. Only http and https are allowed.")

    if parsed.username is not None or parsed.password is not None:
        raise UnsafeURLError("The URL is not a permitted public HTTP(S) target.")

    hostname = parsed.hostname
    if not hostname:
        raise UnsafeURLError("The URL is invalid.")

    if _hostname_is_blocked(hostname):
        raise UnsafeURLError(_UNSAFE_TARGET_MESSAGE)

    literal_ip = _literal_ip(hostname)
    if literal_ip is not None:
        if _ip_is_blocked(literal_ip):
            raise UnsafeURLError(_UNSAFE_TARGET_MESSAGE)
        return candidate

    for ip in _resolve_all_ips(hostname):
        if _ip_is_blocked(ip):
            raise UnsafeURLError(_UNSAFE_TARGET_MESSAGE)

    return candidate


def _hostname_is_blocked(hostname: str) -> bool:
    host = hostname.strip(".").lower()
    if host in BLOCKED_HOSTS:
        return True
    return any(host.endswith(suffix) for suffix in BLOCKED_HOST_SUFFIXES)


def _literal_ip(
    hostname: str,
) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    try:
        return ipaddress.ip_address(hostname)
    except ValueError:
        pass

    try:
        packed = socket.inet_aton(hostname)
        return ipaddress.IPv4Address(packed)
    except (OSError, ValueError):
        pass

    try:
        packed = socket.inet_pton(socket.AF_INET6, hostname)
        return ipaddress.IPv6Address(packed)
    except (OSError, ValueError):
        return None


def _resolve_all_ips(
    hostname: str,
) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    try:
        infos = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise UnsafeURLError("The hostname could not be resolved.") from exc

    ips: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = []
    seen: set[str] = set()
    for info in infos:
        addr = info[4][0]
        if addr in seen:
            continue
        seen.add(addr)
        try:
            ips.append(ipaddress.ip_address(addr))
        except ValueError:
            continue

    if not ips:
        raise UnsafeURLError("The hostname could not be resolved.")
    return ips


def _ip_is_blocked(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    effective = _effective_ip(ip)
    if (
        effective.is_multicast
        or effective.is_loopback
        or effective.is_link_local
        or effective.is_private
        or effective.is_unspecified
        or effective.is_reserved
    ):
        return True
    if isinstance(effective, ipaddress.IPv4Address) and int(effective) == 0xFFFFFFFF:
        return True
    if isinstance(effective, ipaddress.IPv6Address) and effective.is_site_local:
        return True
    return not effective.is_global


def _effective_ip(
    ip: ipaddress.IPv4Address | ipaddress.IPv6Address,
) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    if isinstance(ip, ipaddress.IPv6Address):
        if ip.ipv4_mapped is not None:
            return ip.ipv4_mapped
        if ip.sixtofour is not None:
            return ip.sixtofour
        teredo = ip.teredo
        if teredo is not None:
            return teredo[1]
    return ip
