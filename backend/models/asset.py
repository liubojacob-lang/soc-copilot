"""Asset database model."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, String, Text

from db.session import Base

Base = Base


class AssetDB(Base):
    """Asset database model."""

    __tablename__ = "assets"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    deleted_at = Column(
        DateTime(timezone=True), nullable=True, index=True
    )  # v1.1: soft delete
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )
    hostname = Column(String, unique=True, nullable=True, index=True)
    ip = Column(String, unique=True, nullable=True, index=True)
    owner = Column(String, nullable=True)
    business = Column(String, nullable=True)
    criticality = Column(String, default="medium")
    tags = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)


# Alias for compatibility
AssetModel = AssetDB
