"""Threat Intelligence Cache database model."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, DateTime, Index
from sqlalchemy.orm import declarative_base

from db.session import Base

Base = Base


class ThreatIntelCacheDB(Base):
    """Threat Intelligence Cache database model."""

    __tablename__ = "threat_intel_cache"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    provider = Column(String, nullable=False, index=True)  # e.g., "otx"
    ioc_type = Column(String, nullable=False, index=True)  # ip/domain/url/hash
    ioc_value = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False)  # ok/not_found/error
    response_json = Column(Text, nullable=True)  # Full response as JSON
    score = Column(Integer, nullable=True)  # 0-100
    tags = Column(Text, nullable=True)  # JSON array
    pulse_count = Column(Integer, nullable=True)
    last_seen = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    error_reason = Column(Text, nullable=True)

    __table_args__ = (
        Index('ix_ti_provider_ioc', 'provider', 'ioc_type', 'ioc_value', unique=True),
    )


# Alias for compatibility
ThreatIntelCacheModel = ThreatIntelCacheDB
