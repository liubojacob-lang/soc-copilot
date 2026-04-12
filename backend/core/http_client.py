"""
HTTP Client Manager - Singleton HTTP client for connection pooling
"""

from typing import Optional

import httpx

from core.logger import get_logger

logger = get_logger(__name__)


class HTTPClientManager:
    """Singleton HTTP client manager for connection pooling."""

    _instance: Optional["HTTPClientManager"] = None
    _client: httpx.AsyncClient | None = None

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

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
            logger.debug("Closed shared HTTP client")


http_client_manager = HTTPClientManager()


def get_http_client() -> httpx.AsyncClient:
    """Get the shared HTTP client instance.

    Returns:
        Shared httpx.AsyncClient instance
    """
    return http_client_manager.get_client()
