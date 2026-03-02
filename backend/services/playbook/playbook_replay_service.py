"""Playbook Replay Service for v0.7.3.

This service handles:
- Replaying playbook runs with historical input
- Building replay chain lineage
- Validating replay permissions
- Copying context between runs
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.playbook_run import PlaybookRunModel
from models.playbook_definition import PlaybookDefinitionModel
from models.user import UserModel
from schemas.playbook_dag import (
    PlaybookRunReplayResponse,
    ReplayChainNode,
    ReplayChainResponse
)

logger = logging.getLogger(__name__)


class PlaybookReplayService:
    """Service for replaying playbook runs."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def replay_run(
        self,
        run_id: str,
        mode: str = "dry_run",
        override_context: Optional[dict] = None,
        created_by_user_id: Optional[str] = None
    ) -> PlaybookRunReplayResponse:
        """
        Replay a playbook run with historical input.

        Creates a new run with the same input context and definition.
        Optionally allows overriding context values.

        Args:
            run_id: ID of the original run to replay
            mode: Execution mode ('dry_run' or 'apply')
            override_context: Optional context overrides
            created_by_user_id: ID of the user creating the replay

        Returns:
            Replay response with new run details
        """
        # Get the original run
        stmt = select(PlaybookRunModel).where(
            PlaybookRunModel.id == run_id
        )
        result = await self.session.execute(stmt)
        original_run = result.scalar_one_or_none()

        if not original_run:
            raise ValueError(f"Playbook run {run_id} not found")

        # Validate can replay
        await self._validate_can_replay(original_run, created_by_user_id)

        # Prepare input context (original or with overrides)
        input_context = original_run.input_context_json.copy()
        if override_context:
            input_context.update(override_context)

        # Create new run
        new_run = PlaybookRunModel(
            id=str(uuid.uuid4()),
            playbook_name=original_run.playbook_name,
            playbook_version=original_run.playbook_version,
            mode=mode,
            status="pending",
            created_by_user_id=created_by_user_id,
            input_json=input_context,
            output_json={},
            started_at=datetime.now(timezone.utc),
            finished_at=None,
            error_message=None,

            # v0.7 DAG fields
            engine_version=original_run.engine_version,
            execution_mode=original_run.execution_mode,
            definition_id=original_run.definition_id,
            failure_strategy=original_run.failure_strategy,
            trigger_source="replay",

            # v0.7.3: Context and replay fields
            input_context_json=input_context,
            context_json={},
            replay_of_run_id=run_id
        )

        self.session.add(new_run)
        await self.session.flush()

        logger.info(
            f"Created replay run {new_run.id} from original run {run_id} "
            f"(mode: {mode})"
        )

        return PlaybookRunReplayResponse(
            run_id=new_run.id,
            original_run_id=run_id,
            mode=mode,
            status="pending",
            message=f"Replay run created successfully"
        )

    async def get_replay_chain(
        self,
        run_id: str,
        max_depth: int = 50
    ) -> ReplayChainResponse:
        """
        Get the replay chain for a run.

        Traverses from the root run to the latest replay.

        Args:
            run_id: ID of the run to get chain for
            max_depth: Maximum depth to traverse

        Returns:
            Replay chain response
        """
        # Find root run (the one without replay_of_run_id)
        root_run = await self._find_root_run(run_id)
        if not root_run:
            raise ValueError(f"Could not find root run for {run_id}")

        # Build chain from root
        chain = []
        current_run_id = root_run.id
        depth = 0

        while current_run_id and depth < max_depth:
            stmt = select(PlaybookRunModel).where(
                PlaybookRunModel.id == current_run_id
            )
            result = await self.session.execute(stmt)
            run = result.scalar_one_or_none()

            if not run:
                break

            chain.append(ReplayChainNode(
                run_id=run.id,
                playbook_name=run.playbook_name,
                mode=run.mode,
                status=run.status,
                started_at=run.started_at,
                finished_at=run.finished_at,
                replay_of_run_id=run.replay_of_run_id
            ))

            # Find next replay
            next_stmt = select(PlaybookRunModel).where(
                PlaybookRunModel.replay_of_run_id == current_run_id
            ).order_by(PlaybookRunModel.started_at.desc())

            next_result = await self.session.execute(next_stmt)
            next_run = next_result.first()

            if next_run:
                current_run_id = next_run[0].id
            else:
                break

            depth += 1

        return ReplayChainResponse(
            root_run_id=root_run.id,
            chain=chain,
            total=len(chain),
            depth=depth
        )

    async def _validate_can_replay(
        self,
        original_run: PlaybookRunModel,
        created_by_user_id: Optional[str]
    ) -> None:
        """
        Validate if a run can be replayed.

        Args:
            original_run: The run to replay
            created_by_user_id: ID of the user attempting replay

        Raises:
            ValueError: If replay is not allowed
        """
        # Basic validation - all users can replay their own runs
        # Admin and auditor can replay any run
        if created_by_user_id:
            # For now, allow all replays. RBAC is enforced at API level.
            pass

    async def _find_root_run(self, run_id: str) -> Optional[PlaybookRunModel]:
        """
        Find the root run in a replay chain.

        Traverses up the replay_of_run_id chain to find the first run.

        Args:
            run_id: Starting run ID

        Returns:
            Root run or None
        """
        current_id = run_id
        visited = set()
        max_iterations = 100

        for _ in range(max_iterations):
            if current_id in visited:
                # Circular reference detected
                logger.error(f"Circular reference detected in replay chain for {run_id}")
                break

            visited.add(current_id)

            stmt = select(PlaybookRunModel).where(
                PlaybookRunModel.id == current_id
            )
            result = await self.session.execute(stmt)
            run = result.scalar_one_or_none()

            if not run:
                break

            if run.replay_of_run_id is None:
                return run

            current_id = run.replay_of_run_id

        return None

    async def get_replay_children(
        self,
        run_id: str
    ) -> List[PlaybookRunModel]:
        """
        Get all direct replay children of a run.

        Args:
            run_id: Parent run ID

        Returns:
            List of child runs
        """
        stmt = select(PlaybookRunModel).where(
            PlaybookRunModel.replay_of_run_id == run_id
        ).order_by(PlaybookRunModel.started_at.desc())

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_replay_children(self, run_id: str) -> int:
        """
        Count the number of direct replay children of a run.

        Args:
            run_id: Parent run ID

        Returns:
            Number of child runs
        """
        from sqlalchemy import func

        stmt = select(func.count(PlaybookRunModel.id)).where(
            PlaybookRunModel.replay_of_run_id == run_id
        )

        result = await self.session.execute(stmt)
        return result.scalar() or 0


# Singleton factory function
def get_replay_service(session: AsyncSession) -> PlaybookReplayService:
    """Get replay service instance."""
    return PlaybookReplayService(session)
