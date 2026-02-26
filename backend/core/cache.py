"""
Redis Cache Implementation
Provides distributed caching for SOC Copilot application
"""

import json
import logging
from typing import Optional, Any, List
from datetime import timedelta

try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    aioredis = None

from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)


class RedisCache:
    """Redis cache wrapper with automatic connection management"""

    def __init__(self):
        self._client: Optional[aioredis.Redis] = None
        self._enabled = settings.redis_enabled and REDIS_AVAILABLE

    async def _get_client(self) -> Optional[aioredis.Redis]:
        """Get or create Redis client"""
        if not self._enabled:
            return None

        if self._client is None:
            try:
                self._client = await aioredis.from_url(
                    settings.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                )
                # Test connection
                await self._client.ping()
                logger.info(f"Connected to Redis: {settings.redis_url}")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                self._client = None
                self._enabled = False

        return self._client

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self._enabled:
            return None

        try:
            client = await self._get_client()
            if client is None:
                return None

            value = await client.get(key)
            if value is not None:
                # Try to parse as JSON
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int = 300
    ) -> bool:
        """Set value in cache with TTL (seconds)"""
        if not self._enabled:
            return False

        try:
            client = await self._get_client()
            if client is None:
                return False

            # Serialize to JSON
            if not isinstance(value, (str, bytes)):
                value = json.dumps(value)

            await client.setex(key, ttl, value)
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self._enabled:
            return False

        try:
            client = await self._get_client()
            if client is None:
                return False

            await client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """Delete keys matching pattern"""
        if not self._enabled:
            return 0

        try:
            client = await self._get_client()
            if client is None:
                return 0

            keys = []
            async for key in client.scan_iter(match=pattern, count=100):
                keys.append(key)

            if keys:
                await client.delete(*keys)

            return len(keys)
        except Exception as e:
            logger.error(f"Cache delete pattern error: {e}")
            return 0

    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        if not self._enabled:
            return False

        try:
            client = await self._get_client()
            if client is None:
                return False

            return await client.exists(key) > 0
        except Exception as e:
            logger.error(f"Cache exists error: {e}")
            return False

    async def expire(self, key: str, ttl: int) -> bool:
        """Update key TTL"""
        if not self._enabled:
            return False

        try:
            client = await self._get_client()
            if client is None:
                return False

            return await client.expire(key, ttl)
        except Exception as e:
            logger.error(f"Cache expire error: {e}")
            return False

    async def close(self):
        """Close Redis connection"""
        if self._client is not None:
            await self._client.aclose()
            self._client = None


# Singleton instance
_cache: Optional[RedisCache] = None


def get_cache() -> RedisCache:
    """Get cache singleton instance"""
    global _cache
    if _cache is None:
        _cache = RedisCache()
    return _cache


async def close_cache():
    """Close cache connection"""
    global _cache
    if _cache is not None:
        await _cache.close()
        _cache = None


class CacheDecorator:
    """Decorator for caching function results"""

    def __init__(
        self,
        key_prefix: str,
        ttl: int = 300,
        serialize: bool = True
    ):
        self.key_prefix = key_prefix
        self.ttl = ttl
        self.serialize = serialize

    def __call__(self, func):
        async def wrapper(*args, **kwargs):
            cache = get_cache()

            # Generate cache key
            key_parts = [self.key_prefix]
            if args:
                key_parts.extend(str(arg) for arg in args)
            if kwargs:
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = ":".join(key_parts)

            # Try to get from cache
            cached_value = await cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached_value

            # Call function and cache result
            result = await func(*args, **kwargs)

            if result is not None:
                await cache.set(cache_key, result, self.ttl)
                logger.debug(f"Cache set: {cache_key}")

            return result

        return wrapper


# Predefined cache keys and TTLs
class CacheKeys:
    """Cache key patterns and TTLs"""

    # Playbook definitions (5 minutes)
    PLAYBOOK_DEFINITION = "playbook:definition"
    PLAYBOOK_DEFINITIONS_LIST = "playbook:definitions:list"
    PLAYBOOK_TTL = 300

    # User permissions (5 minutes)
    USER_PERMISSIONS = "user:permissions"
    PERMISSIONS_TTL = 300

    # AI models (1 minute)
    AI_MODELS_LIST = "ai:models:list"
    AI_MODELS_TTL = 60

    # System status (10 seconds)
    SYSTEM_STATUS = "system:status"
    STATUS_TTL = 10

    # Threat intel cache (7 days as configured)
    THREAT_INTEL = "ti:cache"
    THREAT_INTEL_TTL = None  # Use configured TTL


async def invalidate_playbook_cache(definition_id: Optional[str] = None):
    """Invalidate playbook cache"""
    cache = get_cache()

    if definition_id:
        await cache.delete(f"{CacheKeys.PLAYBOOK_DEFINITION}:{definition_id}")
    else:
        await cache.delete_pattern(f"{CacheKeys.PLAYBOOK_DEFINITION}:*")

    # Invalidate list cache
    await cache.delete(CacheKeys.PLAYBOOK_DEFINITIONS_LIST)


async def invalidate_user_cache(user_id: str):
    """Invalidate user-specific cache"""
    cache = get_cache()

    await cache.delete(f"{CacheKeys.USER_PERMISSIONS}:{user_id}")


async def invalidate_ai_cache():
    """Invalidate AI models cache"""
    cache = get_cache()

    await cache.delete(CacheKeys.AI_MODELS_LIST)
    await cache.delete_pattern("ai:model:*")


async def warm_up_cache():
    """Warm up cache with frequently accessed data"""
    from repositories.user_repository import UserRepository
    from repositories.playbook_repository import PlaybookDefinitionRepository
    from db.session import get_session

    cache = get_cache()

    logger.info("Starting cache warm-up...")

    try:
        async with get_session() as session:
            # Cache active playbooks
            playbook_repo = PlaybookDefinitionRepository(session)
            active_playbooks = await playbook_repo.list_active()

            for playbook in active_playbooks:
                await cache.set(
                    f"{CacheKeys.PLAYBOOK_DEFINITION}:{playbook.id}",
                    playbook.to_dict(),
                    CacheKeys.PLAYBOOK_TTL
                )

            logger.info(f"Warmed up {len(active_playbooks)} playbook definitions")

    except Exception as e:
        logger.error(f"Cache warm-up error: {e}")

    logger.info("Cache warm-up complete")
