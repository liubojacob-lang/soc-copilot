"""Human approval node plugin (v0.7.4)."""

import uuid
from typing import Any, Dict
from datetime import datetime, timezone
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..base_node import BaseNodePlugin, NodeExecutionContext
from models.playbook_approval import PlaybookApprovalModel
from models.playbook_node_run import PlaybookNodeRunModel

logger = logging.getLogger(__name__)


class HumanApprovalPlugin(BaseNodePlugin):
    """Human approval node for manual workflow intervention.

    This node pauses playbook execution and waits for manual approval
    before proceeding. Supports timeout configuration and fallback actions.
    """

    @property
    def node_id(self) -> str:
        return "builtin_human_approval"

    @property
    def name(self) -> str:
        return "Human Approval"

    @property
    def node_type(self) -> str:
        return "approval"

    @property
    def description(self) -> str:
        return "Pause execution for manual approval before proceeding"

    def validate_input(self, input_json: Dict[str, Any]) -> None:
        """Validate input before execution."""
        approvers = input_json.get("approvers")
        if not approvers:
            raise ValueError("approvers list is required")

        if not isinstance(approvers, list):
            raise ValueError("approvers must be a list")

        timeout = input_json.get("timeout_seconds")
        if timeout is not None and timeout <= 0:
            raise ValueError("timeout_seconds must be positive")

    async def execute(self, context: NodeExecutionContext) -> Dict[str, Any]:
        """Create approval request and pause execution.

        Args:
            context: Execution context

        Returns:
            Approval request details with paused=True flag
        """
        title = context.input_json.get("title", "Approval Required")
        message = context.input_json.get("message", "Please approve this step to continue.")
        approvers = context.input_json.get("approvers", [])
        timeout_seconds = context.input_json.get("timeout_seconds")
        on_timeout = context.input_json.get("on_timeout", "fail")  # approve, reject, fail
        min_approvals = context.input_json.get("min_approvals", 1)

        # Get database session
        from db.session import AsyncSessionLocal
        session = AsyncSessionLocal()

        try:
            # Create approval record
            approval = PlaybookApprovalModel(
                id=str(uuid.uuid4()),
                run_id=context.run_id,
                node_id=context.node_id,
                requested_by_user_id=context.context.get("created_by_user_id"),
                status="pending",
                title=title,
                message=message,
                approvers=approvers,
                timeout_seconds=timeout_seconds,
                on_timeout=on_timeout,
                min_approvals=min_approvals,
            )

            session.add(approval)
            await session.flush()

            # Update node run status to waiting_approval
            await self._update_node_status(
                session, context.run_id, context.node_id, "waiting_approval",
                {
                    "approval_id": approval.id,
                    "title": title,
                    "message": message,
                    "approvers": approvers,
                }
            )

            await session.commit()

            logger.info(
                f"[{context.run_id}] Created approval request {approval.id} "
                f"for node {context.node_id}, awaiting {min_approvals} approval(s)"
            )

            # Return special output indicating paused execution
            return {
                "status": "waiting_approval",
                "approval_id": approval.id,
                "title": title,
                "message": message,
                "approvers": approvers,
                "paused": True,
                "approval_url": f"/api/approvals/{approval.id}",
            }

        except Exception as e:
            await session.rollback()
            logger.error(f"[{context.run_id}] Failed to create approval: {e}")
            raise
        finally:
            await session.close()

    async def _update_node_status(
        self,
        session: AsyncSession,
        run_id: str,
        node_id: str,
        status: str,
        output_json: Dict[str, Any] | None = None,
    ) -> None:
        """Update node run status in database.

        Args:
            session: Database session
            run_id: Playbook run ID
            node_id: Node identifier
            status: New status
            output_json: Optional output data
        """
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
                node_run.started_at = datetime.now(timezone.utc)

    def get_required_secrets(self) -> list[str]:
        """No secrets required for approval node."""
        return []
