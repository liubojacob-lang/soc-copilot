"""Tenant-aware query helpers and redis key namespace."""

from __future__ import annotations

from sqlalchemy import Select


def with_tenant_scope(query: Select, model, tenant_id: str):
    """Apply tenant isolation filter to SQLAlchemy query."""
    if hasattr(model, "tenant_id"):
        return query.where(model.tenant_id == tenant_id)
    return query


def redis_tenant_key(tenant_id: str, key: str) -> str:
    """Create tenant-prefixed redis key."""
    return f"tenant:{tenant_id}:{key}"
