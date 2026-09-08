"""HTTP request executor with SSRF protection."""

import ipaddress
import socket
from typing import Any
from urllib.parse import urlparse

import aiohttp

from .executor_base import BaseExecutor, ExecutorContext

# Private IP ranges that should be blocked
PRIVATE_IP_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),  # Private Class A
    ipaddress.ip_network("172.16.0.0/12"),  # Private Class B
    ipaddress.ip_network("192.168.0.0/16"),  # Private Class C
    ipaddress.ip_network("127.0.0.0/8"),  # Loopback
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local
    ipaddress.ip_network("0.0.0.0/8"),  # Current network
    ipaddress.ip_network("224.0.0.0/4"),  # Multicast
    ipaddress.ip_network("240.0.0.0/4"),  # Reserved
    ipaddress.ip_network("::1/128"),  # IPv6 loopback
    ipaddress.ip_network("fe80::/10"),  # IPv6 link-local
    ipaddress.ip_network("fc00::/7"),  # IPv6 unique local
]


def is_private_ip(ip_str: str) -> bool:
    """Check if an IP address is private/internal."""
    try:
        ip = ipaddress.ip_address(ip_str)
        return any(ip in network for network in PRIVATE_IP_RANGES)
    except ValueError:
        return False


def resolve_hostname(hostname: str) -> list[str]:
    """Resolve hostname to IP addresses."""
    try:
        # Get all IP addresses for the hostname
        addr_info = socket.getaddrinfo(hostname, None)
        ips = set()
        for family, _, _, _, sockaddr in addr_info:
            if family in (socket.AF_INET, socket.AF_INET6):
                ips.add(sockaddr[0])
        return list(ips)
    except socket.gaierror:
        return []


def validate_url(url: str) -> tuple[bool, str]:
    """Validate URL for SSRF protection.

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        parsed = urlparse(url)

        # Only allow http and https
        if parsed.scheme not in ("http", "https"):
            return (
                False,
                f"Protocol '{parsed.scheme}' is not allowed. Only http and https are permitted.",
            )

        # Must have a hostname
        if not parsed.hostname:
            return False, "URL must have a hostname"

        hostname = parsed.hostname.lower()

        # Block if hostname looks like an IP address directly
        try:
            ip = ipaddress.ip_address(hostname)
            if is_private_ip(str(ip)):
                return False, "Access to private/internal IP addresses is not allowed"
        except ValueError:
            pass  # Not an IP address, continue with hostname resolution

        # Resolve hostname and check all IPs
        resolved_ips = resolve_hostname(hostname)

        if not resolved_ips:
            # Could not resolve - this might be intentional blocking
            return False, f"Could not resolve hostname: {hostname}"

        for ip_str in resolved_ips:
            if is_private_ip(ip_str):
                return False, f"Hostname resolves to private IP: {ip_str}"

        return True, ""

    except Exception as e:
        return False, f"Invalid URL: {e!s}"


class HttpRequestExecutor(BaseExecutor):
    """Executor for making HTTP requests with SSRF protection."""

    async def execute(self, context: ExecutorContext) -> dict[str, Any]:
        """Execute HTTP request with SSRF protection."""
        config = context.node_def.get("config", {})

        url = config.get("url")
        method = config.get("method", "GET").upper()
        headers = config.get("headers", {})
        body = config.get("body")
        timeout = config.get("timeout", 30)  # Default 30 second timeout

        if not url:
            return {
                "status": "error",
                "error": "No URL provided",
            }

        # Resolve URL template
        url = self._resolve_template(url, context)

        # Validate URL for SSRF protection
        is_valid, error_msg = validate_url(url)
        if not is_valid:
            return {
                "status": "error",
                "error": f"URL validation failed: {error_msg}",
            }

        try:
            timeout_obj = aiohttp.ClientTimeout(total=timeout)

            async with aiohttp.ClientSession(timeout=timeout_obj) as session:
                if method == "GET":
                    async with session.get(url, headers=headers) as response:
                        response_text = await response.text()
                        return {
                            "status": "success",
                            "status_code": response.status,
                            "body": response_text,
                        }
                elif method == "POST":
                    async with session.post(
                        url, headers=headers, json=body
                    ) as response:
                        response_text = await response.text()
                        return {
                            "status": "success",
                            "status_code": response.status,
                            "body": response_text,
                        }
                elif method == "PUT":
                    async with session.put(url, headers=headers, json=body) as response:
                        response_text = await response.text()
                        return {
                            "status": "success",
                            "status_code": response.status,
                            "body": response_text,
                        }
                elif method == "DELETE":
                    async with session.delete(url, headers=headers) as response:
                        response_text = await response.text()
                        return {
                            "status": "success",
                            "status_code": response.status,
                            "body": response_text,
                        }
                else:
                    return {
                        "status": "error",
                        "error": f"Unsupported method: {method}",
                    }

        except TimeoutError:
            return {
                "status": "error",
                "error": f"Request timed out after {timeout} seconds",
            }
        except aiohttp.ClientError as e:
            return {
                "status": "error",
                "error": f"HTTP client error: {e!s}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }
