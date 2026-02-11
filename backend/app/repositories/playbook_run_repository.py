"""Repository for playbook run and step operations."""

from typing import Any, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from models.playbook_run import PlaybookRunModel, PlaybookRunStepModel

logger = get_logger(__name__)


class PlaybookRunRepository:
    """Repository for managing playbook runs and steps."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository.

        Args:
            session: Database session
        """
        self.session = session

    async def create(
        self,
        playbook_name: str,
        playbook_version: str,
        mode: str,
        status: str,
        input_json: dict[str, Any],
        output_json: dict[str, Any],
        created_by_user_id: Optional[str] = None,
        **kwargs: Any,
    ) -> PlaybookRunModel:
        """Create a new playbook run.

        Args:
            playbook_name: Name of the playbook
            playbook_version: Version of the playbook
            mode: Execution mode (dry_run/apply)
            status: Initial status
            input_json: Input data
            output_json: Output data
            created_by_user_id: User who initiated the run
            **kwargs: Additional fields

        Returns:
            Created PlaybookRunModel instance
        """
        run = PlaybookRunModel(
            playbook_name=playbook_name,
            playbook_version=playbook_version,
            mode=mode,
            status=status,
            created_by_user_id=created_by_user_id,
            input_json=input_json,
            output_json=output_json,
            started_at=kwargs.get("started_at"),
            finished_at=kwargs.get("finished_at"),
            error_message=kwargs.get("error_message"),
        )
        self.session.add(run)
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def get_by_id(self, run_id: str) -> Optional[PlaybookRunModel]:
        """Get a playbook run by ID.

        Args:
            run_id: Run ID

        Returns:
            PlaybookRunModel instance or None
        """
        stmt = select(PlaybookRunModel).where(PlaybookRunModel.id == run_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_runs(
        self,
        playbook_name: Optional[str] = None,
        status: Optional[str] = None,
        created_by_user_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[PlaybookRunModel], int]:
        """List playbook runs with filters.

        Args:
            playbook_name: Filter by playbook name
            status: Filter by status
            created_by_user_id: Filter by user
            limit: Maximum results
            offset: Result offset for pagination

        Returns:
            Tuple of (list of runs, total count)
        """
        conditions = []

        if playbook_name:
            conditions.append(PlaybookRunModel.playbook_name == playbook_name)
        if status:
            conditions.append(PlaybookRunModel.status == status)
        if created_by_user_id:
            conditions.append(PlaybookRunModel.created_by_user_id == created_by_user_id)

        stmt = select(PlaybookRunModel)

        if conditions:
            stmt = stmt.where(and_(*conditions))

        # Count total
        count_stmt = select(PlaybookRunModel.id)
        if conditions:
            count_stmt = count_stmt.where(and_(*conditions))

        count_result = await self.session.execute(count_stmt)
        total = len(count_result.all())

        # Apply ordering and pagination
        stmt = stmt.order_by(PlaybookRunModel.started_at.desc()).offset(offset).limit(limit)

        result = await self.session.execute(stmt)
        runs = list(result.scalars().all())

        return runs, total

    async def update(self, run_id: str, updates: dict[str, Any]) -> Optional[PlaybookRunModel]:
        """Update a playbook run.

        Args:
            run_id: Run ID
            updates: Fields to update

        Returns:
            Updated PlaybookRunModel instance or None
        """
        run = await self.get_by_id(run_id)
        if not run:
            return None

        for key, value in updates.items():
            if hasattr(run, key):
                setattr(run, key, value)

        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def update_by_id(self, model_id: str, updates: dict[str, Any]) -> Optional[Any]:
        """Update any model by ID (for steps).

        Args:
            model_id: Model ID
            updates: Fields to update

        Returns:
            Updated model instance or None
        """
        # Try step model first
        stmt = select(PlaybookRunStepModel).where(PlaybookRunStepModel.id == model_id)
        result = await self.session.execute(stmt)
        step = result.scalar_one_or_none()

        if step:
            for key, value in updates.items():
                if hasattr(step, key):
                    setattr(step, key, value)
            await self.session.flush()
            await self.session.refresh(step)
            return step

        return None

    async def get_steps_by_run_id(self, run_id: str) -> list[PlaybookRunStepModel]:
        """Get all steps for a playbook run.

        Args:
            run_id: Run ID

        Returns:
            List of PlaybookRunStepModel instances
        """
        stmt = select(PlaybookRunStepModel).where(
            PlaybookRunStepModel.run_id == run_id
        ).order_by(PlaybookRunStepModel.step_index)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_step(
        self,
        run_id: str,
        step_index: int,
        step_id: str,
        step_name: str,
        step_type: str,
        status: str,
        input_json: dict[str, Any],
        output_json: dict[str, Any],
        **kwargs: Any,
    ) -> PlaybookRunStepModel:
        """Create a new playbook run step.

        Args:
            run_id: Run ID
            step_index: Step index
            step_id: Step identifier
            step_name: Step display name
            step_type: Step type
            status: Initial status
            input_json: Input data
            output_json: Output data
            **kwargs: Additional fields

        Returns:
            Created PlaybookRunStepModel instance
        """
        step = PlaybookRunStepModel(
            run_id=run_id,
            step_index=step_index,
            step_id=step_id,
            step_name=step_name,
            step_type=step_type,
            status=status,
            input_json=input_json,
            output_json=output_json,
            started_at=kwargs.get("started_at"),
            finished_at=kwargs.get("finished_at"),
            duration_ms=kwargs.get("duration_ms"),
            error_text=kwargs.get("error_text"),
            skipped_reason=kwargs.get("skipped_reason"),
        )
        self.session.add(step)
        await self.session.flush()
        await self.session.refresh(step)
        return step

    async def get_step_by_id(self, step_id: str) -> Optional[PlaybookRunStepModel]:
        """Get a step by ID.

        Args:
            step_id: Step ID

        Returns:
            PlaybookRunStepModel instance or None
        """
        stmt = select(PlaybookRunStepModel).where(PlaybookRunStepModel.id == step_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
