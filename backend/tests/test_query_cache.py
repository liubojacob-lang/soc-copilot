"""
Tests for query cache service.
"""

import time

import pytest

from services.query_cache import (
    TTLCache,
    cached,
    generate_cache_key,
    get_query_cache,
    invalidate_cache,
)


class TestTTLCache:
    """Tests for TTLCache class."""

    def test_set_and_get(self):
        """Test basic set and get operations."""
        cache = TTLCache(max_size=100, default_ttl=300)

        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_get_nonexistent(self):
        """Test getting non-existent key returns None."""
        cache = TTLCache(max_size=100, default_ttl=300)

        assert cache.get("nonexistent") is None

    def test_delete(self):
        """Test deleting a key."""
        cache = TTLCache(max_size=100, default_ttl=300)

        cache.set("key1", "value1")
        cache.delete("key1")

        assert cache.get("key1") is None

    def test_clear(self):
        """Test clearing all cache."""
        cache = TTLCache(max_size=100, default_ttl=300)

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()

        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert len(cache.cache) == 0

    def test_lru_eviction(self):
        """Test LRU eviction when max size is reached."""
        cache = TTLCache(max_size=3, default_ttl=300)

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        cache.set("key4", "value4")

        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"

    def test_lru_access_order(self):
        """Test that accessing a key updates its LRU position."""
        cache = TTLCache(max_size=3, default_ttl=300)

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        cache.get("key1")
        cache.set("key4", "value4")

        assert cache.get("key2") is None
        assert cache.get("key1") == "value1"
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"

    def test_ttl_expiration(self):
        """Test that expired items are not returned."""
        cache = TTLCache(max_size=100, default_ttl=1)

        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

        time.sleep(1.1)

        assert cache.get("key1") is None

    def test_custom_ttl(self):
        """Test custom TTL per key."""
        cache = TTLCache(max_size=100, default_ttl=300)

        cache.set("key1", "value1", ttl=1)
        cache.set("key2", "value2", ttl=10)

        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"

        time.sleep(1.1)

        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"

    def test_get_stats(self):
        """Test getting cache statistics."""
        cache = TTLCache(max_size=100, default_ttl=300)

        cache.set("key1", "value1")
        cache.set("key2", "value2")

        stats = cache.get_stats()

        assert stats["size"] == 2
        assert stats["max_size"] == 100
        assert stats["default_ttl"] == 300


class TestCacheKeyGeneration:
    """Tests for cache key generation."""

    def test_generate_cache_key_simple(self):
        """Test generating simple cache keys."""
        key1 = generate_cache_key("test", 1, 2, a=3, b=4)
        key2 = generate_cache_key("test", 1, 2, a=3, b=4)

        assert key1 == key2

    def test_generate_cache_key_different_args(self):
        """Test that different args produce different keys."""
        key1 = generate_cache_key("test", 1)
        key2 = generate_cache_key("test", 2)

        assert key1 != key2

    def test_generate_cache_key_different_kwargs(self):
        """Test that different kwargs produce different keys."""
        key1 = generate_cache_key("test", a=1)
        key2 = generate_cache_key("test", a=2)

        assert key1 != key2

    def test_generate_cache_key_kwargs_order(self):
        """Test that kwargs order doesn't matter."""
        key1 = generate_cache_key("test", a=1, b=2)
        key2 = generate_cache_key("test", b=2, a=1)

        assert key1 == key2


class TestCachedDecorator:
    """Tests for @cached decorator."""

    def test_cached_sync_function(self):
        """Test caching a synchronous function."""
        call_count = 0

        @cached(ttl=300, prefix="test_func")
        def test_func(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        result1 = test_func(5)
        result2 = test_func(5)
        result3 = test_func(10)

        assert result1 == 10
        assert result2 == 10
        assert result3 == 20
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_cached_async_function(self):
        """Test caching an asynchronous function."""
        call_count = 0

        @cached(ttl=300, prefix="test_async_func")
        async def test_func(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        result1 = await test_func(5)
        result2 = await test_func(5)
        result3 = await test_func(10)

        assert result1 == 10
        assert result2 == 10
        assert result3 == 20
        assert call_count == 2


class TestInvalidateCache:
    """Tests for invalidate_cache function."""

    def test_invalidate_by_pattern(self):
        """Test invalidating cache by pattern."""
        cache = get_query_cache()

        cache.set("prefix1:key1", "value1")
        cache.set("prefix1:key2", "value2")
        cache.set("prefix2:key1", "value3")

        invalidated = invalidate_cache("prefix1:")

        assert invalidated == 2
        assert cache.get("prefix1:key1") is None
        assert cache.get("prefix1:key2") is None
        assert cache.get("prefix2:key1") == "value3"


class TestFactoryFunction:
    """Tests for get_query_cache factory."""

    def test_get_query_cache_returns_same_instance(self):
        """Test that get_query_cache returns the same instance."""
        cache1 = get_query_cache()
        cache2 = get_query_cache()

        assert cache1 is cache2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
