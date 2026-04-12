"""
Message Queue Service for Offline Message Caching

This service provides offline message caching for WebSocket clients using Redis.
When a client disconnects, messages are queued. When they reconnect, queued
messages are sent automatically.

Features:
- Redis-based message queue
- Per-user queue with size limits
- TTL-based message expiration
- Automatic cleanup
- Queue statistics
"""

import asyncio
from datetime import UTC, datetime
from typing import Any

try:
    import redis
    from redis.asyncio import Redis as AsyncRedis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from core.logger import get_logger
from models.message_queue import (
    MessageQueueConfig,
    MessageType,
    QueuedMessage,
    QueueStats,
    UserQueue,
)

logger = get_logger(__name__)


class MessageQueueService:
    """
    Service for managing offline message queues in Redis.

    Architecture:
    - Each user has a dedicated queue: ws:queue:{user_id}
    - Queue metadata: ws:queue:{user_id}:meta
    - Messages stored as Redis list
    - TTL set on individual messages and queue metadata
    """

    def __init__(self, config: MessageQueueConfig | None = None):
        self.config = config or MessageQueueConfig()
        self._redis: AsyncRedis | None = None
        self._cleanup_task: asyncio.Task | None = None

    async def start(self):
        """Initialize Redis connection and start cleanup task"""
        if not REDIS_AVAILABLE:
            logger.warning("Redis not available, message queue disabled")
            return

        try:
            self._redis = AsyncRedis.from_url(
                self.config.redis_url, encoding="utf-8", decode_responses=True
            )

            # Test connection
            await self._redis.ping()
            logger.info(f"Message queue service started: {self.config.redis_url}")

            # Start cleanup task
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._redis = None

    async def stop(self):
        """Stop the service and cleanup resources"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        if self._redis:
            await self._redis.close()
            logger.info("Message queue service stopped")

    async def is_available(self) -> bool:
        """Check if Redis is available"""
        if not self._redis:
            return False
        try:
            await self._redis.ping()
            return True
        except Exception:
            return False

    async def push_message(
        self,
        user_id: str,
        message_type: MessageType,
        data: dict[str, Any],
        channel: str = "alerts",
    ) -> bool:
        """
        Push a message to user's queue.

        Args:
            user_id: User identifier
            message_type: Type of message (alert, aggregated_alert, etc.)
            data: Message data
            channel: Channel name

        Returns:
            True if message was queued, False if queue is full or error
        """
        if not await self.is_available():
            logger.warning("Redis not available, cannot queue message")
            return False

        try:
            # Get or create queue metadata
            queue_key = self.config.get_queue_key(user_id)
            meta_key = self.config.get_meta_key(user_id)

            # Check if queue exists
            meta_json = await self._redis.get(meta_key)
            if meta_json:
                queue_meta = UserQueue.model_validate_json(meta_json)
                if queue_meta.is_full():
                    logger.debug(f"Queue full for user {user_id}")
                    return False
            else:
                # Create new queue metadata with configured max_size
                queue_meta = UserQueue(user_id=user_id, max_size=self.config.max_queue_size)

            # Create queued message
            queued_msg = QueuedMessage(
                type=message_type,
                data=data,
                channel=channel,
                ttl_seconds=self.config.default_ttl_seconds,
            )

            # Push to queue (rpush for FIFO ordering)
            await self._redis.rpush(queue_key, queued_msg.to_json())

            # Update metadata
            if queue_meta.add_message():
                await self._redis.setex(
                    meta_key, self.config.default_ttl_seconds, queue_meta.model_dump_json()
                )
                # Set TTL on queue key to match metadata
                await self._redis.expire(queue_key, self.config.default_ttl_seconds)

            logger.debug(f"Queued message for user {user_id}: {message_type}")
            return True

        except Exception as e:
            logger.error(f"Error pushing message for user {user_id}: {e}")
            return False

    async def get_messages(self, user_id: str, count: int | None = None) -> list[QueuedMessage]:
        """
        Get queued messages for a user.

        Args:
            user_id: User identifier
            count: Maximum number of messages to retrieve (None = all)

        Returns:
            List of queued messages
        """
        if not await self.is_available():
            return []

        try:
            queue_key = self.config.get_queue_key(user_id)
            meta_key = self.config.get_meta_key(user_id)

            # Get messages
            if count:
                messages_json = await self._redis.lrange(queue_key, 0, count - 1)
            else:
                messages_json = await self._redis.lrange(queue_key, 0, -1)

            messages = [QueuedMessage.from_json(msg) for msg in messages_json]

            # Clear queue if messages retrieved
            if messages:
                await self._redis.delete(queue_key)
                await self._redis.delete(meta_key)

            logger.info(f"Retrieved {len(messages)} queued messages for user {user_id}")
            return messages

        except Exception as e:
            logger.error(f"Error getting messages for user {user_id}: {e}")
            return []

    async def get_stats(self, user_id: str) -> QueueStats | None:
        """
        Get statistics for user's queue.

        Args:
            user_id: User identifier

        Returns:
            Queue statistics or None if queue doesn't exist
        """
        if not await self.is_available():
            return None

        try:
            queue_key = self.config.get_queue_key(user_id)
            meta_key = self.config.get_meta_key(user_id)

            # Get metadata
            meta_json = await self._redis.get(meta_key)
            if not meta_json:
                return None

            queue_meta = UserQueue.model_validate_json(meta_json)

            # Get queue length and size
            length = await self._redis.llen(queue_key)
            size_bytes = await self._redis.memory_usage(queue_key)

            # Get message timestamps for age calculation
            messages_json = await self._redis.lrange(queue_key, 0, 0)
            messages_json += await self._redis.lrange(queue_key, -1, -1)

            oldest_age = None
            newest_age = None

            if len(messages_json) > 0:
                try:
                    oldest_msg = QueuedMessage.from_json(messages_json[0])
                    oldest_ts = datetime.fromisoformat(oldest_msg.timestamp)
                    oldest_age = (datetime.now(UTC) - oldest_ts).total_seconds()

                    if len(messages_json) > 1:
                        newest_msg = QueuedMessage.from_json(messages_json[1])
                        newest_ts = datetime.fromisoformat(newest_msg.timestamp)
                        newest_age = (datetime.now(UTC) - newest_ts).total_seconds()
                except Exception:
                    pass

            return QueueStats(
                user_id=user_id,
                message_count=length,
                queue_size_bytes=size_bytes,
                oldest_message_age_seconds=oldest_age,
                newest_message_age_seconds=newest_age,
                is_full=queue_meta.is_full(),
            )

        except Exception as e:
            logger.error(f"Error getting stats for user {user_id}: {e}")
            return None

    async def clear_queue(self, user_id: str) -> bool:
        """Clear all messages for a user"""
        if not await self.is_available():
            return False

        try:
            queue_key = self.config.get_queue_key(user_id)
            meta_key = self.config.get_meta_key(user_id)

            await self._redis.delete(queue_key, meta_key)
            logger.info(f"Cleared queue for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Error clearing queue for user {user_id}: {e}")
            return False

    async def _cleanup_loop(self):
        """Periodic cleanup of expired queues"""
        if not self._redis:
            return

        while True:
            try:
                await asyncio.sleep(self.config.cleanup_interval_seconds)
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")

    async def _cleanup_expired(self):
        """Remove expired queue entries"""
        try:
            # Scan for queue metadata keys
            pattern = f"{self.config.KEY_PREFIX}:*{self.config.META_SUFFIX}"
            keys = []
            async for key in self._redis.scan_iter(match=pattern):
                keys.append(key)

            logger.info(f"Cleanup: Found {len(keys)} queue metadata keys")

            # Check each queue's TTL
            for meta_key in keys:
                ttl = await self._redis.ttl(meta_key)
                if ttl == -2:  # Key doesn't exist
                    queue_key = meta_key.replace(self.config.META_SUFFIX, "")
                    await self._redis.delete(queue_key)
                    logger.debug(f"Cleaned up expired queue: {meta_key}")

        except Exception as e:
            logger.error(f"Error in cleanup: {e}")


# Global instance
_message_queue_service: MessageQueueService | None = None


def get_message_queue_service(
    config: MessageQueueConfig | None = None,
) -> MessageQueueService:
    """Get or create the global message queue service instance"""
    global _message_queue_service
    if _message_queue_service is None:
        _message_queue_service = MessageQueueService(config)
    return _message_queue_service


async def start_message_queue(
    config: MessageQueueConfig | None = None,
) -> MessageQueueService:
    """Initialize and start the message queue service"""
    service = get_message_queue_service(config)
    await service.start()
    return service


async def stop_message_queue():
    """Stop the message queue service"""
    global _message_queue_service
    if _message_queue_service:
        await _message_queue_service.stop()
        _message_queue_service = None
