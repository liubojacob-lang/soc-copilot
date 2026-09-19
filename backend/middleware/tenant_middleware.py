"""Tenant context middleware."""

from __future__ import annotations

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from core.config import settings


def resolve_tenant_id(request: Request) -> str:
    """Single source of truth for the request tenant.

    The ``x-tenant-id`` header is deliberately ignored: it is attacker-controlled
    and there is no tenant model to authorise it against yet, so honouring it
    only let clients mislabel their own logs and metrics. Derive the tenant from
    the authenticated user here once real tenancy lands.
    """
    return getattr(request.state, "tenant_id", None) or settings.default_tenant_id


class TenantMiddleware(BaseHTTPMiddleware):
    """Pin ``request.state.tenant_id`` to the configured deployment tenant."""

    async def dispatch(self, request: Request, call_next):
        tenant_id = resolve_tenant_id(request)
        request.state.tenant_id = tenant_id
        response = await call_next(request)
        response.headers["x-tenant-id"] = tenant_id
        return response
