"""HTTP Request node plugin with SSRF protection (v0.7.4)."""

import logging
from typing import Any

import aiohttp

from core.ssrf_protection import is_url_safe
from ..base_node import BaseNodePlugin, NodeExecutionContext

logger = logging.getLogger(__name__)


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

    def validate_input(self, input_json: dict[str, Any]) -> None:
        """Validate input before execution."""
        url = input_json.get("url")
        if not url:
            raise ValueError("url is required")

        method = input_json.get("method", "GET").upper()
        if method not in ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"):
            raise ValueError(f"Unsupported HTTP method: {method}")

    async def execute(self, context: NodeExecutionContext) -> dict[str, Any]:
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

        # SSRF protection with comprehensive private IP and hostname validation
        from core.config import settings

        allowed_hosts = None
        if settings.http_allowed_hosts:
            allowed_hosts = [h.strip() for h in settings.http_allowed_hosts.split(",") if h.strip()]

        is_safe, reason = is_url_safe(url, allowed_hosts)
        if not is_safe:
            raise ValueError(f"URL blocked by SSRF protection: {reason}")

        logger.info(f"[{context.run_id}] HTTP {method} {url}")

        # Make the request
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method,
                    url,
                    headers=headers,
                    json=body,
                    timeout=aiohttp.ClientTimeout(total=timeout),
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
