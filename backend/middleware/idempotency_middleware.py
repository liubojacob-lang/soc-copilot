"""
Idempotency middleware for preventing duplicate requests.

This middleware checks for Idempotency-Key header and:
1. If key exists and has a stored response, returns the stored response
2. If key is new, stores the response for future requests
"""

import json
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from core.logger import get_logger
from core.token_blacklist import get_idempotency_store
from middleware.trace_middleware import get_trace_id

logger = get_logger(__name__)

# HTTP methods that support idempotency
IDEMPOTENT_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# Paths that should not use idempotency (health checks, etc.)
EXCLUDED_PATHS = {
    "/health",
    "/health/ready",
    "/health/live",
    "/metrics",
    "/docs",
    "/openapi.json",
    "/redoc",
}


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """Middleware for idempotency key handling."""

    def __init__(self, app, header_name: str = "Idempotency-Key"):
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip non-idempotent methods
        if request.method not in IDEMPOTENT_METHODS:
            return await call_next(request)

        # Skip excluded paths
        if request.url.path in EXCLUDED_PATHS:
            return await call_next(request)

        # Skip if no idempotency key
        idempotency_key = request.headers.get(self.header_name)
        if not idempotency_key:
            return await call_next(request)

        # Validate key format (alphanumeric, dashes, underscores, 8-64 chars)
        if not self._validate_key_format(idempotency_key):
            return JSONResponse(
                status_code=400,
                content={
                    "error": "invalid_idempotency_key",
                    "message": "Idempotency key must be 8-64 alphanumeric characters, dashes, or underscores",
                    "trace_id": get_trace_id(),
                },
            )

        # Get user ID from request state (set by auth middleware)
        user_id = getattr(request.state, "user_id", None)
        if not user_id:
            # No authenticated user, proceed without idempotency
            return await call_next(request)

        # Check for existing response
        store = get_idempotency_store()
        existing_response = await store.check_and_set(idempotency_key, user_id)

        if existing_response:
            logger.info(
                f"Returning cached response for idempotency key: {idempotency_key[:8]}..."
            )
            return self._reconstruct_response(existing_response)

        # Process request and store response
        response = await call_next(request)

        # Only store successful responses (2xx status codes)
        if 200 <= response.status_code < 300:
            response_body = b""
            async for chunk in response.body_iterator:
                response_body += chunk

            try:
                response_data = json.loads(response_body.decode())
                await store.set_response(
                    idempotency_key,
                    user_id,
                    {
                        "status_code": response.status_code,
                        "headers": dict(response.headers),
                        "body": response_data,
                    },
                )
                logger.info(
                    f"Stored response for idempotency key: {idempotency_key[:8]}..."
                )
            except (json.JSONDecodeError, UnicodeDecodeError):
                # Non-JSON response, don't cache
                pass

            # Return the response with the body
            return Response(
                content=response_body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )

        return response

    def _validate_key_format(self, key: str) -> bool:
        """Validate idempotency key format."""
        if not (8 <= len(key) <= 64):
            return False
        allowed_chars = set(
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
        )
        return all(c in allowed_chars for c in key)

    def _reconstruct_response(self, cached_data: dict) -> Response:
        """Reconstruct response from cached data."""
        return JSONResponse(
            status_code=cached_data.get("status_code", 200),
            content=cached_data.get("body", {}),
            headers={
                k: v
                for k, v in cached_data.get("headers", {}).items()
                if k.lower() not in ("content-length", "content-encoding")
            },
        )
