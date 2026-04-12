"""Comprehensive verification suite for P0 idempotency fixes.

This test module validates:
- P0-3: Idempotency controls in run queue to prevent duplicate task execution
- Edge cases: concurrent requests, key expiration, cache invalidation
"""

import asyncio
import os

# Import the modules under test
import sys
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the module to access its globals
import services.run_queue_manager as rqm_module
from services.run_queue_manager import (
    IDEMPOTENCY_CACHE_TTL,
    IdempotencyResult,
    RunQueueManager,
    clear_idempotency_cache,
    get_idempotency_cache_stats,
)


class TestIdempotencyKeyGeneration:
    """Test suite for idempotency key generation."""

    @pytest.fixture
    def manager(self):
        """Create a RunQueueManager instance for testing."""
        session_factory = AsyncMock()
        return RunQueueManager(session_factory)

    def test_generate_key_basic(self, manager):
        """Test basic idempotency key generation."""
        key = manager.generate_idempotency_key(
            playbook_name="test_playbook", trigger_source="webhook"
        )

        assert key is not None
        assert len(key) == 32  # SHA256 truncated to 32 chars
        assert isinstance(key, str)

    def test_generate_key_deterministic(self, manager):
        """Test that same inputs produce same key."""
        key1 = manager.generate_idempotency_key(
            playbook_name="test_playbook",
            trigger_source="webhook",
            trigger_id="trigger-123",
            input_hash="abc123",
        )

        key2 = manager.generate_idempotency_key(
            playbook_name="test_playbook",
            trigger_source="webhook",
            trigger_id="trigger-123",
            input_hash="abc123",
        )

        assert key1 == key2

    def test_generate_key_different_playbook(self, manager):
        """Test that different playbooks produce different keys."""
        key1 = manager.generate_idempotency_key(
            playbook_name="playbook_a", trigger_source="webhook"
        )

        key2 = manager.generate_idempotency_key(
            playbook_name="playbook_b", trigger_source="webhook"
        )

        assert key1 != key2

    def test_generate_key_different_trigger_source(self, manager):
        """Test that different trigger sources produce different keys."""
        key1 = manager.generate_idempotency_key(
            playbook_name="test_playbook", trigger_source="webhook"
        )

        key2 = manager.generate_idempotency_key(
            playbook_name="test_playbook", trigger_source="manual"
        )

        assert key1 != key2

    def test_generate_key_with_trigger_id(self, manager):
        """Test that trigger ID affects key generation."""
        key1 = manager.generate_idempotency_key(
            playbook_name="test_playbook",
            trigger_source="webhook",
            trigger_id="trigger-123",
        )

        key2 = manager.generate_idempotency_key(
            playbook_name="test_playbook",
            trigger_source="webhook",
            trigger_id="trigger-456",
        )

        assert key1 != key2

    def test_generate_key_with_input_hash(self, manager):
        """Test that input hash affects key generation."""
        key1 = manager.generate_idempotency_key(
            playbook_name="test_playbook", trigger_source="webhook", input_hash="hash1"
        )

        key2 = manager.generate_idempotency_key(
            playbook_name="test_playbook", trigger_source="webhook", input_hash="hash2"
        )

        assert key1 != key2


class TestInputHashComputation:
    """Test suite for input data hash computation."""

    @pytest.fixture
    def manager(self):
        """Create a RunQueueManager instance for testing."""
        session_factory = AsyncMock()
        return RunQueueManager(session_factory)

    def test_compute_input_hash_basic(self, manager):
        """Test basic input hash computation."""
        input_data = {"alert_id": "123", "severity": "high"}
        hash_result = manager.compute_input_hash(input_data)

        assert hash_result is not None
        assert len(hash_result) == 16  # Truncated SHA256
        assert isinstance(hash_result, str)

    def test_compute_input_hash_deterministic(self, manager):
        """Test that same input produces same hash."""
        input_data = {"alert_id": "123", "severity": "high"}

        hash1 = manager.compute_input_hash(input_data)
        hash2 = manager.compute_input_hash(input_data)

        assert hash1 == hash2

    def test_compute_input_hash_key_order_independent(self, manager):
        """Test that key order doesn't affect hash."""
        input1 = {"a": 1, "b": 2}
        input2 = {"b": 2, "a": 1}

        hash1 = manager.compute_input_hash(input1)
        hash2 = manager.compute_input_hash(input2)

        assert hash1 == hash2

    def test_compute_input_hash_different_values(self, manager):
        """Test that different values produce different hashes."""
        input1 = {"alert_id": "123"}
        input2 = {"alert_id": "456"}

        hash1 = manager.compute_input_hash(input1)
        hash2 = manager.compute_input_hash(input2)

        assert hash1 != hash2

    def test_compute_input_hash_empty_dict(self, manager):
        """Test hash computation for empty dictionary."""
        hash_result = manager.compute_input_hash({})

        assert hash_result is not None
        assert len(hash_result) == 16


class TestIdempotencyCheck:
    """Test suite for idempotency checking."""

    @pytest.fixture
    def manager(self):
        """Create a RunQueueManager instance for testing."""
        session_factory = AsyncMock()
        manager = RunQueueManager(session_factory)
        # Clear cache before each test
        clear_idempotency_cache()
        return manager

    @pytest.mark.asyncio
    async def test_check_idempotency_cache_hit(self, manager):
        """Test idempotency check with cache hit."""
        key = "test_key_123"
        run_id = "run-abc"
        status = "running"
        now = datetime.now(UTC)

        # Populate cache
        rqm_module._idempotency_cache[key] = (run_id, status, now)

        result = await manager.check_idempotency(key)

        assert result.is_unique is False
        assert result.existing_run_id == run_id
        assert result.existing_status == status

    @pytest.mark.asyncio
    async def test_check_idempotency_cache_miss(self, manager):
        """Test idempotency check with cache miss."""
        key = "nonexistent_key"

        # Mock database session with no existing run
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await manager.check_idempotency(key, session=mock_session)

        assert result.is_unique is True
        assert result.existing_run_id is None

    @pytest.mark.asyncio
    async def test_check_idempotency_expired_cache(self, manager):
        """Test that expired cache entries are ignored."""
        key = "expired_key"
        run_id = "run-old"
        status = "running"
        # Create expired timestamp (older than TTL)
        expired_time = datetime.now(UTC) - timedelta(
            seconds=IDEMPOTENCY_CACHE_TTL + 100
        )

        # Populate cache with expired entry
        rqm_module._idempotency_cache[key] = (run_id, status, expired_time)

        # Mock database session with no existing run
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await manager.check_idempotency(key, session=mock_session)

        assert result.is_unique is True

    @pytest.mark.asyncio
    async def test_check_idempotency_database_hit(self, manager):
        """Test idempotency check with database hit."""
        key = "db_key_123"

        # Mock database session with existing run
        mock_session = AsyncMock()
        mock_run = MagicMock()
        mock_run.id = "run-db-123"
        mock_run.status = "running"
        mock_run.started_at = datetime.now(UTC)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_run
        mock_session.execute.return_value = mock_result

        result = await manager.check_idempotency(key, session=mock_session)

        assert result.is_unique is False
        assert result.existing_run_id == "run-db-123"


class TestIdempotencyRegistration:
    """Test suite for idempotency key registration."""

    @pytest.fixture
    def manager(self):
        """Create a RunQueueManager instance for testing."""
        session_factory = AsyncMock()
        manager = RunQueueManager(session_factory)
        clear_idempotency_cache()
        return manager

    @pytest.mark.asyncio
    async def test_register_idempotency_key(self, manager):
        """Test registering an idempotency key."""
        key = "new_key_123"
        run_id = "run-new"
        status = "queued"

        await manager.register_idempotency_key(key, run_id, status)

        assert key in rqm_module._idempotency_cache
        cached_run_id, cached_status, cached_time = rqm_module._idempotency_cache[key]
        assert cached_run_id == run_id
        assert cached_status == status
        assert isinstance(cached_time, datetime)

    @pytest.mark.asyncio
    async def test_register_updates_existing_key(self, manager):
        """Test that registering updates existing key."""
        key = "update_key"

        # Register initially
        await manager.register_idempotency_key(key, "run-1", "queued")

        # Update with new status
        await manager.register_idempotency_key(key, "run-1", "running")

        cached_run_id, cached_status, _ = rqm_module._idempotency_cache[key]
        assert cached_status == "running"


class TestCacheManagement:
    """Test suite for cache management functions."""

    def setup_method(self):
        """Clear cache before each test."""
        clear_idempotency_cache()

    def test_get_cache_stats_empty(self):
        """Test cache stats when empty."""
        stats = get_idempotency_cache_stats()

        assert stats["cache_size"] == 0
        assert stats["ttl_seconds"] == IDEMPOTENCY_CACHE_TTL

    def test_get_cache_stats_with_entries(self):
        """Test cache stats with entries."""
        # Add some entries
        rqm_module._idempotency_cache["key1"] = (
            "run1",
            "running",
            datetime.now(UTC),
        )
        rqm_module._idempotency_cache["key2"] = (
            "run2",
            "queued",
            datetime.now(UTC),
        )

        stats = get_idempotency_cache_stats()

        assert stats["cache_size"] == 2

    def test_clear_cache(self):
        """Test clearing the cache."""
        # Add entries
        rqm_module._idempotency_cache["key1"] = (
            "run1",
            "running",
            datetime.now(UTC),
        )
        rqm_module._idempotency_cache["key2"] = (
            "run2",
            "queued",
            datetime.now(UTC),
        )

        count = clear_idempotency_cache()

        assert count == 2
        assert len(rqm_module._idempotency_cache) == 0

    def test_clear_empty_cache(self):
        """Test clearing an empty cache."""
        count = clear_idempotency_cache()

        assert count == 0


class TestExpiredCacheCleanup:
    """Test suite for expired cache entry cleanup."""

    @pytest.fixture
    def manager(self):
        """Create a RunQueueManager instance for testing."""
        session_factory = AsyncMock()
        manager = RunQueueManager(session_factory)
        clear_idempotency_cache()
        return manager

    def test_clear_expired_entries(self, manager):
        """Test clearing expired cache entries."""
        now = datetime.now(UTC)

        # Add fresh entry
        rqm_module._idempotency_cache["fresh"] = ("run1", "running", now)

        # Add expired entry
        expired_time = now - timedelta(seconds=IDEMPOTENCY_CACHE_TTL + 100)
        rqm_module._idempotency_cache["expired"] = ("run2", "running", expired_time)

        cleared = manager.clear_expired_cache_entries()

        assert cleared == 1
        assert "fresh" in rqm_module._idempotency_cache
        assert "expired" not in rqm_module._idempotency_cache

    def test_clear_no_expired_entries(self, manager):
        """Test when no entries are expired."""
        now = datetime.now(UTC)

        # Add only fresh entries
        rqm_module._idempotency_cache["key1"] = ("run1", "running", now)
        rqm_module._idempotency_cache["key2"] = ("run2", "queued", now)

        cleared = manager.clear_expired_cache_entries()

        assert cleared == 0
        assert len(rqm_module._idempotency_cache) == 2


class TestQueueRunWithIdempotency:
    """Test suite for queue_run_with_idempotency method."""

    @pytest.fixture
    def manager(self):
        """Create a RunQueueManager instance for testing."""

        # Create a proper async context manager mock
        async def mock_session_factory():
            mock_session = AsyncMock()
            return mock_session

        # Make it a context manager
        class AsyncContextManager:
            async def __aenter__(self):
                return AsyncMock()

            async def __aexit__(self, *args):
                pass

        manager = RunQueueManager(lambda: AsyncContextManager())
        clear_idempotency_cache()
        return manager

    @pytest.mark.asyncio
    async def test_queue_run_unique(self, manager):
        """Test queueing a unique run."""
        # Mock the run object
        mock_run = MagicMock()
        mock_run.id = "new-run-123"

        with patch.object(manager, "check_idempotency") as mock_check:
            with patch.object(manager, "register_idempotency_key") as mock_register:
                with patch.object(
                    manager, "queue_run", new_callable=AsyncMock
                ) as mock_queue:
                    mock_check.return_value = IdempotencyResult(is_unique=True)

                    # Mock PlaybookRunRepository
                    with patch(
                        "repositories.playbook_run_repository.PlaybookRunRepository"
                    ) as MockRepo:
                        mock_repo_instance = AsyncMock()
                        mock_repo_instance.create.return_value = mock_run
                        MockRepo.return_value = mock_repo_instance

                        run_id, result = await manager.queue_run_with_idempotency(
                            playbook_name="test_playbook",
                            trigger_source="webhook",
                            trigger_id="trigger-123",
                            input_data={"alert_id": "A001"},
                        )

                        assert run_id == "new-run-123"
                        assert result.is_unique is True
                        mock_register.assert_called_once()
                        mock_queue.assert_called_once_with("new-run-123")

    @pytest.mark.asyncio
    async def test_queue_run_duplicate_rejected(self, manager):
        """Test that duplicate runs are rejected."""
        with patch.object(manager, "check_idempotency") as mock_check:
            mock_check.return_value = IdempotencyResult(
                is_unique=False,
                existing_run_id="existing-run-123",
                existing_status="running",
            )

            run_id, result = await manager.queue_run_with_idempotency(
                playbook_name="test_playbook",
                trigger_source="webhook",
                trigger_id="trigger-123",
            )

            assert run_id is None
            assert result.is_unique is False
            assert result.existing_run_id == "existing-run-123"


class TestConcurrentRequests:
    """Test suite for concurrent request handling."""

    @pytest.fixture
    def manager(self):
        """Create a RunQueueManager instance for testing."""
        session_factory = AsyncMock()
        manager = RunQueueManager(session_factory)
        clear_idempotency_cache()
        return manager

    @pytest.mark.asyncio
    async def test_concurrent_same_request(self, manager):
        """Test handling of concurrent identical requests."""
        key = "concurrent_key"
        run_id = "run-concurrent"

        # Simulate first request registering the key
        rqm_module._idempotency_cache[key] = (
            run_id,
            "running",
            datetime.now(UTC),
        )

        # Second concurrent request should see the cache entry
        result = await manager.check_idempotency(key)

        assert result.is_unique is False
        assert result.existing_run_id == run_id

    @pytest.mark.asyncio
    async def test_concurrent_different_requests(self, manager):
        """Test handling of concurrent different requests."""
        # Mock database session
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Run two different idempotency checks concurrently
        results = await asyncio.gather(
            manager.check_idempotency("key1", session=mock_session),
            manager.check_idempotency("key2", session=mock_session),
        )

        assert all(r.is_unique for r in results)


class TestIdempotencyResult:
    """Test suite for IdempotencyResult class."""

    def test_unique_result(self):
        """Test creating a unique result."""
        result = IdempotencyResult(is_unique=True)

        assert result.is_unique is True
        assert result.existing_run_id is None
        assert result.existing_status is None

    def test_duplicate_result(self):
        """Test creating a duplicate result."""
        result = IdempotencyResult(
            is_unique=False, existing_run_id="run-123", existing_status="running"
        )

        assert result.is_unique is False
        assert result.existing_run_id == "run-123"
        assert result.existing_status == "running"

    def test_to_dict(self):
        """Test converting result to dictionary."""
        result = IdempotencyResult(
            is_unique=False, existing_run_id="run-123", existing_status="completed"
        )

        result_dict = result.to_dict()

        assert result_dict["is_unique"] is False
        assert result_dict["existing_run_id"] == "run-123"
        assert result_dict["existing_status"] == "completed"


class TestEdgeCases:
    """Test suite for edge cases."""

    @pytest.fixture
    def manager(self):
        """Create a RunQueueManager instance for testing."""
        session_factory = AsyncMock()
        manager = RunQueueManager(session_factory)
        clear_idempotency_cache()
        return manager

    def test_empty_playbook_name(self, manager):
        """Test key generation with empty playbook name."""
        key = manager.generate_idempotency_key(
            playbook_name="", trigger_source="webhook"
        )

        assert key is not None
        assert len(key) == 32

    def test_special_characters_in_playbook_name(self, manager):
        """Test key generation with special characters."""
        key = manager.generate_idempotency_key(
            playbook_name="playbook-with_special.chars:123", trigger_source="webhook"
        )

        assert key is not None
        assert len(key) == 32

    def test_unicode_in_input_data(self, manager):
        """Test hash computation with unicode data."""
        input_data = {"message": "你好世界", "alert": "🚨 Alert"}

        hash_result = manager.compute_input_hash(input_data)

        assert hash_result is not None
        assert len(hash_result) == 16

    def test_nested_input_data(self, manager):
        """Test hash computation with nested data."""
        input_data = {
            "alert": {"id": "123", "details": {"severity": "high", "source": "siem"}}
        }

        hash_result = manager.compute_input_hash(input_data)

        assert hash_result is not None
        assert len(hash_result) == 16

    def test_very_long_playbook_name(self, manager):
        """Test key generation with very long playbook name."""
        long_name = "a" * 1000

        key = manager.generate_idempotency_key(
            playbook_name=long_name, trigger_source="webhook"
        )

        assert key is not None
        assert len(key) == 32

    @pytest.mark.asyncio
    async def test_none_trigger_id(self, manager):
        """Test key generation with None trigger ID."""
        key = manager.generate_idempotency_key(
            playbook_name="test", trigger_source="manual", trigger_id=None
        )

        assert key is not None
        assert len(key) == 32

    @pytest.mark.asyncio
    async def test_none_input_hash(self, manager):
        """Test key generation with None input hash."""
        key = manager.generate_idempotency_key(
            playbook_name="test", trigger_source="manual", input_hash=None
        )

        assert key is not None
        assert len(key) == 32


# Integration test markers
@pytest.mark.integration
class TestIntegration:
    """Integration tests requiring database connection."""

    @pytest.mark.asyncio
    async def test_full_idempotency_flow(self):
        """Test complete idempotency flow with database."""
        # This test would require a real database connection
        # Marked as integration test to skip in unit test runs
        pytest.skip("Integration test requires database connection")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
