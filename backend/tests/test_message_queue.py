"""
Unit tests for Message Queue Service

Tests the offline message caching functionality including:
- Message queuing
- Message retrieval
- Queue statistics
- TTL management
- Edge cases
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from models.message_queue import (
    MessageQueueConfig,
    MessageType,
    QueuedMessage,
    UserQueue,
)
from services.message_queue import MessageQueueService


@pytest.fixture
async def message_queue_service():
    """Create a message queue service for testing"""
    # Use in-memory mock for testing (no real Redis required)
    config = MessageQueueConfig(redis_url="redis://mock:6379/0")
    service = MessageQueueService(config)

    # Mock Redis client
    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)
    service._redis = mock_redis

    yield service

    # Cleanup
    await service.stop()


@pytest.mark.asyncio
class TestQueuedMessage:
    """Tests for QueuedMessage model"""

    def test_create_queued_message(self):
        """Test creating a queued message"""
        msg = QueuedMessage(type=MessageType.ALERT, data={"test": "data"}, channel="alerts")

        assert msg.type == MessageType.ALERT
        assert msg.data == {"test": "data"}
        assert msg.channel == "alerts"
        assert msg.ttl_seconds == 86400

    def test_message_serialization(self):
        """Test message to/from JSON conversion"""
        msg = QueuedMessage(
            type=MessageType.ALERT,
            data={"severity": "high", "id": "123"},
            channel="alerts",
        )

        # To JSON
        json_str = msg.to_json()
        assert isinstance(json_str, str)

        # From JSON
        restored = QueuedMessage.from_json(json_str)
        assert restored.type == MessageType.ALERT
        assert restored.data["severity"] == "high"
        assert restored.data["id"] == "123"


@pytest.mark.asyncio
class TestUserQueue:
    """Tests for UserQueue model"""

    def test_create_user_queue(self):
        """Test creating a user queue"""
        queue = UserQueue(user_id="user123")

        assert queue.user_id == "user123"
        assert queue.message_count == 0
        assert queue.max_size == 1000
        assert not queue.is_full()

    def test_queue_full_detection(self):
        """Test queue full detection"""
        queue = UserQueue(user_id="user123", max_size=5)
        queue.message_count = 5

        assert queue.is_full()

    def test_add_message_to_queue(self):
        """Test adding messages to queue"""
        queue = UserQueue(user_id="user123")

        # Add messages
        assert queue.add_message() == True
        assert queue.message_count == 1

        assert queue.add_message() == True
        assert queue.message_count == 2

    def test_add_to_full_queue(self):
        """Test adding message to full queue"""
        queue = UserQueue(user_id="user123", max_size=1)
        queue.add_message()

        # Should fail when full
        assert queue.add_message() == False
        assert queue.message_count == 1

    def test_remove_messages_from_queue(self):
        """Test removing messages from queue"""
        queue = UserQueue(user_id="user123")
        queue.add_message()
        queue.add_message()
        queue.add_message()

        # Remove messages
        removed = queue.remove_messages(2)
        assert removed == 2
        assert queue.message_count == 1


@pytest.mark.asyncio
class TestMessageQueueService:
    """Tests for MessageQueueService"""

    async def test_service_initialization(self):
        """Test service initializes without Redis"""
        config = MessageQueueConfig(redis_url="redis://invalid:6379/0")
        service = MessageQueueService(config)

        # Service should start even if Redis unavailable
        await service.start()

        # Should report unavailable
        assert not await service.is_available()

        await service.stop()

    async def test_push_message_success(self, message_queue_service):
        """Test successfully pushing a message"""
        service = message_queue_service

        # Mock successful queue operations
        service._redis.get = AsyncMock(return_value=None)  # No existing queue
        service._redis.rpush = AsyncMock(return_value=1)
        service._redis.setex = AsyncMock(return_value=True)
        service._redis.expire = AsyncMock(return_value=True)

        result = await service.push_message(
            user_id="user123", message_type=MessageType.ALERT, data={"test": "data"}
        )

        assert result is True
        service._redis.rpush.assert_called_once()
        service._redis.setex.assert_called_once()

    async def test_push_message_to_full_queue(self, message_queue_service):
        """Test pushing message to full queue"""
        service = message_queue_service

        # Mock existing full queue
        full_queue = UserQueue(user_id="user123", max_size=1)
        full_queue.add_message()  # Make it full

        service._redis.get = AsyncMock(return_value=full_queue.model_dump_json())

        result = await service.push_message(
            user_id="user123", message_type=MessageType.ALERT, data={"test": "data"}
        )

        assert result is False

    async def test_get_messages_from_queue(self, message_queue_service):
        """Test retrieving messages from queue"""
        service = message_queue_service

        # Mock queued messages
        msg1 = QueuedMessage(type=MessageType.ALERT, data={"id": "1"})
        msg2 = QueuedMessage(type=MessageType.ALERT, data={"id": "2"})

        service._redis.lrange = AsyncMock(return_value=[msg1.to_json(), msg2.to_json()])
        service._redis.delete = AsyncMock(return_value=1)

        messages = await service.get_messages("user123")

        assert len(messages) == 2
        assert messages[0].data["id"] == "1"
        assert messages[1].data["id"] == "2"

        # Verify queue was cleared
        assert service._redis.delete.call_count == 2  # queue + meta keys

    async def test_get_queue_stats(self, message_queue_service):
        """Test getting queue statistics"""
        service = message_queue_service

        # Mock queue metadata
        queue_meta = UserQueue(user_id="user123", message_count=5)

        service._redis.get = AsyncMock(return_value=queue_meta.model_dump_json())
        service._redis.llen = AsyncMock(return_value=5)
        service._redis.memory_usage = AsyncMock(return_value=1024)

        # Mock message timestamps
        old_msg = QueuedMessage(
            type=MessageType.ALERT,
            data={},
            timestamp=(datetime.now(UTC).isoformat()),
        )
        new_msg = QueuedMessage(
            type=MessageType.ALERT,
            data={},
            timestamp=(datetime.now(UTC).isoformat()),
        )

        service._redis.lrange = AsyncMock(return_value=[old_msg.to_json(), new_msg.to_json()])

        stats = await service.get_stats("user123")

        assert stats is not None
        assert stats.user_id == "user123"
        assert stats.message_count == 5
        assert stats.queue_size_bytes == 1024
        assert not stats.is_full

    async def test_get_stats_for_nonexistent_queue(self, message_queue_service):
        """Test getting stats for non-existent queue"""
        service = message_queue_service

        service._redis.get = AsyncMock(return_value=None)

        stats = await service.get_stats("user999")

        assert stats is None

    async def test_clear_queue(self, message_queue_service):
        """Test clearing a queue"""
        service = message_queue_service

        service._redis.delete = AsyncMock(return_value=2)

        result = await service.clear_queue("user123")

        assert result is True
        service._redis.delete.assert_called_once()

    async def test_message_tll_settings(self, message_queue_service):
        """Test that default TTL is set on queued messages"""
        service = message_queue_service

        service._redis.get = AsyncMock(return_value=None)
        service._redis.rpush = AsyncMock(return_value=1)
        service._redis.setex = AsyncMock(return_value=True)
        service._redis.expire = AsyncMock(return_value=True)

        result = await service.push_message(
            user_id="user123",
            message_type=MessageType.ALERT,
            data={"test": "data"},
        )

        assert result is True
        service._redis.rpush.assert_called_once()


@pytest.mark.asyncio
class TestMessageQueueConfig:
    """Tests for MessageQueueConfig"""

    def test_default_config(self):
        """Test default configuration values"""
        config = MessageQueueConfig()

        assert config.redis_url == "redis://localhost:6379/0"
        assert config.default_ttl_seconds == 86400
        assert config.max_queue_size == 1000

    def test_custom_config(self):
        """Test custom configuration"""
        config = MessageQueueConfig(
            redis_url="redis://custom:6380/1",
            default_ttl_seconds=3600,
            max_queue_size=500,
        )

        assert config.redis_url == "redis://custom:6380/1"
        assert config.default_ttl_seconds == 3600
        assert config.max_queue_size == 500

    def test_redis_key_generation(self):
        """Test Redis key generation"""
        config = MessageQueueConfig()

        queue_key = config.get_queue_key("user123")
        assert queue_key == "ws:queue:user123"

        meta_key = config.get_meta_key("user123")
        assert meta_key == "ws:queue:user123:meta"


# Integration tests (require real Redis)
@pytest.mark.integration
@pytest.mark.asyncio
class TestMessageQueueIntegration:
    """Integration tests with real Redis (skipped if Redis unavailable)"""

    @pytest.fixture
    async def real_service(self):
        """Create service with real Redis connection"""
        import os

        redis_url = os.getenv("REDIS_TEST_URL", "redis://localhost:6379/1")

        config = MessageQueueConfig(redis_url=redis_url)
        service = MessageQueueService(config)

        try:
            await service.start()
            if not await service.is_available():
                pytest.skip("Redis not available")
            yield service
        finally:
            await service.stop()

    async def test_full_message_cycle(self, real_service):
        """Test complete message lifecycle"""
        service = real_service

        # Clear any existing queue
        await service.clear_queue("test_user")

        # Push messages
        await service.push_message(
            user_id="test_user",
            message_type=MessageType.ALERT,
            data={"id": "1", "severity": "high"},
        )

        await service.push_message(
            user_id="test_user",
            message_type=MessageType.ALERT,
            data={"id": "2", "severity": "medium"},
        )

        # Get stats
        stats = await service.get_stats("test_user")
        assert stats is not None
        assert stats.message_count == 2

        # Retrieve messages
        messages = await service.get_messages("test_user")
        assert len(messages) == 2
        assert messages[0].data["id"] == "1"
        assert messages[1].data["id"] == "2"

        # Verify queue is cleared
        stats_after = await service.get_stats("test_user")
        assert stats_after is None  # Queue no longer exists

    async def test_queue_size_limit(self, real_service):
        """Test that queue size limit is enforced"""
        service = real_service
        max_size = 5  # Small limit for testing

        # Create queue with small limit
        config = MessageQueueConfig(max_queue_size=max_size)
        limited_service = MessageQueueService(config)
        await limited_service.start()

        try:
            await limited_service.clear_queue("limit_test")

            # Add messages up to limit
            for i in range(max_size):
                result = await limited_service.push_message(
                    user_id="limit_test",
                    message_type=MessageType.ALERT,
                    data={"id": str(i)},
                )
                assert result is True

            # Try to add one more
            result = await limited_service.push_message(
                user_id="limit_test",
                message_type=MessageType.ALERT,
                data={"id": "overflow"},
            )
            assert result is False  # Should fail

        finally:
            await limited_service.stop()
            await limited_service.clear_queue("limit_test")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
