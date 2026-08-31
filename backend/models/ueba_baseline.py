"""UEBA Baseline model for persisting user behavior baselines and ML models."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, LargeBinary, String, Float, Integer, Text

from db.session import Base


class UEBABaselineModel(Base):
    """Persisted UEBA baseline for a user or entity.

    Stores:
    - Behavior feature vectors extracted from audit_logs and security_alerts
    - Serialized IsolationForest model for the user
    - Training metadata
    """

    __tablename__ = "ueba_baselines"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(64), nullable=False, index=True, unique=True)
    entity_type = Column(String(20), nullable=False, default="user")

    # Serialized IsolationForest model (pickle bytes)
    model_data = Column(LargeBinary, nullable=True)

    # Aggregated behavior features (JSON-encoded)
    # Structure: {"login_count": N, "login_failures": N, ...}
    features_json = Column(Text, nullable=True)

    # Summary metrics
    anomaly_threshold = Column(Float, nullable=True)
    training_samples = Column(Integer, nullable=False, default=0)

    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    def __repr__(self) -> str:
        return f"<UEBABaseline(id={self.id}, user_id={self.user_id}, samples={self.training_samples})>"
