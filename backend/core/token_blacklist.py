"""
Token blacklist management module with Redis support.

This module provides:
- Token blacklist for JWT revocation
- Redis backend for distributed deployments
- In-memory fallback for single-instance deployments
- Idempotency key support for preventing duplicate requests
"""

import asyncio
import hashlib
import json
from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status

from core.config import settings
from core.logger import get_logger
from core.security import decode_token

logger = get_logger(__name__)

# Try to import redis, fall back gracefully if not available
try:
    import redis.asyncio as redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis package not available, using in-memory fallback")


class TokenBlacklistBackend(ABC):
    """Abstract backend for token blacklist storage."""

    @abstractmethod
    async def add(self, token: str, ttl: int, reason: str = "logged out") -> bool:
        """Add token to blacklist with TTL."""
        pass

    @abstractmethod
    async def contains(self, token: str) -> bool:
        """Check if token is blacklisted."""
        pass

    @abstractmethod
    async def remove(self, token: str) -> bool:
        """Remove token from blacklist."""
        pass

    @abstractmethod
    async def get_info(self) -> dict:
        """Get backend info."""
        pass


class InMemoryBackend(TokenBlacklistBackend):
    """In-memory token blacklist backend for single-instance deployments."""

    def __init__(self):
        self._blacklist: dict[str, datetime] = {}
        self._lock = asyncio.Lock()

    async def add(self, token: str, ttl: int, reason: str = "logged out") -> bool:
        """Add token with expiration time."""
        async with self._lock:
            expires_at = datetime.now(UTC) + timedelta(seconds=ttl)
            self._blacklist[token] = expires_at
            logger.info(f"Token added to in-memory blacklist: {reason}")
            return True

    async def contains(self, token: str) -> bool:
        """Check if token is blacklisted and not expired."""
        async with self._lock:
            if token not in self._blacklist:
                return False

            expires_at = self._blacklist[token]
            if datetime.now(UTC) > expires_at:
                del self._blacklist[token]
                return False

            return True

    async def remove(self, token: str) -> bool:
        """Remove token from blacklist."""
        async with self._lock:
            if token in self._blacklist:
                del self._blacklist[token]
                return True
            return False

    async def get_info(self) -> dict:
        """Get blacklist info."""
        async with self._lock:
            # Clean expired entries
            now = datetime.now(UTC)
            expired = [t for t, exp in self._blacklist.items() if now > exp]
            for t in expired:
                del self._blacklist[t]

            # Never return raw token strings: this dict is exposed via the
            # health endpoint and revoked JWTs must stay confidential.
            return {
                "backend": "memory",
                "count": len(self._blacklist),
            }


class RedisBackend(TokenBlacklistBackend):
    """Redis-backed token blacklist backend for distributed deployments."""

    def __init__(self, redis_url: str, key_prefix: str = "token_blacklist:"):
        self._redis_url = redis_url
        self._key_prefix = key_prefix
        self._redis: redis.Redis | None = None
        self._connected = False

    def _hash_token(self, token: str) -> str:
        """Hash token for storage key (security)."""
        return hashlib.sha256(token.encode()).hexdigest()[:32]

    async def _get_redis(self) -> redis.Redis | None:
        """Get Redis connection, reconnect if needed."""
        if self._redis is None:
            try:
                self._redis = redis.from_url(
                    self._redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                )
                # Test connection
                await self._redis.ping()
                self._connected = True
                logger.info("Connected to Redis for token blacklist")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                self._connected = False
                return None
        return self._redis

    async def add(self, token: str, ttl: int, reason: str = "logged out") -> bool:
        """Add token to Redis with TTL."""
        try:
            r = await self._get_redis()
            if r is None:
                return False

            key = f"{self._key_prefix}{self._hash_token(token)}"
            await r.setex(
                key,
                ttl,
                json.dumps(
                    {
                        "reason": reason,
                        "blacklisted_at": datetime.now(UTC).isoformat(),
                    }
                ),
            )
            logger.info(f"Token added to Redis blacklist: {reason}")
            return True
        except Exception as e:
            logger.error(f"Failed to add token to Redis: {e}")
            return False

    async def contains(self, token: str) -> bool:
        """Check if token is in Redis blacklist."""
        try:
            r = await self._get_redis()
            if r is None:
                return False

            key = f"{self._key_prefix}{self._hash_token(token)}"
            return await r.exists(key) > 0
        except Exception as e:
            logger.error(f"Failed to check token in Redis: {e}")
            return False

    async def remove(self, token: str) -> bool:
        """Remove token from Redis blacklist."""
        try:
            r = await self._get_redis()
            if r is None:
                return False

            key = f"{self._key_prefix}{self._hash_token(token)}"
            return await r.delete(key) > 0
        except Exception as e:
            logger.error(f"Failed to remove token from Redis: {e}")
            return False

    async def get_info(self) -> dict:
        """Get Redis blacklist info."""
        try:
            r = await self._get_redis()
            if r is None:
                return {"backend": "redis", "connected": False, "count": 0}

            # Count keys with prefix
            keys = []
            async for key in r.scan_iter(match=f"{self._key_prefix}*"):
                keys.append(key)

            return {
                "backend": "redis",
                "connected": self._connected,
                "count": len(keys),
                "keys": keys[:10],
            }
        except Exception as e:
            return {"backend": "redis", "connected": False, "error": str(e)}


class TokenBlacklist:
    """Token blacklist manager with Redis support and in-memory fallback."""

    def __init__(self, redis_url: str | None = None):
        """Initialize token blacklist with optional Redis backend.

        Args:
            redis_url: Redis connection URL (e.g., redis://localhost:6379/0)
        """
        self._primary_backend: TokenBlacklistBackend | None = None
        self._fallback_backend = InMemoryBackend()
        self._use_redis = False
        self._is_production = settings.environment == "production"

        if redis_url and REDIS_AVAILABLE:
            self._primary_backend = RedisBackend(redis_url)
            self._use_redis = True
            logger.info("Token blacklist initialized with Redis backend")
        else:
            if self._is_production:
                logger.critical(
                    "Token blacklist: Redis is REQUIRED in production but not initialized. "
                    "Token revocation will NOT work across multiple workers."
                )
            logger.info("Token blacklist initialized with in-memory backend")

    async def add_to_blacklist(
        self,
        token: str,
        reason: str = "logged out",
        ttl: int | None = None,
    ) -> bool:
        """Add token to blacklist.

        Args:
            token: JWT token to blacklist
            reason: Reason for blacklisting
            ttl: Time-to-live in seconds (default: from token exp claim)

        Returns:
            True if successfully added
        """
        # Get TTL from token if not provided
        if ttl is None:
            payload = decode_token(token)
            if payload and "exp" in payload:
                exp = payload["exp"]
                now = datetime.now(UTC).timestamp()
                ttl = max(int(exp - now), 60)  # At least 60 seconds
            else:
                ttl = 86400  # Default 24 hours

        # Try primary backend first
        if self._primary_backend:
            success = await self._primary_backend.add(token, ttl, reason)
            if success:
                return True
            # Primary backend failed
            if self._is_production:
                logger.critical(
                    "CRITICAL: Redis backend failed to add token to blacklist. "
                    "Refusing to fall back to InMemoryBackend in production — "
                    "this would cause inconsistent token state across multiple workers. "
                    f"Token prefix: {token[:20]}..., reason: {reason}"
                )
                raise RuntimeError(
                    "Token blacklist operation failed: Redis backend unavailable in production. "
                    "Token revocation cannot proceed with InMemoryBackend in multi-worker setup."
                )

        # Fallback to in-memory (development only)
        logger.warning(
            "⚠️  Token blacklist falling back to InMemoryBackend. "
            "This is NOT safe in multi-worker deployments — tokens may not be "
            "consistently revoked across all workers. "
            f"Token prefix: {token[:20]}..., reason: {reason}"
        )
        return await self._fallback_backend.add(token, ttl, reason)

    async def is_blacklisted(self, token: str) -> bool:
        """Check if token is blacklisted."""
        # Check primary backend first (fail-closed in production)
        if self._primary_backend:
            try:
                if await self._primary_backend.contains(token):
                    return True
            except Exception as e:
                if self._is_production:
                    logger.critical(
                        "CRITICAL: Redis backend failed during blacklist check. "
                        "Failing closed — refusing to authenticate token that cannot "
                        "be verified against the centralized blacklist. "
                        f"Error: {e}"
                    )
                    raise RuntimeError(
                        "Token blacklist check failed: Redis backend unavailable in production. "
                        "Cannot verify token status without centralized blacklist."
                    )
                logger.warning(
                    f"Redis backend error during blacklist check, falling back to in-memory: {e}"
                )

        # Fallback to in-memory (development only)
        logger.debug("Checking in-memory blacklist (single-worker fallback)")
        return await self._fallback_backend.contains(token)

    async def remove_from_blacklist(self, token: str) -> bool:
        """Remove token from blacklist."""
        success = False
        primary_failed = False

        if self._primary_backend:
            try:
                success = await self._primary_backend.remove(token)
            except Exception as e:
                primary_failed = True
                if self._is_production:
                    logger.critical(
                        "CRITICAL: Redis backend failed to remove token from blacklist. "
                        "Failing closed — inconsistent blacklist state in multi-worker setup. "
                        f"Error: {e}"
                    )
                    raise RuntimeError(
                        "Token blacklist removal failed: Redis backend unavailable in production. "
                        "Cannot reliably remove token without centralized blacklist."
                    )
                logger.warning(
                    f"Redis backend error during blacklist removal, falling back to in-memory: {e}"
                )

        if primary_failed or not self._primary_backend:
            logger.debug(
                "Using in-memory blacklist for token removal (single-worker fallback)"
            )
            success = await self._fallback_backend.remove(token) or success
        return success

    async def get_blacklist_info(self) -> dict:
        """Get blacklist info for debugging."""
        return {
            "redis_available": REDIS_AVAILABLE and self._use_redis,
            "primary": (
                await self._primary_backend.get_info()
                if self._primary_backend
                else None
            ),
            "fallback": await self._fallback_backend.get_info(),
        }


# Global token blacklist instance
_token_blacklist: TokenBlacklist | None = None


def get_token_blacklist() -> TokenBlacklist:
    """Get global token blacklist instance."""
    global _token_blacklist
    if _token_blacklist is None:
        # Get Redis URL from settings if configured
        redis_url = getattr(settings, "redis_url", None)
        _token_blacklist = TokenBlacklist(redis_url)
    return _token_blacklist


async def verify_token_not_blacklisted(token: str) -> bool:
    """Verify token is not blacklisted.

    Raises:
        HTTPException: If token is blacklisted
    """
    blacklist = get_token_blacklist()

    if await blacklist.is_blacklisted(token):
        logger.warning(f"Blacklisted token attempted: {token[:20]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked. Please login again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return True


async def add_token_to_blacklist(token: str, reason: str = "logged out") -> bool:
    """Add token to blacklist."""
    blacklist = get_token_blacklist()
    return await blacklist.add_to_blacklist(token, reason)


async def remove_token_from_blacklist(token: str) -> bool:
    """Remove token from blacklist."""
    blacklist = get_token_blacklist()
    return await blacklist.remove_from_blacklist(token)


class IdempotencyKeyStore:
    """Store for idempotency keys to prevent duplicate requests.

    Supports both Redis and in-memory backends.
    """

    def __init__(self, redis_url: str | None = None):
        """Initialize idempotency key store.

        Args:
            redis_url: Optional Redis URL for distributed deployments
        """
        self._memory_store: dict[str, dict] = {}
        self._redis: redis.Redis | None = None
        self._key_prefix = "idempotency:"
        self._lock = asyncio.Lock()

        if redis_url and REDIS_AVAILABLE:
            try:
                self._redis = redis.from_url(
                    redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                )
                logger.info("Idempotency key store initialized with Redis")
            except Exception as e:
                logger.warning(f"Failed to init Redis for idempotency: {e}")

    async def check_and_set(
        self,
        key: str,
        user_id: str,
        ttl: int = 86400,  # 24 hours default
    ) -> dict | None:
        """Check if key exists and set if not.

        Args:
            key: Idempotency key from client
            user_id: User ID for additional validation
            ttl: Time-to-live in seconds

        Returns:
            Previous response if key exists, None if key was set
        """
        full_key = f"{self._key_prefix}{user_id}:{key}"

        # Check Redis first
        if self._redis:
            try:
                existing = await self._redis.get(full_key)
                if existing:
                    return json.loads(existing)
            except Exception as e:
                logger.error(f"Redis error in idempotency check: {e}")

        # Check memory store
        async with self._lock:
            if full_key in self._memory_store:
                entry = self._memory_store[full_key]
                if datetime.now(UTC) < entry["expires_at"]:
                    return entry["response"]
                else:
                    del self._memory_store[full_key]

        return None

    async def set_response(
        self,
        key: str,
        user_id: str,
        response: dict,
        ttl: int = 86400,
    ) -> None:
        """Store response for idempotency key.

        Args:
            key: Idempotency key
            user_id: User ID
            response: Response to cache
            ttl: Time-to-live in seconds
        """
        full_key = f"{self._key_prefix}{user_id}:{key}"
        expires_at = datetime.now(UTC) + timedelta(seconds=ttl)

        # Store in Redis
        if self._redis:
            try:
                await self._redis.setex(
                    full_key,
                    ttl,
                    json.dumps(response),
                )
            except Exception as e:
                logger.error(f"Redis error storing idempotency key: {e}")

        # Also store in memory as backup
        async with self._lock:
            self._memory_store[full_key] = {
                "response": response,
                "expires_at": expires_at,
            }


# Global idempotency store
_idempotency_store: IdempotencyKeyStore | None = None


def get_idempotency_store() -> IdempotencyKeyStore:
    """Get global idempotency store instance."""
    global _idempotency_store
    if _idempotency_store is None:
        redis_url = getattr(settings, "redis_url", None)
        _idempotency_store = IdempotencyKeyStore(redis_url)
    return _idempotency_store
