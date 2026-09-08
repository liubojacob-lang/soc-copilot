"""
Message Queue Models for Offline Message Caching

This module defines the data models for caching WebSocket messages
when clients are offline, using Redis as the backend store.

Key Features:
- Message queuing per user
- TTL-based expiration (24 hours default)
- Queue size limits (1000 messages per user)
- Automatic cleanup of expired messages
"""

import json
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """WebSocket message types"""

    ALERT = "alert"
    AGGREGATED_ALERT = "aggregated_alert"
    PLAYBOOK_RUN = "playbook_run"
    SYSTEM = "system"
    PING = "ping"
    PONG = "pong"


class QueuedMessage(BaseModel):
    """A queued message for offline client"""

    id: str = Field(default_factory=lambda: f"msg_{datetime.now(UTC).timestamp()}")
    type: MessageType
    data: dict[str, Any]
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    channel: str = "alerts"
    ttl_seconds: int = Field(
        default=86400, description="Time to live in seconds (default 24 hours)"
    )

    def to_json(self) -> str:
        """Convert to JSON for storage"""
        return self.model_dump_json(exclude_none=True)

    @classmethod
    def from_json(cls, json_str: str) -> "QueuedMessage":
        """Create from JSON string"""
        data = json.loads(json_str)
        return cls(**data)


class UserQueue(BaseModel):
    """Message queue metadata for a user"""

    user_id: str
    message_count: int = 0
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    last_updated: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    max_size: int = Field(default=1000, description="Maximum messages in queue")
    ttl_seconds: int = Field(default=86400, description="Queue TTL in seconds")

    def is_full(self) -> bool:
        """Check if queue is at capacity"""
        return self.message_count >= self.max_size

    def add_message(self) -> bool:
        """Increment message count, return False if full"""
        if self.is_full():
            return False
        self.message_count += 1
        self.last_updated = datetime.now(UTC).isoformat()
        return True

    def remove_messages(self, count: int) -> int:
        """Remove messages and return actual count removed"""
        actual = min(count, self.message_count)
        self.message_count -= actual
        self.last_updated = datetime.now(UTC).isoformat()
        return actual


class QueueStats(BaseModel):
    """Statistics for a user's message queue"""

    user_id: str
    message_count: int
    queue_size_bytes: int | None = None
    oldest_message_age_seconds: float | None = None
    newest_message_age_seconds: float | None = None
    is_full: bool = False

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user123",
                "message_count": 42,
                "queue_size_bytes": 42000,
                "oldest_message_age_seconds": 3600,
                "newest_message_age_seconds": 60,
                "is_full": False,
            }
        }


class MessageQueueConfig(BaseModel):
    """Configuration for the message queue service"""

    redis_url: str = Field(default="redis://localhost:6379/0")
    default_ttl_seconds: int = Field(
        default=86400, description="Default message TTL (24 hours)"
    )
    max_queue_size: int = Field(default=1000, description="Max messages per user queue")
    cleanup_interval_seconds: int = Field(
        default=3600, description="Cleanup interval (1 hour)"
    )

    # Redis keys
    KEY_PREFIX: str = Field(default="ws:queue")
    META_SUFFIX: str = Field(default=":meta")

    def get_queue_key(self, user_id: str) -> str:
        """Get Redis key for user's message queue"""
        return f"{self.KEY_PREFIX}:{user_id}"

    def get_meta_key(self, user_id: str) -> str:
        """Get Redis key for user's queue metadata"""
        return f"{self.KEY_PREFIX}:{user_id}{self.META_SUFFIX}"
