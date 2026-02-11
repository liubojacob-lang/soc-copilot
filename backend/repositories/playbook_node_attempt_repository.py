"""Repository for playbook node attempts."""

import uuid
from datetime import datetime, timezone
from typing import Any, Optional
from sqlalchemy import select, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models.playbook_node_attempt import PlaybookNodeAttemptModel
from core.logger import get_logger

logger = get_logger(__name__)


class PlaybookNodeAttemptRepository:
    """Repository for playbook node attempt CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        node_run_id: str,
        attempt_no: int,
        status: str = "pending",
    ) -> PlaybookNodeAttemptModel:
        """Create a new node attempt."""
        attempt = PlaybookNodeAttemptModel(
            id=str(uuid.uuid4()),
            node_run_id=node_run_id,
            attempt_no=attempt_no,
            status=status,
            output_json={},
        )
        self.session.add(attempt)
        await self.session.flush()
        await self.session.refresh(attempt)
        logger.debug(f"Created attempt {attempt.id} for node_run {node_run_id}")
        return attempt

    async def get_by_id(self, attempt_id: str) -> Optional[PlaybookNodeAttemptModel]:
        """Get attempt by ID."""
        stmt = select(PlaybookNodeAttemptModel).where(
            PlaybookNodeAttemptModel.id == attempt_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_node_run(
        self,
        node_run_id: str,
    ) -> list[PlaybookNodeAttemptModel]:
        """List all attempts for a node run."""
        stmt = select(PlaybookNodeAttemptModel).where(
            PlaybookNodeAttemptModel.node_run_id == node_run_id
        ).order_by(PlaybookNodeAttemptModel.attempt_no)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_status(
        self,
        attempt_id: str,
        status: str,
        log_text: Optional[str] = None,
        output_json: Optional[dict[str, Any]] = None,
        error_text: Optional[str] = None,
    ) -> Optional[PlaybookNodeAttemptModel]:
        """Update attempt status and result."""
        attempt = await self.get_by_id(attempt_id)
        if not attempt:
            return None
        
        attempt.status = status
        
        # Set finished_at and duration if transitioning to terminal state
        if status in ("success", "failed") and attempt.finished_at is None:
            now = datetime.now(timezone.utc)
            attempt.finished_at = now
            if attempt.started_at:
                duration_ms = int((now - attempt.started_at).total_seconds() * 1000)
                attempt.duration_ms = duration_ms
        
        if log_text:
            attempt.log_text = log_text
        if output_json:
            attempt.output_json = output_json
        if error_text:
            attempt.error_text = error_text
        
        await self.session.flush()
        await self.session.refresh(attempt)
        logger.debug(f"Updated attempt {attempt_id} status to {status}")
        return attempt

    async def mark_started(self, attempt_id: str) -> Optional[PlaybookNodeAttemptModel]:
        """Mark attempt as started."""
        attempt = await self.get_by_id(attempt_id)
        if not attempt:
            return None
        
        attempt.status = "running"
        attempt.started_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.session.refresh(attempt)
        return attempt

    async def get_latest_attempt(
        self,
        node_run_id: str,
    ) -> Optional[PlaybookNodeAttemptModel]:
        """Get the latest attempt for a node run."""
        stmt = select(PlaybookNodeAttemptModel).where(
            PlaybookNodeAttemptModel.node_run_id == node_run_id
        ).order_by(
            PlaybookNodeAttemptModel.attempt_no.desc()
        ).limit(1)
        
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
