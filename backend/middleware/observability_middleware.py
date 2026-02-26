"""Middleware for API observability metrics."""

from __future__ import annotations

import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from observability.metrics import observe_api_request


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Record API request metrics for all routes."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.perf_counter()
        path = request.url.path
        method = request.method
        tenant_id = getattr(request.state, "tenant_id", request.headers.get("x-tenant-id", "default"))

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            status_code = 500
            raise
        finally:
            elapsed = time.perf_counter() - start
            observe_api_request(method, path, status_code, tenant_id, elapsed)

        return response
