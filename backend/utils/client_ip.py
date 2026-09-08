"""Client IP resolution that is safe behind a trusted reverse proxy.

nginx overwrites ``X-Real-IP`` with ``$remote_addr`` and APPENDS the peer
address to ``X-Forwarded-For``, so the trustworthy values are ``X-Real-IP``
and the RIGHTMOST ``X-Forwarded-For`` entry. The leftmost entry is fully
client-controlled and must never be used for security decisions (rate
limiting buckets, audit attribution).
"""

import ipaddress

from fastapi import Request


def _is_valid_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(value.strip())
    except ValueError:
        return False
    return True


def get_client_ip(request: Request) -> str:
    """Resolve the real client IP from a request behind our nginx proxy."""
    real_ip = request.headers.get("x-real-ip")
    if real_ip and _is_valid_ip(real_ip):
        return real_ip.strip()

    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # Rightmost entry is the one our own proxy appended; walk right-to-left
        # and skip anything malformed or empty.
        for candidate in reversed(forwarded.split(",")):
            candidate = candidate.strip()
            if candidate and _is_valid_ip(candidate):
                return candidate

    return request.client.host if request.client else "unknown"
