"""Monitor history model for storing system metrics over time."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Float, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from db.session import Base


class MonitorHistoryModel(Base):
    """Model for storing system monitoring metrics history.

    Stores CPU, memory, disk usage and service health status at regular intervals.
    Designed for time-series data with efficient querying.
    """

    __tablename__ = "monitor_history"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # Timestamp with timezone
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        index=True,
        nullable=False,
    )

    # Resource metrics
    cpu_percent: Mapped[float] = mapped_column(Float, nullable=False)
    memory_percent: Mapped[float] = mapped_column(Float, nullable=False)
    memory_used_gb: Mapped[float] = mapped_column(Float, nullable=False)
    memory_total_gb: Mapped[float] = mapped_column(Float, nullable=False)
    disk_percent: Mapped[float] = mapped_column(Float, nullable=False)
    disk_used_gb: Mapped[float] = mapped_column(Float, nullable=False)
    disk_total_gb: Mapped[float] = mapped_column(Float, nullable=False)

    # Service statuses (stored as JSON for flexibility)
    services: Mapped[dict] = mapped_column(JSON, nullable=False, default=lambda: {})

    # Request metrics
    requests_per_minute: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    avg_response_time_ms: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False
    )

    # Composite index for efficient time-range queries
    __table_args__ = (Index("idx_monitor_history_timestamp", "timestamp"),)
