"""AI Task model for background processing."""

from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import Column, String, Text, DateTime, JSON, Integer
from sqlalchemy.sql import func

from db.session import Base


class AITaskStatus(str, Enum):
    """AI task status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class AITaskType(str, Enum):
    """AI task type enumeration."""
    ALERT_ANALYSIS = "alert_analysis"
    TIMELINE_ANALYSIS = "timeline_analysis"
    REPORT_GENERATION = "report_generation"
    CHAT_COMPLETION = "chat_completion"
    IOC_ANALYSIS = "ioc_analysis"


class AITaskModel(Base):
    """Model for AI background tasks."""
    __tablename__ = "ai_tasks"

    id = Column(String(36), primary_key=True)
    task_type = Column(String(50), nullable=False, index=True)
    status = Column(String(20), nullable=False, default=AITaskStatus.PENDING.value, index=True)
    
    # Input data
    input_data = Column(JSON, nullable=True)
    prompt = Column(Text, nullable=True)
    model_id = Column(String(100), nullable=True)
    provider = Column(String(50), nullable=True)
    
    # Output data
    result = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Timing
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    timeout_seconds = Column(Integer, default=300)  # 5 minutes default
    
    # Ownership
    user_id = Column(String(36), nullable=True, index=True)
    request_id = Column(String(36), nullable=True)
    
    # Retry info
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=2)
    
    # Priority (higher = more urgent)
    priority = Column(Integer, default=0)
    
    def __repr__(self):
        return f"<AITask {self.id} type={self.task_type} status={self.status}>"
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "task_type": self.task_type,
            "status": self.status,
            "input_data": self.input_data,
            "result": self.result,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "user_id": self.user_id,
            "retry_count": self.retry_count,
        }
    
    @property
    def is_terminal(self) -> bool:
        """Check if task is in terminal state."""
        return self.status in [
            AITaskStatus.COMPLETED.value,
            AITaskStatus.FAILED.value,
            AITaskStatus.TIMEOUT.value,
        ]
    
    @property
    def elapsed_seconds(self) -> float:
        """Get elapsed time in seconds since creation."""
        if self.started_at:
            end = self.completed_at or datetime.now(timezone.utc)
            return (end - self.started_at).total_seconds()
        return 0.0
    
    @property
    def is_timeout(self) -> bool:
        """Check if task has timed out."""
        if self.status == AITaskStatus.PROCESSING.value:
            return self.elapsed_seconds > self.timeout_seconds
        return False
