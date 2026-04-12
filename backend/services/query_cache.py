"""
In-memory Query Cache Service
Caches frequent database queries to improve performance.
"""

import hashlib
import json
import time
from collections import OrderedDict
from collections.abc import Callable
from functools import wraps
from typing import Any

from core.logger import get_logger
from observability.metrics import observe_cache_hit, observe_cache_miss, set_cache_size

logger = get_logger(__name__)


class TTLCache:
    """
    Simple in-memory TTL cache with LRU eviction.
    """

    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self.cache: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self.max_size = max_size
        self.default_ttl = default_ttl

    def get(self, key: str) -> Any | None:
        """Get a value from cache if it exists and hasn't expired."""
        if key not in self.cache:
            observe_cache_miss("query_cache")
            return None

        item = self.cache[key]
        if time.time() > item["expires_at"]:
            del self.cache[key]
            observe_cache_miss("query_cache")
            set_cache_size(len(self.cache), "query_cache")
            return None

        self.cache.move_to_end(key)
        observe_cache_hit("query_cache")
        return item["value"]

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set a value in cache with optional TTL."""
        if len(self.cache) >= self.max_size:
            self.cache.popitem(last=False)

        ttl = ttl or self.default_ttl
        self.cache[key] = {
            "value": value,
            "expires_at": time.time() + ttl,
        }
        self.cache.move_to_end(key)
        set_cache_size(len(self.cache), "query_cache")

    def delete(self, key: str) -> None:
        """Delete a value from cache."""
        if key in self.cache:
            del self.cache[key]
            set_cache_size(len(self.cache), "query_cache")

    def clear(self) -> None:
        """Clear all cached values."""
        self.cache.clear()
        set_cache_size(0, "query_cache")

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "default_ttl": self.default_ttl,
        }


_query_cache = TTLCache(max_size=1000, default_ttl=300)


def get_query_cache() -> TTLCache:
    """Get the global query cache instance."""
    return _query_cache


def generate_cache_key(prefix: str, *args, **kwargs) -> str:
    """Generate a unique cache key from function arguments."""
    key_data = {
        "prefix": prefix,
        "args": args,
        "kwargs": sorted(kwargs.items()),
    }
    key_string = json.dumps(key_data, sort_keys=True, default=str)
    return f"{prefix}:{hashlib.md5(key_string.encode()).hexdigest()}"


def cached(ttl: int = 300, prefix: str | None = None):
    """
    Decorator to cache function results.

    Args:
        ttl: Time to live in seconds
        prefix: Cache key prefix (defaults to function name)
    """

    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            cache_prefix = prefix or func.__name__
            cache_key = generate_cache_key(cache_prefix, *args, **kwargs)

            cached_result = _query_cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached_result

            logger.debug(f"Cache miss: {cache_key}")
            result = await func(*args, **kwargs)
            _query_cache.set(cache_key, result, ttl)
            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            cache_prefix = prefix or func.__name__
            cache_key = generate_cache_key(cache_prefix, *args, **kwargs)

            cached_result = _query_cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached_result

            logger.debug(f"Cache miss: {cache_key}")
            result = func(*args, **kwargs)
            _query_cache.set(cache_key, result, ttl)
            return result

        import inspect

        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def invalidate_cache(pattern: str) -> int:
    """
    Invalidate all cache keys matching a pattern.

    Args:
        pattern: Key prefix to invalidate

    Returns:
        Number of invalidated keys
    """
    keys_to_delete = [
        key for key in _query_cache.cache.keys() if key.startswith(pattern)
    ]
    for key in keys_to_delete:
        del _query_cache.cache[key]
    if keys_to_delete:
        set_cache_size(len(_query_cache.cache), "query_cache")
    return len(keys_to_delete)
