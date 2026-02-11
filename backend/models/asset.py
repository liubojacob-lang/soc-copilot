"""Asset database model."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Text, Integer, DateTime
from sqlalchemy.orm import declarative_base

from db.session import Base

Base = Base


class AssetDB(Base):
    """Asset database model."""

    __tablename__ = "assets"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
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
