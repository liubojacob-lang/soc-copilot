"""Repository for playbook node runs."""

import uuid
from datetime import datetime, timezone
from typing import Any, Optional
from sqlalchemy import select, update, delete, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.playbook_node_run import PlaybookNodeRunModel
from models.playbook_node_attempt import PlaybookNodeAttemptModel
from models.playbook_run import PlaybookRunModel
from core.logger import get_logger

logger = get_logger(__name__)


class PlaybookNodeRunRepository:
    """Repository for playbook node run CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        run_id: str,
        node_id: str,
        node_name: str,
        node_type: str,
        input_json: dict[str, Any],
        status: str = "pending",
    ) -> PlaybookNodeRunModel:
        """Create a new node run."""
        node_run = PlaybookNodeRunModel(
            id=str(uuid.uuid4()),
            run_id=run_id,
            node_id=node_id,
            node_name=node_name,
            node_type=node_type,
            status=status,
            input_json=input_json,
            output_json={},
            attempt_count=0,
        )
        self.session.add(node_run)
        await self.session.flush()
        await self.session.refresh(node_run)
        logger.debug(f"Created node run: {node_run.id} for node {node_id}")
        return node_run

    async def get_by_id(self, node_run_id: str) -> Optional[PlaybookNodeRunModel]:
        """Get node run by ID."""
        stmt = select(PlaybookNodeRunModel).where(
            PlaybookNodeRunModel.id == node_run_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_run_and_node(
        self,
        run_id: str,
        node_id: str,
    ) -> Optional[PlaybookNodeRunModel]:
        """Get node run by run ID and node ID."""
        stmt = select(PlaybookNodeRunModel).where(
            and_(
                PlaybookNodeRunModel.run_id == run_id,
                PlaybookNodeRunModel.node_id == node_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_run(
        self,
        run_id: str,
        include_attempts: bool = False,
    ) -> list[PlaybookNodeRunModel]:
        """List all node runs for a given run."""
        stmt = select(PlaybookNodeRunModel).where(
            PlaybookNodeRunModel.run_id == run_id
        ).order_by(PlaybookNodeRunModel.created_at)
        
        if include_attempts:
            stmt = stmt.options(selectinload(PlaybookNodeRunModel.attempts))
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_status(
        self,
        run_id: str,
        status: str,
    ) -> list[PlaybookNodeRunModel]:
        """List node runs by status."""
        stmt = select(PlaybookNodeRunModel).where(
            and_(
                PlaybookNodeRunModel.run_id == run_id,
                PlaybookNodeRunModel.status == status,
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_status(
        self,
        node_run_id: str,
        status: str,
        error_message: Optional[str] = None,
        output_json: Optional[dict[str, Any]] = None,
    ) -> Optional[PlaybookNodeRunModel]:
        """Update node run status."""
        node_run = await self.get_by_id(node_run_id)
        if not node_run:
            return None
        
        # Set finished_at if transitioning to terminal state
        if status in ("success", "failed", "skipped", "cancelled") and node_run.finished_at is None:
            node_run.finished_at = datetime.now(timezone.utc)
        
        node_run.status = status
        if error_message:
            node_run.last_error = error_message
        if output_json:
            node_run.output_json = output_json
        
        node_run.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.session.refresh(node_run)
        logger.debug(f"Updated node run {node_run_id} status to {status}")
        return node_run

    async def increment_attempt(
        self,
        node_run_id: str,
    ) -> Optional[PlaybookNodeRunModel]:
        """Increment attempt count for a node run."""
        node_run = await self.get_by_id(node_run_id)
        if not node_run:
            return None
        
        node_run.attempt_count += 1
        node_run.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.session.refresh(node_run)
        return node_run

    async def mark_started(self, node_run_id: str) -> Optional[PlaybookNodeRunModel]:
        """Mark node run as started."""
        node_run = await self.get_by_id(node_run_id)
        if not node_run:
            return None
        
        node_run.status = "running"
        node_run.started_at = datetime.now(timezone.utc)
        node_run.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.session.refresh(node_run)
        logger.debug(f"Marked node run {node_run_id} as started")
        return node_run

    async def get_run_summary(
        self,
        run_id: str,
    ) -> dict[str, int]:
        """Get summary of node runs for a run."""
        # Count by status
        stmt = select(
            PlaybookNodeRunModel.status,
            func.count(PlaybookNodeRunModel.id),
        ).where(
            PlaybookNodeRunModel.run_id == run_id
        ).group_by(PlaybookNodeRunModel.status)
        
        result = await self.session.execute(stmt)
        status_counts = {status: count for status, count in result.all()}
        
        total_stmt = select(func.count()).select_from(
            select(PlaybookNodeRunModel).where(
                PlaybookNodeRunModel.run_id == run_id
            ).subquery()
        )
        total_result = await self.session.execute(total_stmt)
        total = total_result.scalar() or 0
        
        return {
            "total": total,
            "pending": status_counts.get("pending", 0),
            "running": status_counts.get("running", 0),
            "success": status_counts.get("success", 0),
            "failed": status_counts.get("failed", 0),
            "skipped": status_counts.get("skipped", 0),
            "cancelled": status_counts.get("cancelled", 0),
        }

    async def delete_by_run(self, run_id: str) -> int:
        """Delete all node runs for a given run."""
        stmt = delete(PlaybookNodeRunModel).where(
            PlaybookNodeRunModel.run_id == run_id
        )
        result = await self.session.execute(stmt)
        count = result.rowcount
        await self.session.flush()
        logger.info(f"Deleted {count} node runs for run {run_id}")
        return count
