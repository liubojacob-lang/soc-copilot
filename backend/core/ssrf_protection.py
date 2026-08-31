"""SSRF protection utilities — comprehensive private IP and hostname validation."""

from __future__ import annotations

import ipaddress
import logging
import socket
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Cloud metadata hostnames that should never be accessible
BLOCKED_METADATA_HOSTNAMES: frozenset[str] = frozenset(
    {
        "metadata.google.internal",
        "metadata.goog",
    }
)

# Reserved IP networks that should never be reachable
_PRIVATE_NETWORKS: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = [
    # RFC 1918 private ranges
    ipaddress.IPv4Network("10.0.0.0/8"),
    ipaddress.IPv4Network("172.16.0.0/12"),
    ipaddress.IPv4Network("192.168.0.0/16"),
    # Loopback
    ipaddress.IPv4Network("127.0.0.0/8"),
    ipaddress.IPv6Network("::1/128"),
    # Link-local (covers AWS/GCP/Azure metadata at 169.254.x.x)
    ipaddress.IPv4Network("169.254.0.0/16"),
    ipaddress.IPv6Network("fe80::/10"),
    # IPv6 unique local
    ipaddress.IPv6Network("fc00::/7"),
    # Other reserved
    ipaddress.IPv4Network("0.0.0.0/8"),
    ipaddress.IPv4Network("100.64.0.0/10"),  # Carrier-grade NAT
    ipaddress.IPv4Network("192.0.2.0/24"),  # TEST-NET-1
    ipaddress.IPv4Network("198.51.100.0/24"),  # TEST-NET-2
    ipaddress.IPv4Network("203.0.113.0/24"),  # TEST-NET-3
    ipaddress.IPv4Network("224.0.0.0/4"),  # Multicast
    ipaddress.IPv4Network("240.0.0.0/4"),  # Reserved
]


def _is_private_ip(ip_str: str) -> bool:
    """Check if an IP address belongs to a private/reserved network."""
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return True  # Treat unparseable IPs as unsafe

    return any(ip in network for network in _PRIVATE_NETWORKS)


def is_url_safe(url: str, allowed_hosts: list[str] | None = None) -> tuple[bool, str]:
    """Validate a URL against SSRF attacks.

    Returns:
        (is_safe, reason) — is_safe=True means the URL passed all checks.
    """
    if not url:
        return False, "Empty URL"

    try:
        parsed = urlparse(url)
    except Exception:
        return False, "Invalid URL format"

    hostname = parsed.hostname
    if not hostname:
        return False, "No hostname in URL"

    # Block known metadata hostnames
    if hostname.lower() in BLOCKED_METADATA_HOSTNAMES:
        return False, f"Blocked metadata hostname: {hostname}"

    # If allowed_hosts is configured, enforce deny-by-default
    if allowed_hosts:
        if hostname.lower() not in [h.lower() for h in allowed_hosts]:
            return False, f"Hostname '{hostname}' not in allowed list"

    # Resolve hostname and check all resulting IPs
    try:
        addr_infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return False, f"Cannot resolve hostname: {hostname}"

    for _family, _type, _proto, _canonname, sockaddr in addr_infos:
        ip_str = sockaddr[0]
        if _is_private_ip(ip_str):
            return False, f"Resolved to private/reserved IP: {ip_str}"

    return True, "OK"
