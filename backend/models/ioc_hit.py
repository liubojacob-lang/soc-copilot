"""IOC Hit database model."""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from db.session import Base

Base = Base


class IOCHitDB(Base):
    """IOC Hit database model."""

    __tablename__ = "ioc_hits"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=lambda: datetime.now(datetime.UTC), index=True)
    history_id = Column(String, ForeignKey("history.id"), nullable=True, index=True)
    asset_id = Column(String, ForeignKey("assets.id"), nullable=True, index=True)
    ioc_type = Column(String, nullable=False, index=True)
    ioc_value = Column(String, nullable=False, index=True)
    confidence = Column(Integer, default=60)
    source = Column(String, nullable=False)
    context_snippet = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)


# Alias for compatibility
IOCHitModel = IOCHitDB
