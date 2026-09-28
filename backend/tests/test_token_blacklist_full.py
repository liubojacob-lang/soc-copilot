"""Comprehensive tests for TokenBlacklist, InMemoryBackend, and RedisBackend."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from core.token_blacklist import (
    InMemoryBackend,
    RedisBackend,
    TokenBlacklist,
)


@pytest.mark.asyncio
async def test_in_memory_backend_lifecycle():
    backend = InMemoryBackend()

    # Initially empty
    assert await backend.contains("token_123") is False

    # Add token with 10s TTL
    added = await backend.add("token_123", ttl=10, reason="test_logout")
    assert added is True
    assert await backend.contains("token_123") is True

    # Info reflects count
    info = await backend.get_info()
    assert info["backend"] == "memory"
    assert info["count"] == 1

    # Remove token
    removed = await backend.remove("token_123")
    assert removed is True
    assert await backend.contains("token_123") is False
    assert await backend.remove("token_123") is False


@pytest.mark.asyncio
async def test_in_memory_backend_expiration():
    backend = InMemoryBackend()
    # Add with negative or expired TTL
    await backend.add("expired_token", ttl=-1)
    # Checking contains should clean it up and return False
    assert await backend.contains("expired_token") is False


@pytest.mark.asyncio
async def test_redis_backend_operations():
    backend = RedisBackend(redis_url="redis://localhost:6379/0")

    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)
    mock_redis.setex = AsyncMock(return_value=True)
    mock_redis.exists = AsyncMock(return_value=1)
    mock_redis.delete = AsyncMock(return_value=1)

    async def mock_scan_iter(match=None):
        yield "token_blacklist:abc"

    mock_redis.scan_iter = mock_scan_iter

    with patch.object(backend, "_get_redis", return_value=mock_redis):
        # Hash token
        hashed = backend._hash_token("sample_jwt_token")
        assert len(hashed) == 32

        # Add
        res = await backend.add("sample_jwt_token", ttl=3600, reason="logout")
        assert res is True
        mock_redis.setex.assert_awaited()

        # Contains
        res = await backend.contains("sample_jwt_token")
        assert res is True
        mock_redis.exists.assert_awaited()

        # Remove
        res = await backend.remove("sample_jwt_token")
        assert res is True
        mock_redis.delete.assert_awaited()

        # Get info
        info = await backend.get_info()
        assert info["backend"] == "redis"
        assert info["count"] == 1


@pytest.mark.asyncio
async def test_redis_backend_failure_handling():
    backend = RedisBackend(redis_url="redis://localhost:6379/0")
    with patch.object(backend, "_get_redis", return_value=None):
        assert await backend.add("tok", ttl=100) is False
        assert await backend.contains("tok") is False
        assert await backend.remove("tok") is False
        info = await backend.get_info()
        assert info["backend"] == "redis"
        assert info["connected"] is False


@pytest.mark.asyncio
async def test_token_blacklist_manager():
    mgr = TokenBlacklist()  # in-memory default

    # 1. Add valid token with mock decode_token
    mock_exp = int((datetime.now(UTC) + timedelta(minutes=15)).timestamp())
    with patch("core.token_blacklist.decode_token", return_value={"exp": mock_exp}):
        added = await mgr.add_to_blacklist("valid_jwt", reason="unit_test")
        assert added is True
        assert await mgr.is_blacklisted("valid_jwt") is True

    # 2. Add token without exp claim (fallback to default ttl)
    with patch("core.token_blacklist.decode_token", return_value={}):
        added = await mgr.add_to_blacklist("no_exp_jwt")
        assert added is True
        assert await mgr.is_blacklisted("no_exp_jwt") is True

    # 3. Explicit ttl
    added_ttl = await mgr.add_to_blacklist("custom_ttl_jwt", ttl=120)
    assert added_ttl is True
    assert await mgr.is_blacklisted("custom_ttl_jwt") is True

    # 4. Remove
    removed = await mgr.remove_from_blacklist("valid_jwt")
    assert removed is True
    assert await mgr.is_blacklisted("valid_jwt") is False
