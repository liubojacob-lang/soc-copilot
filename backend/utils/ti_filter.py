"""IOC external transmission filter for compliance.

Only IOCs that pass compliance checks are sent to external TI services.
"""

import ipaddress
import re
from dataclasses import dataclass


@dataclass
class FilterDecision:
    """Filter decision for IOC external transmission.

    Attributes:
        allowed: Whether the IOC is allowed to be sent to external TI
        reason: Reason for filtering (if not allowed)
    """

    allowed: bool
    reason: str | None = None


def is_private_ip(ip: str) -> bool:
    """Check if IP address is private/reserved.

    Args:
        ip: IP address string

    Returns:
        True if IP is private, loopback, link-local, or reserved
    """
    try:
        obj = ipaddress.ip_address(ip.strip())
        return obj.is_private or obj.is_loopback or obj.is_link_local or obj.is_reserved
    except Exception:
        return False


def extract_host_from_url(url: str) -> str | None:
    """Extract hostname from URL.

    Args:
        url: URL string

    Returns:
        Extracted hostname in lowercase, or None if invalid
    """
    if not url:
        return None

    url = url.strip()

    # Support http/https
    m = re.match(r"^https?://([^/]+)", url, flags=re.IGNORECASE)
    if m:
        host = m.group(1)
        # Handle userinfo@host format
        host = host.split("@")[-1]
        # Handle port
        host = host.split(":")[0]
        return host.lower().strip()

    return None


def matches_internal_domain(host: str, internal_suffixes: list[str]) -> bool:
    """Check if hostname matches internal domain suffixes.

    Args:
        host: Hostname string
        internal_suffixes: List of domain suffixes (e.g., ["corp.example.com"])

    Returns:
        True if host matches an internal domain
    """
    if not internal_suffixes:
        return False

    h = host.lower().strip(".")
    for suf in internal_suffixes:
        if not suf:
            continue
        s = suf.lower().strip(".")
        if h == s or h.endswith("." + s):
            return True
    return False


def has_blocked_tld(host: str, blocked_tlds: list[str]) -> bool:
    """Check if hostname has a blocked TLD.

    Args:
        host: Hostname string
        blocked_tlds: List of blocked TLDs (e.g., ["local", "lan", "internal"])

    Returns:
        True if TLD is in blocked list
    """
    if not blocked_tlds:
        return False

    h = host.lower().strip(".")
    parts = h.split(".")
    if len(parts) < 2:
        return True

    tld = parts[-1]
    blocked_set = {x.lower().strip() for x in blocked_tlds if x.strip()}
    return tld in blocked_set


def should_send_ioc_to_external_ti(
    ioc_type: str,
    ioc_value: str,
    *,
    allow_private_ip: bool = False,
    internal_domain_suffixes: list[str] | None = None,
    blocked_tlds: list[str] | None = None,
    allow_url_with_private_host: bool = False,
) -> FilterDecision:
    """Determine if IOC should be sent to external TI service.

    Args:
        ioc_type: IOC type (ip/domain/url/hash)
        ioc_value: IOC value
        allow_private_ip: Whether to allow private IPs
        internal_domain_suffixes: Internal domain suffixes to block
        blocked_tlds: Blocked TLDs
        allow_url_with_private_host: Whether URLs with private IP hosts are allowed

    Returns:
        FilterDecision with allowed flag and optional reason
    """
    t = (ioc_type or "").lower().strip()
    v = (ioc_value or "").strip()

    # Empty value
    if not v:
        return FilterDecision(False, "empty_value")

    # Normalize optional lists
    internal_domain_suffixes = internal_domain_suffixes or []
    blocked_tlds = blocked_tlds or []

    # IP address
    if t == "ip":
        if is_private_ip(v) and not allow_private_ip:
            return FilterDecision(False, "private_ip")
        return FilterDecision(True, None)

    # Domain
    if t == "domain":
        host = v.lower().strip(".")
        # Check internal domains
        if matches_internal_domain(host, internal_domain_suffixes):
            return FilterDecision(False, "internal_domain")
        # Check blocked TLDs
        if has_blocked_tld(host, blocked_tlds):
            return FilterDecision(False, "blocked_tld")
        return FilterDecision(True, None)

    # URL
    if t == "url":
        host = extract_host_from_url(v)
        if not host:
            return FilterDecision(False, "invalid_url")

        # Check if host is an IP
        if re.fullmatch(r"\d+\.\d+\.\d+\.\d+", host):
            if is_private_ip(host) and not allow_url_with_private_host:
                return FilterDecision(False, "url_private_ip_host")
            return FilterDecision(True, None)

        # Check internal domains
        if matches_internal_domain(host, internal_domain_suffixes):
            return FilterDecision(False, "url_internal_domain")
        # Check blocked TLDs
        if has_blocked_tld(host, blocked_tlds):
            return FilterDecision(False, "url_blocked_tld")
        return FilterDecision(True, None)

    # File hash - always allowed (still subject to global switch)
    if t == "hash":
        return FilterDecision(True, None)

    # Unsupported type
    return FilterDecision(False, "unsupported_type")
