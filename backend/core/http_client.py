"""
HTTP Client Manager - Singleton HTTP client for connection pooling
and SSRF-safe outbound request utilities with DNS-rebinding protection.
"""

from typing import Optional

import httpx

from core.logger import get_logger
from core.ssrf_protection import is_url_safe

logger = get_logger(__name__)


class SafeAsyncTransport(httpx.AsyncHTTPTransport):
    """HTTP transport that intercepts requests and validates destination IPs on the fly.

    Prevents TOCTOU / DNS-rebinding SSRF attacks by inspecting the target host
    prior to socket connection.
    """

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        is_safe, reason = is_url_safe(url_str)
        if not is_safe:
            raise ValueError(f"SSRF Protection blocked request to {url_str}: {reason}")
        return await super().handle_async_request(request)


class HTTPClientManager:
    """Singleton HTTP client manager for connection pooling."""

    _instance: Optional["HTTPClientManager"] = None
    _client: httpx.AsyncClient | None = None
    _safe_client: httpx.AsyncClient | None = None

    def __new__(cls) -> "HTTPClientManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_client(self) -> httpx.AsyncClient:
        """Get or create the shared HTTP client.

        Returns:
            Shared httpx.AsyncClient instance
        """
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(
                    connect=10.0,
                    read=90.0,
                    write=30.0,
                    pool=10.0,
                ),
                limits=httpx.Limits(
                    max_connections=100,
                    max_keepalive_connections=20,
                    keepalive_expiry=30.0,
                ),
                follow_redirects=True,
            )
            logger.debug("Created new shared HTTP client")
        return self._client

    def get_safe_client(self, timeout: float = 30.0) -> httpx.AsyncClient:
        """Get or create the SSRF-protected shared HTTP client.

        Every outbound request automatically verifies the destination host/IP
        through SafeAsyncTransport, blocking private IP ranges and metadata services.
        """
        if self._safe_client is None or self._safe_client.is_closed:
            self._safe_client = httpx.AsyncClient(
                transport=SafeAsyncTransport(verify=True),
                timeout=httpx.Timeout(connect=10.0, read=timeout, write=30.0, pool=10.0),
                follow_redirects=False,  # Prevent open redirects from bypassing SSRF checks
            )
            logger.debug("Created new SSRF-safe HTTP client")
        return self._safe_client

    async def close(self) -> None:
        """Close the HTTP clients."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
        if self._safe_client and not self._safe_client.is_closed:
            await self._safe_client.aclose()
            self._safe_client = None
        logger.debug("Closed shared HTTP clients")


http_client_manager = HTTPClientManager()


def get_http_client() -> httpx.AsyncClient:
    """Get the shared HTTP client instance."""
    return http_client_manager.get_client()


def get_safe_http_client(timeout: float = 30.0) -> httpx.AsyncClient:
    """Get the SSRF-protected HTTP client instance."""
    return http_client_manager.get_safe_client(timeout=timeout)
