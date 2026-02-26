"""Unit tests for Token Blacklist.

v0.8.5: Updated to match actual TokenBlacklist implementation.
- TokenBlacklist now takes redis_url instead of redis_client
- Uses backend pattern (RedisBackend, InMemoryBackend)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta

from core.token_blacklist import (
    TokenBlacklist,
    InMemoryBackend,
    get_token_blacklist,
    verify_token_not_blacklisted,
    add_token_to_blacklist,
)


@pytest.fixture
def valid_token():
    """Create a valid JWT token for testing."""
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"


@pytest.fixture
def token_blacklist():
    """Create token blacklist instance without Redis."""
    return TokenBlacklist(redis_url=None)


@pytest.fixture
def token_blacklist_with_mock_redis(valid_token):
    """Create token blacklist with mocked Redis backend."""
    blacklist = TokenBlacklist(redis_url=None)
    # Mock the primary backend
    blacklist._primary_backend = AsyncMock(spec=InMemoryBackend)
    blacklist._use_redis = True
    return blacklist


class TestInMemoryBackend:
    """Tests for InMemoryBackend."""

    @pytest.mark.asyncio
    async def test_add_and_contains(self):
        """Test adding and checking token in memory backend."""
        backend = InMemoryBackend()
        token = "test_token_123"
        
        # Add token
        result = await backend.add(token, ttl=3600, reason="test")
        assert result is True
        
        # Check token exists
        exists = await backend.contains(token)
        assert exists is True

    @pytest.mark.asyncio
    async def test_remove(self):
        """Test removing token from memory backend."""
        backend = InMemoryBackend()
        token = "test_token_123"
        
        await backend.add(token, ttl=3600)
        assert await backend.contains(token) is True
        
        # Remove token
        result = await backend.remove(token)
        assert result is True
        assert await backend.contains(token) is False

    @pytest.mark.asyncio
    async def test_get_info(self):
        """Test getting backend info."""
        backend = InMemoryBackend()
        await backend.add("token1", ttl=3600)
        await backend.add("token2", ttl=3600)
        
        info = await backend.get_info()
        
        assert info["backend"] == "memory"
        assert info["count"] == 2


class TestTokenBlacklist:
    """Tests for TokenBlacklist."""

    def test_init_without_redis(self):
        """Test initialization without Redis."""
        blacklist = TokenBlacklist(redis_url=None)
        
        assert blacklist._primary_backend is None
        assert blacklist._use_redis is False
        assert blacklist._fallback_backend is not None

    @pytest.mark.asyncio
    async def test_add_to_blacklist(self, token_blacklist, valid_token):
        """Test adding token to blacklist."""
        result = await token_blacklist.add_to_blacklist(valid_token, reason="logout")
        
        assert result is True

    @pytest.mark.asyncio
    async def test_is_blacklisted_true(self, token_blacklist, valid_token):
        """Test checking if token is blacklisted."""
        await token_blacklist.add_to_blacklist(valid_token, reason="logout")
        
        result = await token_blacklist.is_blacklisted(valid_token)
        
        assert result is True

    @pytest.mark.asyncio
    async def test_is_blacklisted_false(self, token_blacklist, valid_token):
        """Test checking if token is not blacklisted."""
        result = await token_blacklist.is_blacklisted(valid_token)
        
        assert result is False

    @pytest.mark.asyncio
    async def test_remove_from_blacklist(self, token_blacklist, valid_token):
        """Test removing token from blacklist."""
        await token_blacklist.add_to_blacklist(valid_token)
        assert await token_blacklist.is_blacklisted(valid_token) is True
        
        result = await token_blacklist.remove_from_blacklist(valid_token)
        
        assert result is True
        assert await token_blacklist.is_blacklisted(valid_token) is False

    @pytest.mark.asyncio
    async def test_get_blacklist_info(self, token_blacklist):
        """Test getting blacklist info."""
        info = await token_blacklist.get_blacklist_info()
        
        assert "redis_available" in info
        assert "fallback" in info
        assert info["fallback"]["backend"] == "memory"


class TestGlobalFunctions:
    """Tests for global helper functions."""

    def test_get_token_blacklist_singleton(self):
        """Test that get_token_blacklist returns singleton."""
        blacklist1 = get_token_blacklist()
        blacklist2 = get_token_blacklist()
        
        assert blacklist1 is blacklist2

    @pytest.mark.asyncio
    async def test_add_token_to_blacklist(self, valid_token):
        """Test global add_token_to_blacklist function."""
        result = await add_token_to_blacklist(valid_token, reason="test")
        
        assert result is True

    @pytest.mark.asyncio
    async def test_verify_token_not_blacklisted_passes(self, valid_token):
        """Test that non-blacklisted token passes verification."""
        # Use a different token that's not blacklisted
        different_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkaWZmZXJlbnQifQ.signature"
        
        result = await verify_token_not_blacklisted(different_token)
        
        assert result is True


class TestEdgeCases:
    """Tests for edge cases."""

    @pytest.mark.asyncio
    async def test_empty_token(self, token_blacklist):
        """Test handling empty token."""
        result = await token_blacklist.is_blacklisted("")
        
        assert result is False

    @pytest.mark.asyncio
    async def test_none_token(self, token_blacklist):
        """Test handling None token."""
        result = await token_blacklist.is_blacklisted(None)
        
        assert result is False

    @pytest.mark.asyncio
    async def test_very_long_token(self, token_blacklist):
        """Test handling very long token."""
        long_token = "a" * 1000
        
        result = await token_blacklist.add_to_blacklist(long_token, reason="test")
        
        assert result is True
        assert await token_blacklist.is_blacklisted(long_token) is True

    @pytest.mark.asyncio
    async def test_special_characters_in_token(self, token_blacklist):
        """Test handling special characters in token."""
        special_token = "token!@#$%^&*()_+-=[]{}|;':\",./<>?"
        
        result = await token_blacklist.add_to_blacklist(special_token, reason="test")
        
        assert result is True
