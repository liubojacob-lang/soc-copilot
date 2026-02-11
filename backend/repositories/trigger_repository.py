"""Repository for trigger operations."""

import uuid
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Any, Optional
from sqlalchemy import select, update, delete, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models.playbook_definition import PlaybookTriggerModel
from models.trigger import TriggerInvocationModel
from core.logger import get_logger

logger = get_logger(__name__)


class TriggerRepository:
    """Repository for trigger CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_trigger(
        self,
        definition_id: str,
        trigger_type: str,
        name: Optional[str] = None,
        config: dict[str, Any] | None = None,
        secret: Optional[str] = None,
        cron_expr: Optional[str] = None,
        is_active: bool = True,
        created_by_user_id: Optional[str] = None,
    ) -> PlaybookTriggerModel:
        """Create a new trigger."""
        trigger = PlaybookTriggerModel(
            id=str(uuid.uuid4()),
            definition_id=definition_id,
            type=trigger_type,
            name=name,
            config_json=config or {},
            secret=secret,
            cron_expr=cron_expr,
            is_active=is_active,
            created_by=created_by_user_id,
        )
        self.session.add(trigger)
        await self.session.flush()
        await self.session.refresh(trigger)
        logger.info(f"Created trigger: {trigger.id} - type={trigger_type}")
        return trigger

    async def get_by_id(self, trigger_id: str) -> Optional[PlaybookTriggerModel]:
        """Get trigger by ID."""
        stmt = select(PlaybookTriggerModel).where(
            PlaybookTriggerModel.id == trigger_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_definition(
        self,
        definition_id: str,
        trigger_type: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> list[PlaybookTriggerModel]:
        """List triggers for a definition."""
        stmt = select(PlaybookTriggerModel).where(
            PlaybookTriggerModel.definition_id == definition_id
        )

        if trigger_type:
            stmt = stmt.where(PlaybookTriggerModel.type == trigger_type)
        if is_active is not None:
            stmt = stmt.where(PlaybookTriggerModel.is_active == is_active)

        stmt = stmt.order_by(PlaybookTriggerModel.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_all(
        self,
        trigger_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[PlaybookTriggerModel], int]:
        """List all triggers with pagination."""
        stmt = select(PlaybookTriggerModel)

        if trigger_type:
            stmt = stmt.where(PlaybookTriggerModel.type == trigger_type)
        if is_active is not None:
            stmt = stmt.where(PlaybookTriggerModel.is_active == is_active)

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar() or 0

        # Apply pagination
        stmt = stmt.order_by(PlaybookTriggerModel.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await self.session.execute(stmt)
        items = list(result.scalars().all())

        return items, total

    async def update(
        self,
        trigger_id: str,
        name: Optional[str] = None,
        config: Optional[dict[str, Any]] = None,
        secret: Optional[str] = None,
        cron_expr: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Optional[PlaybookTriggerModel]:
        """Update a trigger."""
        trigger = await self.get_by_id(trigger_id)
        if not trigger:
            return None

        update_values: dict[str, Any] = {}
        if name is not None:
            update_values["name"] = name
        if config is not None:
            update_values["config_json"] = config
        if secret is not None:
            update_values["secret"] = secret
        if cron_expr is not None:
            update_values["cron_expr"] = cron_expr
        if is_active is not None:
            update_values["is_active"] = is_active

        if update_values:
            stmt = (
                update(PlaybookTriggerModel)
                .where(PlaybookTriggerModel.id == trigger_id)
                .values(**update_values)
            )
            await self.session.execute(stmt)
            await self.session.flush()
            await self.session.refresh(trigger)
            logger.info(f"Updated trigger: {trigger_id}")

        return trigger

    async def delete(self, trigger_id: str) -> bool:
        """Delete a trigger."""
        trigger = await self.get_by_id(trigger_id)
        if not trigger:
            return False

        await self.session.delete(trigger)
        await self.session.flush()
        logger.info(f"Deleted trigger: {trigger_id}")
        return True

    async def update_last_triggered(self, trigger_id: str) -> None:
        """Update the last_triggered_at timestamp for a trigger."""
        stmt = (
            update(PlaybookTriggerModel)
            .where(PlaybookTriggerModel.id == trigger_id)
            .values(last_triggered_at=datetime.now(timezone.utc))
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def get_active_cron_triggers(self) -> list[PlaybookTriggerModel]:
        """Get all active cron triggers."""
        stmt = select(PlaybookTriggerModel).where(
            and_(
                PlaybookTriggerModel.type == "cron",
                PlaybookTriggerModel.is_active == True,
                PlaybookTriggerModel.cron_expr.isnot(None),
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_active_webhook_triggers(self) -> list[PlaybookTriggerModel]:
        """Get all active webhook triggers."""
        stmt = select(PlaybookTriggerModel).where(
            and_(
                PlaybookTriggerModel.type == "webhook",
                PlaybookTriggerModel.is_active == True,
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # Idempotency methods

    def _hash_request(self, payload: bytes) -> str:
        """Generate SHA-256 hash of request payload."""
        return hashlib.sha256(payload).hexdigest()

    async def check_idempotency(
        self,
        trigger_id: str,
        idempotency_key: Optional[str],
        payload: bytes,
    ) -> Optional[TriggerInvocationModel]:
        """Check if this request has already been processed.

        Returns the existing invocation if found, None otherwise.
        """
        request_hash = self._hash_request(payload)

        # First check by idempotency key if provided
        if idempotency_key:
            stmt = select(TriggerInvocationModel).where(
                and_(
                    TriggerInvocationModel.trigger_id == trigger_id,
                    TriggerInvocationModel.idempotency_key == idempotency_key,
                    TriggerInvocationModel.expires_at > datetime.now(timezone.utc),
                )
            )
            result = await self.session.execute(stmt)
            existing = result.scalar_one_or_none()
            if existing:
                logger.info(f"Idempotent request found: {idempotency_key}")
                return existing

        # Then check by hash to catch duplicates without idempotency key
        stmt = select(TriggerInvocationModel).where(
            and_(
                TriggerInvocationModel.trigger_id == trigger_id,
                TriggerInvocationModel.request_hash == request_hash,
                TriggerInvocationModel.created_at > datetime.now(timezone.utc) - timedelta(hours=24),
            )
        )
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            logger.info(f"Duplicate request found by hash: {request_hash[:16]}...")
            return existing

        return None

    async def record_invocation(
        self,
        trigger_id: str,
        idempotency_key: Optional[str],
        payload: bytes,
        run_id: Optional[str] = None,
        status: str = "pending",
        error_message: Optional[str] = None,
    ) -> TriggerInvocationModel:
        """Record a trigger invocation for idempotency tracking."""
        request_hash = self._hash_request(payload)

        invocation = TriggerInvocationModel(
            id=str(uuid.uuid4()),
            trigger_id=trigger_id,
            idempotency_key=idempotency_key,
            run_id=run_id,
            request_hash=request_hash,
            status=status,
            error_message=error_message,
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        )
        self.session.add(invocation)
        await self.session.flush()
        await self.session.refresh(invocation)
        return invocation

    async def update_invocation(
        self,
        invocation_id: str,
        run_id: Optional[str] = None,
        status: str = "success",
        error_message: Optional[str] = None,
    ) -> Optional[TriggerInvocationModel]:
        """Update an invocation with results."""
        stmt = (
            update(TriggerInvocationModel)
            .where(TriggerInvocationModel.id == invocation_id)
            .values(run_id=run_id, status=status, error_message=error_message)
        )
        await self.session.execute(stmt)
        await self.session.flush()

        # Get updated model
        stmt = select(TriggerInvocationModel).where(
            TriggerInvocationModel.id == invocation_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def cleanup_old_invocations(self, hours: int = 24) -> int:
        """Delete invocations older than specified hours.

        Args:
            hours: Number of hours (must be between 1 and 8760, i.e., 1 day to 1 year)

        Returns:
            Number of invocations deleted
        """
        # Validate hours parameter to prevent abuse
        if hours < 1 or hours > 8760:
            raise ValueError("hours must be between 1 and 8760 (1 day to 1 year)")

        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        stmt = delete(TriggerInvocationModel).where(
            TriggerInvocationModel.expires_at < cutoff
        )
        result = await self.session.execute(stmt)
        deleted_count = result.rowcount
        await self.session.flush()
        logger.info(f"Cleaned up {deleted_count} old invocations")
        return deleted_count

    async def get_invocation(
        self, invocation_id: str
    ) -> Optional[TriggerInvocationModel]:
        """Get invocation by ID."""
        stmt = select(TriggerInvocationModel).where(
            TriggerInvocationModel.id == invocation_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
