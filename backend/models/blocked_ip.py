"""Blocked IP model for threat response."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, Index, String, Text

from db.session import Base


class BlockedIP(Base):
    """Model for blocked IPs/domains for threat response."""

    __tablename__ = "blocked_ips"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    value = Column(String(255), nullable=False, index=True)
    type = Column(String(20), nullable=False, default="ip")
    reason = Column(Text, nullable=True)
    source = Column(String(50), nullable=False, default="manual")
    created_by = Column(String(100), nullable=False)
    alert_id = Column(String(100), nullable=True, index=True)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    deactivated_at = Column(DateTime, nullable=True)
    deactivated_by = Column(String(100), nullable=True)

    __table_args__ = (
        Index("ix_blocked_ip_value_type", "value", "type"),
        Index("ix_blocked_ip_active_created", "is_active", "created_at"),
    )
