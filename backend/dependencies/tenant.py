"""Tenant dependency."""

from fastapi import Request

from core.config import settings


async def get_tenant_id(request: Request) -> str:
    return getattr(request.state, "tenant_id", None) or settings.default_tenant_id
