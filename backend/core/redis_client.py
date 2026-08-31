"""
Redis Client Module
Provides a singleton async Redis client for internal services.
"""

import redis.asyncio as aioredis

from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)

_client: aioredis.Redis | None = None


async def get_redis_client() -> aioredis.Redis | None:
    """Get or create the singleton async Redis client."""
    global _client

    if _client is not None:
        return _client

    try:
        _client = await aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        await _client.ping()
        logger.info(f"Connected to Redis: {settings.redis_url}")
        return _client
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        _client = None
        return None


async def close_redis_client() -> None:
    """Close the Redis client connection."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
        logger.info("Redis client closed")
