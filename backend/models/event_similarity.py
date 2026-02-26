"""Event similarity cache model."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Float, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column

from db.session import Base


class EventSimilarity(Base):
    """Cache for computed event similarities.

    Stores similarity scores between event pairs to avoid
    redundant computation. TTL-based auto-cleanup.
    """

    __tablename__ = "event_similarities"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    event_id_1: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True
    )

    event_id_2: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True
    )

    similarity_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="Similarity score (0-1)"
    )

    # Method used to compute similarity
    method: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="jaccard, cosine, embedding, or rule_based"
    )

    # Cache TTL
    created_at: Mapped[str] = mapped_column(
        String(50),
        default=lambda: datetime.now(timezone.utc).isoformat(),
        index=True
    )

    ttl_seconds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3600,
        doc="Time-to-live in seconds (default: 1 hour)"
    )

    # Indexes
    __table_args__ = (
        Index('idx_event_similarities_event_pair', 'event_id_1', 'event_id_2'),
        Index('idx_event_similarities_created_at', 'created_at'),
    )
