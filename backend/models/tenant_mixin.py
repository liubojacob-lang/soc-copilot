"""Tenant-aware model mixin (P2 preparation)."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column


class TenantMixin:
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True, default="default")
