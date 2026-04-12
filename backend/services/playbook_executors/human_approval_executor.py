"""Human Approval node executor for playbook execution pause."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from models.playbook_approval import PlaybookApprovalModel
from models.playbook_node_run import PlaybookNodeRunModel

from .executor_base import BaseExecutor, ExecutorContext

logger = get_logger(__name__)


class HumanApprovalExecutor(BaseExecutor):
    """Executor for human approval nodes that pause playbook execution."""

    async def execute(self, context: ExecutorContext) -> dict[str, Any]:
        """Execute human approval node - creates approval request and pauses execution.

        This executor:
        1. Creates a PlaybookApprovalModel record
        2. Updates the node run status to 'waiting_approval'
        3. Returns special output indicating execution is paused

        The playbook engine will detect this status and pause execution of dependent nodes.

        Args:
            context: Execution context with node definition and inputs

        Returns:
            Output dictionary with approval request details
        """
        config = context.node_def.get("config", {})
        title = config.get("title", "Approval Required")
        message = config.get("message", "Please approve this step to continue.")
        timeout_seconds = config.get("timeout_seconds")
        on_timeout = config.get("on_timeout", "fail")  # approve/reject/fail

        # Get session from context (need to access via thread-local or pass in)
        # For now, we'll create the approval record and update node status
        session = self._get_session()

        # Create approval record
        approval = PlaybookApprovalModel(
            id=str(uuid.uuid4()),
            run_id=context.run_id,
            node_id=context.node_id,
            requested_by_user_id=self._get_current_user_id(context),
            status="pending",
            title=title,
            message=message,
            timeout_seconds=timeout_seconds,
            on_timeout=on_timeout,
        )

        session.add(approval)
        await session.flush()

        # Update node run status to waiting_approval
        await self._update_node_status(
            context.run_id,
            context.node_id,
            "waiting_approval",
            {
                "approval_id": approval.id,
                "title": title,
                "message": message,
            },
        )

        await session.commit()

        logger.info(
            f"[{context.run_id}] Created approval request {approval.id} "
            f"for node {context.node_id}"
        )

        # Return special output indicating paused execution
        return {
            "status": "waiting_approval",
            "approval_id": approval.id,
            "title": title,
            "message": message,
            "paused": True,
        }

    def _get_session(self) -> AsyncSession:
        """Get database session from context.

        This is a workaround - in production, session should be passed via context.
        """
        from db.session import AsyncSessionLocal

        return AsyncSessionLocal()

    def _get_current_user_id(self, context: ExecutorContext) -> str | None:
        """Get current user ID from context.

        User context is now passed via ExecutorContext during playbook execution.
        Falls back to None if user context is not available (e.g., system-triggered runs).

        Args:
            context: Execution context containing user information

        Returns:
            User ID if available, None otherwise
        """
        return context.user_id

    async def _update_node_status(
        self,
        run_id: str,
        node_id: str,
        status: str,
        output_json: dict[str, Any] | None = None,
    ) -> None:
        """Update node run status in database.

        Args:
            run_id: Playbook run ID
            node_id: Node identifier
            status: New status
            output_json: Optional output data
        """
        session = self._get_session()

        stmt = select(PlaybookNodeRunModel).where(
            PlaybookNodeRunModel.run_id == run_id,
            PlaybookNodeRunModel.node_id == node_id,
        )
        result = await session.execute(stmt)
        node_run = result.scalar_one_or_none()

        if node_run:
            node_run.status = status
            if output_json:
                node_run.output_json = output_json

            if status == "waiting_approval":
                node_run.started_at = datetime.now(UTC)

            await session.commit()

        await session.close()
