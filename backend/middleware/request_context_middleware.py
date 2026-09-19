"""Request context middleware for request_id/trace_id propagation."""

from __future__ import annotations

import uuid
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from core.logger import clear_request_context, set_request_context
from middleware.tenant_middleware import resolve_tenant_id
from middleware.trace_middleware import get_trace_id
from observability.context import clear_context, set_context


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Populate request context for logging and observability correlation."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = (
            request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex[:24]}"
        )
        trace_id = (
            getattr(request.state, "trace_id", None)
            or request.headers.get("X-Trace-ID")
            or get_trace_id()
            or ""
        )
        tenant_id = resolve_tenant_id(request)

        user_id = getattr(request.state, "user_id", "")
        user_role = getattr(request.state, "user_role", "")

        set_context(request_id=request_id, trace_id=trace_id, tenant_id=tenant_id)
        set_request_context(
            request_id=request_id,
            user_id=user_id,
            user_role=user_role,
            trace_id=trace_id,
            tenant_id=tenant_id,
        )

        try:
            response = await call_next(request)
        finally:
            clear_context()
            clear_request_context()

        response.headers["X-Request-ID"] = request_id
        if trace_id:
            response.headers["X-Trace-ID"] = trace_id
        return response
