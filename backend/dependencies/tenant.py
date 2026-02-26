"""Tenant dependencies."""

from fastapi import Request


async def get_tenant_id(request: Request) -> str:
    return getattr(request.state, "tenant_id", "default")
