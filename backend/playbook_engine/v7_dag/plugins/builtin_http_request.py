"""HTTP Request node plugin with hostname whitelist sandbox (v0.7.4)."""

from typing import Any, Dict
from urllib.parse import urlparse
import logging

import aiohttp

from ..base_node import BaseNodePlugin, NodeExecutionContext

logger = logging.getLogger(__name__)

# Banned hosts that should never be accessible
BANNED_HOSTS = {
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "::1",
    "169.254.169.254",  # AWS metadata service
    "metadata.google.internal",  # GCP metadata service
}


class HttpRequestPlugin(BaseNodePlugin):
    """HTTP request node with hostname whitelist sandbox for security.

    This node makes HTTP requests to external services with built-in
    security controls:
    - Blocks access to localhost/internal addresses
    - Enforces hostname whitelist when configured
    - Supports all HTTP methods and custom headers
    """

    @property
    def node_id(self) -> str:
        return "builtin_http_request"

    @property
    def name(self) -> str:
        return "HTTP Request"

    @property
    def node_type(self) -> str:
        return "action"

    @property
    def description(self) -> str:
        return "Make HTTP requests with hostname whitelist sandbox protection"

    def validate_input(self, input_json: Dict[str, Any]) -> None:
        """Validate input before execution."""
        url = input_json.get("url")
        if not url:
            raise ValueError("url is required")

        method = input_json.get("method", "GET").upper()
        if method not in ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"):
            raise ValueError(f"Unsupported HTTP method: {method}")

    async def execute(self, context: NodeExecutionContext) -> Dict[str, Any]:
        """Execute HTTP request with sandbox validation.

        Args:
            context: Execution context

        Returns:
            Response with status, headers, and body

        Raises:
            ValueError: If URL hostname is blocked or not in whitelist
        """
        url = context.input_json.get("url")
        method = context.input_json.get("method", "GET").upper()
        headers = context.input_json.get("headers", {})
        body = context.input_json.get("body")
        timeout = context.input_json.get("timeout", 30)

        # Sandbox validation
        parsed = urlparse(url)

        # Check against banned hosts
        if parsed.hostname in BANNED_HOSTS:
            raise ValueError(
                f"Access to '{parsed.hostname}' is blocked by security policy. "
                f"Cannot make requests to localhost or internal addresses."
            )

        # Check hostname whitelist if configured
        from core.config import settings
        allowed_hosts = settings.http_allowed_hosts.split(",") if settings.http_allowed_hosts else []

        if allowed_hosts and allowed_hosts != [""]:
            # Remove empty strings from split
            allowed_hosts = [h.strip() for h in allowed_hosts if h.strip()]

            if allowed_hosts and parsed.hostname not in allowed_hosts:
                raise ValueError(
                    f"Host '{parsed.hostname}' is not in the allowed hosts list. "
                    f"Allowed hosts: {', '.join(allowed_hosts)}"
                )

        logger.info(f"[{context.run_id}] HTTP {method} {url}")

        # Make the request
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method,
                    url,
                    headers=headers,
                    json=body,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:
                    response_body = await response.text()
                    response_headers = dict(response.headers)

                    logger.info(
                        f"[{context.run_id}] HTTP response: "
                        f"{response.status} {len(response_body)} bytes"
                    )

                    return {
                        "status": "success",
                        "status_code": response.status,
                        "headers": response_headers,
                        "body": response_body,
                        "url": url,
                        "method": method,
                    }

        except aiohttp.ClientError as e:
            logger.error(f"[{context.run_id}] HTTP request failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "url": url,
                "method": method,
            }

    def get_required_secrets(self) -> list[str]:
        """Declare secrets that may be used in headers/auth."""
        # Secrets for API keys, tokens, etc.
        return []
