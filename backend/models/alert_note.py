"""
Alert Note database model.

Stores user notes and comments on security alerts.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from db.session import Base


class AlertNoteModel(Base):
    """Alert Note model for storing user comments on alerts."""

    __tablename__ = "alert_notes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Foreign key to security alert
    alert_id = Column(
        Integer,
        ForeignKey("security_alerts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # User information
    user_id = Column(String(255), nullable=False, index=True)
    username = Column(String(255), nullable=False)

    # Note content
    content = Column(Text, nullable=False)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    alert = relationship("SecurityAlert", back_populates="notes")
