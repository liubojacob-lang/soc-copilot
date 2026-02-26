"""Tenant context middleware."""

from __future__ import annotations

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class TenantMiddleware(BaseHTTPMiddleware):
    """Inject tenant_id into request.state from header or fallback default."""

    async def dispatch(self, request: Request, call_next):
        tenant_id = request.headers.get("x-tenant-id", "default")
        request.state.tenant_id = tenant_id
        response = await call_next(request)
        response.headers["x-tenant-id"] = tenant_id
        return response
