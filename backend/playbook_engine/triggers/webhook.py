"""Webhook trigger handler with HMAC signature verification and deduplication."""

import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.logger import get_logger
from models.playbook_definition import PlaybookDefinitionModel, PlaybookTriggerModel

logger = get_logger(__name__)


class WebhookDeduplicationStore:
    """Store for webhook deduplication based on payload hash.

    Supports both Redis and in-memory backends for distributed deployments.
    """

    def __init__(self, redis_url: str | None = None):
        """Initialize deduplication store.

        Args:
            redis_url: Optional Redis URL for distributed deployments
        """
        self._memory_store: dict[str, dict] = {}
        self._redis = None
        self._key_prefix = "webhook_dedup:"
        self._lock = None

        # Try to use Redis if available
        if redis_url:
            try:
                import redis.asyncio as redis

                self._redis = redis.from_url(
                    redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                )
                logger.info("Webhook deduplication store initialized with Redis")
            except Exception as e:
                logger.warning(f"Failed to init Redis for webhook dedup: {e}")

        import asyncio

        self._lock = asyncio.Lock()

    def _compute_payload_hash(self, trigger_id: str, payload: bytes) -> str:
        """Compute hash for payload deduplication.

        Args:
            trigger_id: Trigger ID for scope
            payload: Raw payload bytes

        Returns:
            SHA256 hash of trigger_id + payload
        """
        combined = f"{trigger_id}:{payload.hex()}"
        return hashlib.sha256(combined.encode()).hexdigest()[:32]

    async def check_and_mark(
        self,
        trigger_id: str,
        payload: bytes,
        ttl: int = 300,  # 5 minutes default dedup window
    ) -> dict[str, Any] | None:
        """Check if payload was recently processed and mark as processing.

        Args:
            trigger_id: Trigger ID
            payload: Raw payload bytes
            ttl: Deduplication window in seconds

        Returns:
            Previous run info if duplicate, None if new
        """
        payload_hash = self._compute_payload_hash(trigger_id, payload)
        full_key = f"{self._key_prefix}{payload_hash}"

        # Check Redis first
        if self._redis:
            try:
                existing = await self._redis.get(full_key)
                if existing:
                    logger.info(
                        f"Duplicate webhook detected (Redis): {payload_hash[:16]}..."
                    )
                    return json.loads(existing)
            except Exception as e:
                logger.error(f"Redis error in webhook dedup check: {e}")

        # Check memory store
        async with self._lock:
            if full_key in self._memory_store:
                entry = self._memory_store[full_key]
                if datetime.now(UTC) < entry["expires_at"]:
                    logger.info(
                        f"Duplicate webhook detected (memory): {payload_hash[:16]}..."
                    )
                    return entry["run_info"]
                else:
                    del self._memory_store[full_key]

        return None

    async def mark_processed(
        self,
        trigger_id: str,
        payload: bytes,
        run_info: dict[str, Any],
        ttl: int = 300,
    ) -> None:
        """Mark payload as processed.

        Args:
            trigger_id: Trigger ID
            payload: Raw payload bytes
            run_info: Run information to cache
            ttl: Deduplication window in seconds
        """
        payload_hash = self._compute_payload_hash(trigger_id, payload)
        full_key = f"{self._key_prefix}{payload_hash}"
        expires_at = datetime.now(UTC) + timedelta(seconds=ttl)

        # Store in Redis
        if self._redis:
            try:
                await self._redis.setex(
                    full_key,
                    ttl,
                    json.dumps(run_info),
                )
            except Exception as e:
                logger.error(f"Redis error storing webhook dedup: {e}")

        # Also store in memory as backup
        async with self._lock:
            self._memory_store[full_key] = {
                "run_info": run_info,
                "expires_at": expires_at,
            }

        logger.debug(f"Webhook marked as processed: {payload_hash[:16]}...")


# Global deduplication store
_dedup_store: WebhookDeduplicationStore | None = None


def get_dedup_store() -> WebhookDeduplicationStore:
    """Get global webhook deduplication store instance."""
    global _dedup_store
    if _dedup_store is None:
        redis_url = getattr(settings, "redis_url", None)
        _dedup_store = WebhookDeduplicationStore(redis_url)
    return _dedup_store


def verify_hmac_signature(
    payload: bytes,
    signature: str,
    secret: str,
) -> bool:
    """Verify HMAC signature for webhook payload.

    Args:
        payload: Raw payload bytes
        signature: Base64-encoded signature from X-Signature header
        secret: Webhook secret key

    Returns:
        True if signature is valid, False otherwise
    """
    try:
        # Calculate expected signature
        expected = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).digest()

        # Decode provided signature
        provided = base64.b64decode(signature)

        # Timing-safe comparison
        return hmac.compare_digest(expected, provided)
    except Exception as e:
        logger.error(f"Failed to verify HMAC signature: {e}")
        return False


class WebhookHandler:
    """Handler for webhook-triggered playbook executions."""

    def __init__(self, session: AsyncSession):
        """Initialize the webhook handler.

        Args:
            session: Database session
        """
        self.session = session

    async def get_trigger(self, trigger_id: str) -> PlaybookTriggerModel | None:
        """Get a trigger configuration by ID.

        Args:
            trigger_id: Trigger ID

        Returns:
            Trigger model or None if not found
        """
        stmt = select(PlaybookTriggerModel).where(
            PlaybookTriggerModel.id == trigger_id,
            PlaybookTriggerModel.type == "webhook",
            PlaybookTriggerModel.is_active == True,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def check_idempotency(
        self,
        idempotency_key: str,
    ) -> bool:
        """Check if an idempotency key has already been processed.

        Args:
            idempotency_key: Unique key for this request

        Returns:
            True if key is unique (first time), False if already processed
        """
        from models.playbook_run import PlaybookRunModel

        stmt = select(PlaybookRunModel).where(
            PlaybookRunModel.idempotency_key == idempotency_key,
        )
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()

        return existing is None

    async def handle_webhook(
        self,
        trigger_id: str,
        payload: bytes,
        signature: str,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Handle an incoming webhook trigger.

        Args:
            trigger_id: Trigger ID
            payload: Raw request payload
            signature: HMAC signature from X-Signature header
            idempotency_key: Optional idempotency key from X-Idempotency-Key header

        Returns:
            Dictionary with run_id and status

        Raises:
            ValueError: If trigger not found or signature invalid
        """
        # Get trigger configuration
        trigger = await self.get_trigger(trigger_id)
        if not trigger:
            raise ValueError(f"Webhook trigger not found: {trigger_id}")

        # Verify signature
        secret = trigger.config_json.get("webhook_secret", "")
        if not verify_hmac_signature(payload, signature, secret):
            raise ValueError("Invalid HMAC signature")

        # v0.8.4: Check payload-based deduplication (automatic)
        dedup_store = get_dedup_store()
        dedup_ttl = trigger.config_json.get(
            "dedup_ttl_seconds", 300
        )  # Default 5 minutes
        dedup_enabled = trigger.config_json.get(
            "dedup_enabled", True
        )  # Enabled by default

        if dedup_enabled:
            existing_run = await dedup_store.check_and_mark(
                trigger_id, payload, dedup_ttl
            )
            if existing_run:
                logger.info(
                    f"Duplicate webhook payload detected for trigger {trigger_id}"
                )
                return {
                    "run_id": existing_run.get("run_id"),
                    "status": existing_run.get("status"),
                    "message": "Duplicate payload within dedup window, returning existing run",
                    "dedup": True,
                }

        # Check explicit idempotency key (client-provided)
        if idempotency_key:
            is_unique = await self.check_idempotency(idempotency_key)
            if not is_unique:
                logger.info(
                    f"Duplicate webhook request with idempotency key: {idempotency_key}"
                )
                # Return existing run instead of creating new one
                from models.playbook_run import PlaybookRunModel

                stmt = select(PlaybookRunModel).where(
                    PlaybookRunModel.idempotency_key == idempotency_key,
                )
                result = await self.session.execute(stmt)
                existing_run = result.scalar_one_or_none()
                if existing_run:
                    return {
                        "run_id": existing_run.id,
                        "status": existing_run.status,
                        "message": "Duplicate request, returning existing run",
                    }

        # Parse payload
        try:
            input_json = json.loads(payload.decode("utf-8"))
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON payload: {e}")

        # Get playbook definition
        stmt = select(PlaybookDefinitionModel).where(
            PlaybookDefinitionModel.id == trigger.definition_id,
        )
        result = await self.session.execute(stmt)
        definition = result.scalar_one_or_none()

        if not definition:
            raise ValueError(f"Playbook definition not found: {trigger.definition_id}")

        # Execute the playbook
        from .dag import DAGBuilder, DAGExecutionEngine

        dag_definition = DAGBuilder.from_json(definition.definition_json)
        engine = DAGExecutionEngine(self.session)

        # Create run record
        import uuid

        from models.playbook_run import PlaybookRunModel
        from repositories.playbook_run_repository import PlaybookRunRepository

        run_repo = PlaybookRunRepository(self.session)
        run_id = str(uuid.uuid4())

        await run_repo.create(
            playbook_name=f"webhook:{definition.name}",
            playbook_version=definition.version,
            mode="dry_run",
            status="running",
            created_by_user_id=None,
            input_json=input_json,
            output_json={},
            execution_mode="dag",
            definition_id=definition.id,
            idempotency_key=idempotency_key,
            trigger_source="webhook",
        )

        await self.session.flush()

        # v0.8.4: Mark payload as processed for deduplication
        if dedup_enabled:
            await dedup_store.mark_processed(
                trigger_id, payload, {"run_id": run_id, "status": "running"}, dedup_ttl
            )

        # Execute the DAG
        result = await engine.execute_dag(
            definition=dag_definition,
            run_id=run_id,
            input_json=input_json,
            mode="dry_run",
        )

        return {
            "run_id": run_id,
            "status": result["status"],
            "outputs": result.get("outputs", {}),
        }
