"""Webhook Deduplication and Idempotency Service.

Provides:
- Request deduplication using Redis or database
- Idempotency key validation
- Request fingerprinting
- Duplicate response caching
"""

import hashlib
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Tuple
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from core.config import settings

logger = get_logger(__name__)

# Default TTL for deduplication cache (24 hours)
DEDUPLICATION_TTL_SECONDS = 60 * 60 * 24


class WebhookDeduplicationService:
    """Service for webhook request deduplication and idempotency."""

    def __init__(self, session: AsyncSession, redis_client=None):
        """Initialize deduplication service.

        Args:
            session: Database session for fallback storage
            redis_client: Optional Redis client for distributed caching
        """
        self.session = session
        self.redis = redis_client
        self._memory_cache: Dict[str, Tuple[Any, float]] = {}

    def _generate_fingerprint(
        self,
        payload: bytes,
        headers: Dict[str, str],
        trigger_id: str,
    ) -> str:
        """Generate a unique fingerprint for the webhook request.

        Args:
            payload: Raw request payload
            headers: Request headers
            trigger_id: Webhook trigger ID

        Returns:
            SHA256 fingerprint hash
        """
        # Include relevant headers in fingerprint
        relevant_headers = {
            k: v for k, v in headers.items()
            if k.lower() in [
                'content-type',
                'x-signature',
                'x-event-type',
                'x-timestamp',
            ]
        }

        # Create fingerprint data
        fingerprint_data = {
            'trigger_id': trigger_id,
            'payload_hash': hashlib.sha256(payload).hexdigest(),
            'headers': relevant_headers,
        }

        # Generate fingerprint
        fingerprint_str = json.dumps(fingerprint_data, sort_keys=True)
        return hashlib.sha256(fingerprint_str.encode()).hexdigest()

    def _generate_idempotency_key(
        self,
        fingerprint: str,
        idempotency_header: Optional[str] = None,
    ) -> str:
        """Generate idempotency key.

        Args:
            fingerprint: Request fingerprint
            idempotency_header: Optional idempotency key from header

        Returns:
            Idempotency key
        """
        if idempotency_header:
            return f"webhook:idempotency:{idempotency_header}"
        return f"webhook:fingerprint:{fingerprint}"

    async def check_duplicate(
        self,
        payload: bytes,
        headers: Dict[str, str],
        trigger_id: str,
        idempotency_key: Optional[str] = None,
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Check if this webhook request is a duplicate.

        Args:
            payload: Raw request payload
            headers: Request headers
            trigger_id: Webhook trigger ID
            idempotency_key: Optional explicit idempotency key

        Returns:
            Tuple of (is_duplicate, cached_response)
        """
        # Generate fingerprint
        fingerprint = self._generate_fingerprint(payload, headers, trigger_id)
        
        # Generate idempotency key
        idem_key = self._generate_idempotency_key(fingerprint, idempotency_key)

        # Check Redis first (if available)
        if self.redis:
            cached = await self._check_redis(idem_key)
            if cached is not None:
                logger.info(f"Webhook duplicate found in Redis: {idem_key}")
                return True, cached

        # Check memory cache
        cached = self._check_memory(idem_key)
        if cached is not None:
            logger.info(f"Webhook duplicate found in memory: {idem_key}")
            return True, cached

        # Check database
        cached = await self._check_database(idem_key)
        if cached is not None:
            logger.info(f"Webhook duplicate found in database: {idem_key}")
            return True, cached

        return False, None

    async def record_request(
        self,
        payload: bytes,
        headers: Dict[str, str],
        trigger_id: str,
        response: Dict[str, Any],
        idempotency_key: Optional[str] = None,
        ttl_seconds: int = DEDUPLICATION_TTL_SECONDS,
    ) -> str:
        """Record a webhook request for deduplication.

        Args:
            payload: Raw request payload
            headers: Request headers
            trigger_id: Webhook trigger ID
            response: Response to cache
            idempotency_key: Optional explicit idempotency key
            ttl_seconds: Time-to-live for the record

        Returns:
            The idempotency key used
        """
        # Generate fingerprint
        fingerprint = self._generate_fingerprint(payload, headers, trigger_id)
        
        # Generate idempotency key
        idem_key = self._generate_idempotency_key(fingerprint, idempotency_key)

        # Store in Redis (if available)
        if self.redis:
            await self._store_redis(idem_key, response, ttl_seconds)

        # Store in memory cache
        self._store_memory(idem_key, response, ttl_seconds)

        # Store in database
        await self._store_database(idem_key, trigger_id, response, ttl_seconds)

        logger.info(f"Recorded webhook request: {idem_key}")
        return idem_key

    async def _check_redis(self, key: str) -> Optional[Dict[str, Any]]:
        """Check Redis for cached response."""
        if not self.redis:
            return None
        try:
            cached = await self.redis.get(key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Redis check failed: {e}")
        return None

    async def _store_redis(
        self,
        key: str,
        response: Dict[str, Any],
        ttl_seconds: int,
    ) -> None:
        """Store response in Redis."""
        if not self.redis:
            return
        try:
            await self.redis.setex(
                key,
                ttl_seconds,
                json.dumps(response),
            )
        except Exception as e:
            logger.warning(f"Redis store failed: {e}")

    def _check_memory(self, key: str) -> Optional[Dict[str, Any]]:
        """Check memory cache for cached response."""
        if key in self._memory_cache:
            response, expires_at = self._memory_cache[key]
            if time.time() < expires_at:
                return response
            else:
                # Expired, remove from cache
                del self._memory_cache[key]
        return None

    def _store_memory(
        self,
        key: str,
        response: Dict[str, Any],
        ttl_seconds: int,
    ) -> None:
        """Store response in memory cache."""
        expires_at = time.time() + ttl_seconds
        self._memory_cache[key] = (response, expires_at)

        # Cleanup expired entries
        self._cleanup_memory_cache()

    def _cleanup_memory_cache(self) -> None:
        """Remove expired entries from memory cache."""
        current_time = time.time()
        expired_keys = [
            k for k, (_, expires_at) in self._memory_cache.items()
            if current_time >= expires_at
        ]
        for key in expired_keys:
            del self._memory_cache[key]

    async def _check_database(self, key: str) -> Optional[Dict[str, Any]]:
        """Check database for cached response."""
        from models.trigger import TriggerInvocationModel

        try:
            stmt = select(TriggerInvocationModel).where(
                and_(
                    TriggerInvocationModel.idempotency_key == key,
                    TriggerInvocationModel.created_at > datetime.now(timezone.utc) - timedelta(hours=24),
                )
            )
            result = await self.session.execute(stmt)
            invocation = result.scalar_one_or_none()

            if invocation and invocation.result:
                return invocation.result
        except Exception as e:
            logger.warning(f"Database check failed: {e}")
        return None

    async def _store_database(
        self,
        key: str,
        trigger_id: str,
        response: Dict[str, Any],
        ttl_seconds: int,
    ) -> None:
        """Store response in database."""
        from models.trigger import TriggerInvocationModel

        try:
            invocation = TriggerInvocationModel(
                trigger_id=trigger_id,
                idempotency_key=key,
                status="completed",
                result=response,
            )
            self.session.add(invocation)
            await self.session.commit()
        except Exception as e:
            logger.warning(f"Database store failed: {e}")
            await self.session.rollback()


class WebhookIdempotencyMiddleware:
    """Middleware for webhook idempotency validation."""

    def __init__(self, session_factory, redis_client=None):
        """Initialize middleware.

        Args:
            session_factory: Database session factory
            redis_client: Optional Redis client
        """
        self.session_factory = session_factory
        self.redis = redis_client

    async def process_webhook(
        self,
        trigger_id: str,
        payload: bytes,
        headers: Dict[str, str],
        handler_func,
    ) -> Tuple[bool, Dict[str, Any]]:
        """Process a webhook request with idempotency check.

        Args:
            trigger_id: Webhook trigger ID
            payload: Raw request payload
            headers: Request headers
            handler_func: Async function to handle the webhook

        Returns:
            Tuple of (was_duplicate, response)
        """
        # Get idempotency key from header
        idempotency_key = headers.get('X-Idempotency-Key')

        async with self.session_factory() as session:
            service = WebhookDeduplicationService(session, self.redis)

            # Check for duplicate
            is_duplicate, cached_response = await service.check_duplicate(
                payload,
                headers,
                trigger_id,
                idempotency_key,
            )

            if is_duplicate:
                logger.info(
                    f"Returning cached response for duplicate webhook: {trigger_id}"
                )
                return True, cached_response

            # Process the webhook
            response = await handler_func()

            # Record the request
            await service.record_request(
                payload,
                headers,
                trigger_id,
                response,
                idempotency_key,
            )

            return False, response


def generate_webhook_signature(payload: bytes, secret: str) -> str:
    """Generate HMAC signature for webhook payload.

    Args:
        payload: Raw payload bytes
        secret: Webhook secret key

    Returns:
        Base64-encoded signature
    """
    import base64

    signature = hashlib.sha256(
        secret.encode('utf-8') + payload
    ).digest()
    return base64.b64encode(signature).decode('utf-8')


def verify_webhook_signature(
    payload: bytes,
    signature: str,
    secret: str,
    timestamp: Optional[str] = None,
    tolerance_seconds: int = 300,
) -> bool:
    """Verify webhook signature with optional timestamp validation.

    Args:
        payload: Raw payload bytes
        signature: Provided signature
        secret: Webhook secret key
        timestamp: Optional timestamp for replay attack prevention
        tolerance_seconds: Maximum age of request in seconds

    Returns:
        True if signature is valid
    """
    import hmac
    import base64

    # Check timestamp if provided
    if timestamp:
        try:
            request_time = int(timestamp)
            current_time = int(time.time())
            if abs(current_time - request_time) > tolerance_seconds:
                logger.warning(
                    f"Webhook timestamp too old: {request_time} vs {current_time}"
                )
                return False
        except ValueError:
            logger.warning(f"Invalid webhook timestamp: {timestamp}")
            return False

    # Verify signature
    try:
        expected = hmac.new(
            secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).digest()

        provided = base64.b64decode(signature)
        return hmac.compare_digest(expected, provided)
    except Exception as e:
        logger.error(f"Signature verification failed: {e}")
        return False
