"""Run Queue Manager for execution concurrency control (v0.7.4).

This service manages the execution queue for playbook runs, providing:
- Concurrency control (max concurrent runs)
- FIFO queue policy for pending runs
- Orphaned run recovery after server restart
- Queue status monitoring
- Idempotency control to prevent duplicate task execution (P0-3 fix)
"""

import asyncio
import hashlib
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.playbook_run import PlaybookRunModel
from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)


class IdempotencyResult:
    """Result of idempotency check operation."""
    
    def __init__(
        self,
        is_unique: bool,
        existing_run_id: Optional[str] = None,
        existing_status: Optional[str] = None,
    ):
        self.is_unique = is_unique
        self.existing_run_id = existing_run_id
        self.existing_status = existing_status
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "is_unique": self.is_unique,
            "existing_run_id": self.existing_run_id,
            "existing_status": self.existing_status,
        }


# Global queue manager instance
_queue_manager: Optional["RunQueueManager"] = None

# In-memory idempotency cache for fast lookups (backed by DB for persistence)
# Format: {idempotency_key: (run_id, status, timestamp)}
_idempotency_cache: Dict[str, Tuple[str, str, datetime]] = {}

# Cache TTL in seconds (5 minutes)
IDEMPOTENCY_CACHE_TTL = 300


class RunQueueManager:
    """Manager for playbook run execution queue.

    This service controls the number of concurrently running playbooks
    and queues excess requests for FIFO processing.
    """

    def __init__(self, session_factory):
        """Initialize the queue manager.

        Args:
            session_factory: AsyncSessionLocal factory for DB access
        """
        self.session_factory = session_factory
        self.max_concurrent = settings.run_queue_max
        self.policy = settings.run_queue_policy
        self._processing_task: Optional[asyncio.Task] = None
        # Thread safety: lock for queue operations to prevent race conditions
        self._queue_lock = asyncio.Lock()

    async def recover_runs(self) -> int:
        """Recover orphaned runs from previous server session.

        Marks runs as failed if they were in 'running' state for more
        than 1 hour (likely interrupted by server restart).

        Returns:
            Number of orphaned runs recovered
        """
        async with self.session_factory() as session:
            # Find orphaned running runs (started > 1 hour ago with no finish time)
            cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
            stmt = select(PlaybookRunModel).where(
                and_(
                    PlaybookRunModel.status == "running",
                    PlaybookRunModel.started_at < cutoff,
                    PlaybookRunModel.finished_at.is_(None)
                )
            )
            result = await session.execute(stmt)
            orphaned = result.scalars().all()

            for run in orphaned:
                run.status = "failed"
                run.error_message = "Run interrupted by server restart"
                run.finished_at = datetime.now(timezone.utc)

            await session.commit()

            if orphaned:
                logger.warning(f"Recovered {len(orphaned)} orphaned runs from previous session")

            return len(orphaned)

    async def can_start_run(self) -> bool:
        """Check if a new run can be started immediately.

        Returns:
            True if concurrent limit not reached, False otherwise
        """
        async with self.session_factory() as session:
            stmt = select(func.count(PlaybookRunModel.id)).where(
                PlaybookRunModel.status == "running"
            )
            result = await session.execute(stmt)
            running_count = result.scalar() or 0

            has_capacity = running_count < self.max_concurrent

            if not has_capacity:
                logger.info(
                    f"Queue at capacity: {running_count}/{self.max_concurrent} running"
                )

            return has_capacity

    async def get_queue_stats(self) -> dict:
        """Get current queue statistics.

        Returns:
            Dictionary with running and queued counts
        """
        async with self.session_factory() as session:
            # Count running runs
            running_stmt = select(func.count(PlaybookRunModel.id)).where(
                PlaybookRunModel.status == "running"
            )
            running_result = await session.execute(running_stmt)
            running_count = running_result.scalar() or 0

            # Count queued runs
            queued_stmt = select(func.count(PlaybookRunModel.id)).where(
                PlaybookRunModel.status == "queued"
            )
            queued_result = await session.execute(queued_stmt)
            queued_count = queued_result.scalar() or 0

            return {
                "running": running_count,
                "queued": queued_count,
                "max_concurrent": self.max_concurrent,
                "has_capacity": running_count < self.max_concurrent,
            }

    async def process_queue(self) -> Optional[str]:
        """Process the queue and start the next pending run if capacity available.

        Returns:
            Run ID of started run, or None if queue is empty or at capacity
        """
        # Acquire lock to prevent race conditions when multiple calls happen concurrently
        async with self._queue_lock:
            if not await self.can_start_run():
                return None

            async with self.session_factory() as session:
                # Get oldest queued run (FIFO)
                stmt = select(PlaybookRunModel).where(
                    PlaybookRunModel.status == "queued"
                ).order_by(
                    PlaybookRunModel.queued_at
                ).limit(1)

                result = await session.execute(stmt)
                queued_run = result.scalar_one_or_none()

                if not queued_run:
                    return None

                # Update status to running
                queued_run.status = "running"
                queued_run.started_at = datetime.now(timezone.utc)

                await session.commit()

                logger.info(
                    f"Started queued run {queued_run.id} "
                    f"(playbook: {queued_run.playbook_name})"
                )

                # Trigger execution of the run
                # This will be handled by the caller
                return queued_run.id

    async def queue_run(self, run_id: str) -> None:
        """Add a run to the queue.

        Args:
            run_id: ID of the run to queue
        """
        async with self.session_factory() as session:
            stmt = select(PlaybookRunModel).where(
                PlaybookRunModel.id == run_id
            )
            result = await session.execute(stmt)
            run = result.scalar_one_or_none()

            if run:
                run.status = "queued"
                run.queued_at = datetime.now(timezone.utc)
                await session.commit()

                logger.info(f"Queued run {run_id} (playbook: {run.playbook_name})")

    async def start_background_processor(self) -> None:
        """Start background task to process queue continuously."""
        if self._processing_task is not None:
            return  # Already running

        async def process_loop():
            while True:
                try:
                    await self.process_queue()
                except Exception as e:
                    logger.error(f"Error processing queue: {e}")

                await asyncio.sleep(5)  # Check every 5 seconds

        self._processing_task = asyncio.create_task(process_loop())
        logger.info("Started queue processor background task")

    async def stop_background_processor(self) -> None:
        """Stop background queue processor."""
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
            self._processing_task = None
            logger.info("Stopped queue processor background task")

    # ==================== Idempotency Control Methods (P0-3) ====================

    def generate_idempotency_key(
        self,
        playbook_name: str,
        trigger_source: str,
        trigger_id: Optional[str] = None,
        input_hash: Optional[str] = None,
    ) -> str:
        """Generate a deterministic idempotency key for a playbook run.

        The key is based on:
        - Playbook name
        - Trigger source (webhook, manual, cron, alert)
        - Trigger ID (for webhooks/alerts)
        - Input data hash (optional, for dedup based on input)

        Args:
            playbook_name: Name of the playbook
            trigger_source: Source of the trigger
            trigger_id: Optional trigger identifier
            input_hash: Optional hash of input data

        Returns:
            A deterministic idempotency key
        """
        components = [playbook_name, trigger_source]
        if trigger_id:
            components.append(trigger_id)
        if input_hash:
            components.append(input_hash)

        key_string = ":".join(components)
        return hashlib.sha256(key_string.encode()).hexdigest()[:32]

    def compute_input_hash(self, input_data: Dict[str, Any]) -> str:
        """Compute a hash of input data for deduplication.

        Args:
            input_data: Input data dictionary

        Returns:
            Hash string of the input data
        """
        import json

        # Sort keys for deterministic serialization
        serialized = json.dumps(input_data, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()[:16]

    async def check_idempotency(
        self,
        idempotency_key: str,
        session: Optional[AsyncSession] = None,
        ttl_seconds: int = 300,
    ) -> IdempotencyResult:
        """Check if a run with the given idempotency key already exists.

        Uses a two-tier check:
        1. In-memory cache for fast lookups (with TTL)
        2. Database for persistence

        Args:
            idempotency_key: The idempotency key to check
            session: Optional database session (will create if not provided)
            ttl_seconds: Time-to-live for considering a run as duplicate

        Returns:
            IdempotencyResult with uniqueness status and existing run info
        """
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=ttl_seconds)

        # Check in-memory cache first (fast path)
        if idempotency_key in _idempotency_cache:
            run_id, status, timestamp = _idempotency_cache[idempotency_key]
            if timestamp > cutoff:
                logger.info(
                    f"Idempotency cache hit for key {idempotency_key[:8]}...: "
                    f"run_id={run_id}, status={status}"
                )
                return IdempotencyResult(
                    is_unique=False,
                    existing_run_id=run_id,
                    existing_status=status,
                )

        # Check database for persistence
        async def _check_db(db_session: AsyncSession) -> IdempotencyResult:
            # Look for runs with matching idempotency key in input_json
            # or matching trigger_id within the TTL window
            stmt = select(PlaybookRunModel).where(
                and_(
                    PlaybookRunModel.input_json["_idempotency_key"].as_string() == idempotency_key,
                    PlaybookRunModel.started_at > cutoff,
                    PlaybookRunModel.status.in_(["running", "queued", "completed"]),
                )
            ).limit(1)

            result = await db_session.execute(stmt)
            existing_run = result.scalar_one_or_none()

            if existing_run:
                # Update cache
                _idempotency_cache[idempotency_key] = (
                    existing_run.id,
                    existing_run.status,
                    existing_run.started_at or now,
                )
                logger.info(
                    f"Idempotency DB hit for key {idempotency_key[:8]}...: "
                    f"run_id={existing_run.id}, status={existing_run.status}"
                )
                return IdempotencyResult(
                    is_unique=False,
                    existing_run_id=existing_run.id,
                    existing_status=existing_run.status,
                )

            return IdempotencyResult(is_unique=True)

        if session:
            return await _check_db(session)
        else:
            async with self.session_factory() as db_session:
                return await _check_db(db_session)

    async def register_idempotency_key(
        self,
        idempotency_key: str,
        run_id: str,
        status: str = "running",
    ) -> None:
        """Register an idempotency key for a new run.

        Args:
            idempotency_key: The idempotency key to register
            run_id: The run ID associated with this key
            status: Current status of the run
        """
        now = datetime.now(timezone.utc)
        _idempotency_cache[idempotency_key] = (run_id, status, now)
        logger.debug(
            f"Registered idempotency key {idempotency_key[:8]}... for run {run_id}"
        )

    def clear_expired_cache_entries(self, ttl_seconds: int = 300) -> int:
        """Clear expired entries from the in-memory idempotency cache.

        Args:
            ttl_seconds: Time-to-live threshold

        Returns:
            Number of entries cleared
        """
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=ttl_seconds)

        expired_keys = [
            key for key, (_, _, timestamp) in _idempotency_cache.items()
            if timestamp < cutoff
        ]

        for key in expired_keys:
            del _idempotency_cache[key]

        if expired_keys:
            logger.debug(f"Cleared {len(expired_keys)} expired idempotency cache entries")

        return len(expired_keys)

    async def queue_run_with_idempotency(
        self,
        playbook_name: str,
        trigger_source: str,
        trigger_id: Optional[str] = None,
        input_data: Optional[Dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
        idempotency_ttl: int = 300,
        **kwargs: Any,
    ) -> Tuple[Optional[str], IdempotencyResult]:
        """Queue a run with idempotency check.

        This is the main entry point for queueing runs with deduplication.
        It checks for existing runs before creating a new one.

        Args:
            playbook_name: Name of the playbook
            trigger_source: Source of the trigger
            trigger_id: Optional trigger identifier
            input_data: Optional input data for the run
            idempotency_key: Optional pre-computed idempotency key
            idempotency_ttl: TTL for idempotency check in seconds
            **kwargs: Additional arguments for run creation

        Returns:
            Tuple of (run_id or None if duplicate, IdempotencyResult)
        """
        # Generate or use provided idempotency key
        if not idempotency_key:
            input_hash = None
            if input_data:
                input_hash = self.compute_input_hash(input_data)
            idempotency_key = self.generate_idempotency_key(
                playbook_name, trigger_source, trigger_id, input_hash
            )

        # Check for existing run
        idempotency_result = await self.check_idempotency(
            idempotency_key, ttl_seconds=idempotency_ttl
        )

        if not idempotency_result.is_unique:
            logger.warning(
                f"Duplicate run detected for playbook {playbook_name}: "
                f"existing_run={idempotency_result.existing_run_id}"
            )
            return None, idempotency_result

        # Create the run
        async with self.session_factory() as session:
            from repositories.playbook_run_repository import PlaybookRunRepository

            repo = PlaybookRunRepository(session)

            # Add idempotency key to input data
            run_input_data = input_data or {}
            run_input_data["_idempotency_key"] = idempotency_key

            run = await repo.create(
                playbook_name=playbook_name,
                playbook_version=kwargs.get("playbook_version", "1.0.0"),
                mode=kwargs.get("mode", "apply"),
                status="queued",
                input_json=run_input_data,
                trigger_source=trigger_source,
                trigger_id=trigger_id,
                **{k: v for k, v in kwargs.items() if k not in ["playbook_version", "mode"]},
            )

            await session.commit()

            # Register the idempotency key
            await self.register_idempotency_key(idempotency_key, run.id, "queued")

            # Queue the run
            await self.queue_run(run.id)

            logger.info(
                f"Created and queued run {run.id} for playbook {playbook_name} "
                f"with idempotency key {idempotency_key[:8]}..."
            )

            return run.id, idempotency_result


# Global singleton functions
def set_run_queue_manager(manager: RunQueueManager) -> None:
    """Set the global queue manager instance."""
    global _queue_manager
    _queue_manager = manager


def get_run_queue_manager() -> Optional[RunQueueManager]:
    """Get the global queue manager instance."""
    return _queue_manager


def get_idempotency_cache_stats() -> Dict[str, Any]:
    """Get statistics about the idempotency cache.

    Returns:
        Dictionary with cache statistics
    """
    return {
        "cache_size": len(_idempotency_cache),
        "ttl_seconds": IDEMPOTENCY_CACHE_TTL,
    }


def clear_idempotency_cache() -> int:
    """Clear all entries from the idempotency cache.

    Returns:
        Number of entries cleared
    """
    global _idempotency_cache
    count = len(_idempotency_cache)
    _idempotency_cache = {}
    return count
