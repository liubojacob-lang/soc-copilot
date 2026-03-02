"""
Alert Note database model.

Stores user notes and comments on security alerts.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship

from db.session import Base


class AlertNoteModel(Base):
    """Alert Note model for storing user comments on alerts."""

    __tablename__ = "alert_notes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Foreign key to security alert
    alert_id = Column(Integer, ForeignKey("security_alerts.id", ondelete="CASCADE"), nullable=False, index=True)

    # User information
    user_id = Column(String(255), nullable=False, index=True)
    username = Column(String(255), nullable=False)

    # Note content
    content = Column(Text, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    alert = relationship("SecurityAlert", back_populates="notes")
