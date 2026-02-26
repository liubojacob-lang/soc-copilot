"""Rate limiting middleware for API endpoints.

Prevents brute force attacks on sensitive endpoints like API key verification.

v0.8.5: Refactored to use async Redis client with connection pool.
- Replaced synchronous redis.Redis with redis.asyncio
- Added connection pool support for better resource management
- Added health check and auto-reconnect mechanism
- Fixed event loop blocking issue in high-concurrency scenarios
"""

from functools import wraps
from typing import Callable, Optional
from datetime import datetime, timedelta

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.logger import get_logger
from core.config import settings
from models.api_key import APIKeyModel

logger = get_logger(__name__)

# Check if Redis is available
try:
    import redis.asyncio as aioredis
    from redis.asyncio import ConnectionPool
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    aioredis = None
    ConnectionPool = None


class AsyncRateLimiter:
    """Async rate limiter using Redis or in-memory storage.
    
    Features:
    - Async Redis client with connection pool
    - Automatic fallback to in-memory storage
    - Health check and auto-reconnect
    - Non-blocking operations for high concurrency
    """

    def __init__(self):
        self._redis_client: Optional[aioredis.Redis] = None
        self._connection_pool: Optional[ConnectionPool] = None
        self._in_memory_store: dict = {}  # Fallback for development
        self._enabled: bool = settings.redis_enabled and REDIS_AVAILABLE
        self._healthy: bool = False
        self._last_health_check: Optional[datetime] = None
        
    async def _init_redis(self) -> bool:
        """Initialize async Redis client with connection pool.
        
        Returns:
            True if Redis connection is successful, False otherwise.
        """
        if not self._enabled:
            logger.info("Redis rate limiter disabled by configuration")
            return False
            
        if not REDIS_AVAILABLE:
            logger.warning("Redis package not installed, using in-memory rate limiter")
            return False
            
        try:
            # Create connection pool for better resource management
            self._connection_pool = ConnectionPool.from_url(
                settings.redis_url,
                decode_responses=True,
                max_connections=20,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
            )
            
            self._redis_client = aioredis.Redis(connection_pool=self._connection_pool)
            
            # Test connection
            await self._redis_client.ping()
            self._healthy = True
            self._last_health_check = datetime.now()
            logger.info(f"Async Redis rate limiter initialized: {settings.redis_url}")
            return True
            
        except Exception as e:
            logger.warning(f"Redis connection failed, using in-memory rate limiter: {e}")
            self._healthy = False
            self._redis_client = None
            self._connection_pool = None
            return False
    
    async def _ensure_connection(self) -> bool:
        """Ensure Redis connection is available, reconnect if needed.
        
        Returns:
            True if connected, False otherwise.
        """
        if not self._enabled:
            return False
            
        # Check if we need to reconnect
        if self._redis_client is None:
            return await self._init_redis()
            
        # Periodic health check (every 30 seconds)
        now = datetime.now()
        if self._last_health_check and (now - self._last_health_check).total_seconds() > 30:
            try:
                await self._redis_client.ping()
                self._healthy = True
                self._last_health_check = now
            except Exception as e:
                logger.warning(f"Redis health check failed: {e}")
                self._healthy = False
                # Try to reconnect
                await self._close_redis()
                return await self._init_redis()
                
        return self._healthy
    
    async def _close_redis(self):
        """Close Redis connection gracefully."""
        if self._redis_client:
            try:
                await self._redis_client.aclose()
            except Exception:
                pass
            self._redis_client = None
            
        if self._connection_pool:
            try:
                await self._connection_pool.aclose()
            except Exception:
                pass
            self._connection_pool = None
            
        self._healthy = False

    def _get_key(self, identifier: str, endpoint: str) -> str:
        """Generate rate limit key."""
        return f"rate_limit:{endpoint}:{identifier}"

    async def is_allowed(
        self,
        identifier: str,
        endpoint: str,
        max_requests: int = 10,
        window_seconds: int = 60
    ) -> tuple[bool, dict]:
        """Check if request is allowed under rate limit.

        Args:
            identifier: Unique identifier (IP address, API key prefix, etc.)
            endpoint: Endpoint name for namespacing
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds

        Returns:
            Tuple of (allowed, info_dict)
            - allowed: True if under limit, False otherwise
            - info_dict: Contains limit, remaining, reset time
        """
        key = self._get_key(identifier, endpoint)
        current_time = datetime.now()
        window_start = current_time - timedelta(seconds=window_seconds)

        # Try Redis first
        if await self._ensure_connection():
            return await self._check_redis(key, max_requests, window_seconds)
        else:
            # Fallback to in-memory
            return self._check_in_memory(key, max_requests, window_seconds, window_start)

    async def _check_redis(
        self,
        key: str,
        max_requests: int,
        window_seconds: int
    ) -> tuple[bool, dict]:
        """Check rate limit using async Redis.
        
        Uses Redis pipeline for atomic operations.
        """
        try:
            # Use async pipeline for atomic operations
            async with self._redis_client.pipeline(transaction=True) as pipe:
                pipe.incr(key)
                pipe.expire(key, window_seconds)
                results = await pipe.execute()

            current_count = results[0]
            remaining = max(0, max_requests - current_count)

            if current_count > max_requests:
                ttl = await self._redis_client.ttl(key)
                return False, {
                    "limit": max_requests,
                    "remaining": 0,
                    "reset": max(0, ttl)
                }

            return True, {
                "limit": max_requests,
                "remaining": remaining,
                "reset": window_seconds
            }
        except Exception as e:
            logger.error(f"Redis rate limit check failed: {e}")
            self._healthy = False
            # Fallback to allow request if Redis fails (fail-open)
            return True, {"limit": max_requests, "remaining": max_requests, "reset": window_seconds}

    def _check_in_memory(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
        window_start: datetime
    ) -> tuple[bool, dict]:
        """Check rate limit using in-memory store."""
        current_time = datetime.now()

        # Clean old entries periodically (prevent memory leak)
        if len(self._in_memory_store) > 10000:
            self._in_memory_store = {
                k: v for k, v in self._in_memory_store.items()
                if v['first_seen'] > window_start
            }

        if key not in self._in_memory_store:
            self._in_memory_store[key] = {
                'count': 1,
                'first_seen': current_time
            }
            return True, {"limit": max_requests, "remaining": max_requests - 1, "reset": window_seconds}

        record = self._in_memory_store[key]

        # Reset if window expired
        if record['first_seen'] < window_start:
            record['count'] = 1
            record['first_seen'] = current_time
            return True, {"limit": max_requests, "remaining": max_requests - 1, "reset": window_seconds}

        # Increment count
        record['count'] += 1

        if record['count'] > max_requests:
            # Calculate reset time
            reset_seconds = (record['first_seen'] + timedelta(seconds=window_seconds) - current_time).total_seconds()
            return False, {
                "limit": max_requests,
                "remaining": 0,
                "reset": int(max(0, reset_seconds))
            }

        remaining = max_requests - record['count']
        return True, {"limit": max_requests, "remaining": remaining, "reset": window_seconds}

    async def reset(self, identifier: str, endpoint: str):
        """Reset rate limit for identifier (admin use)."""
        key = self._get_key(identifier, endpoint)

        if await self._ensure_connection():
            try:
                await self._redis_client.delete(key)
            except Exception as e:
                logger.error(f"Failed to reset rate limit in Redis: {e}")
        else:
            if key in self._in_memory_store:
                del self._in_memory_store[key]
    
    async def close(self):
        """Close Redis connection gracefully. Call on application shutdown."""
        await self._close_redis()
        logger.info("Rate limiter Redis connection closed")


# Global rate limiter instance (lazy initialization)
_rate_limiter: Optional[AsyncRateLimiter] = None


def get_rate_limiter() -> AsyncRateLimiter:
    """Get or create rate limiter singleton instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = AsyncRateLimiter()
    return _rate_limiter


# For backward compatibility
rate_limiter = None  # Will be initialized lazily


async def init_rate_limiter():
    """Initialize rate limiter on application startup."""
    global rate_limiter
    rate_limiter = get_rate_limiter()
    await rate_limiter._init_redis()
    return rate_limiter


async def close_rate_limiter():
    """Close rate limiter on application shutdown."""
    global _rate_limiter
    if _rate_limiter:
        await _rate_limiter.close()
        _rate_limiter = None


async def check_api_key_rate_limit(
    api_key_prefix: str,
    session: AsyncSession
) -> tuple[bool, dict]:
    """Check API key rate limit.

    Args:
        api_key_prefix: First 8 characters of API key
        session: Database session

    Returns:
        Tuple of (allowed, info_dict)
    """
    limiter = get_rate_limiter()
    
    # Check if API key has custom rate limit
    result = await session.execute(
        select(APIKeyModel).where(APIKeyModel.key_prefix == api_key_prefix)
    )
    api_key = result.scalar_one_or_none()

    # Rate limit settings
    if api_key and hasattr(api_key, 'rate_limit') and api_key.rate_limit:
        max_requests = api_key.rate_limit
    else:
        max_requests = 10  # Default: 10 requests per minute

    window_seconds = 60  # 1 minute window

    return await limiter.is_allowed(
        identifier=api_key_prefix,
        endpoint="api_key_verification",
        max_requests=max_requests,
        window_seconds=window_seconds
    )


def rate_limit(max_requests: int = 10, window_seconds: int = 60):
    """Decorator for rate limiting endpoints.

    Args:
        max_requests: Maximum requests per window
        window_seconds: Time window in seconds

    Example:
        @app.post("/api/sensitive")
        @rate_limit(max_requests=5, window_seconds=60)
        async def sensitive_endpoint():
            return {"status": "ok"}
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from kwargs
            request = kwargs.get('request')
            if not request:
                return await func(*args, **kwargs)

            # Get identifier (IP address or API key)
            identifier = request.client.host if request.client else "unknown"

            # Check rate limit
            limiter = get_rate_limiter()
            allowed, info = await limiter.is_allowed(
                identifier=identifier,
                endpoint=request.url.path,
                max_requests=max_requests,
                window_seconds=window_seconds
            )

            if not allowed:
                logger.warning(f"Rate limit exceeded for {identifier} on {request.url.path}")

                # Add rate limit headers
                headers = {
                    "X-RateLimit-Limit": str(info["limit"]),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(info["reset"]),
                    "Retry-After": str(info["reset"])
                }

                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests. Please slow down.",
                    headers=headers
                )

            # Add rate limit headers to response
            response = await func(*args, **kwargs)
            if hasattr(response, 'headers'):
                response.headers["X-RateLimit-Limit"] = str(info["limit"])
                response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
                response.headers["X-RateLimit-Reset"] = str(info["reset"])

            return response

        return wrapper
    return decorator
