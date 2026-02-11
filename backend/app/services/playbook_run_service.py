"""Service for playbook run operations."""

from typing import Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from models.playbook_run import PlaybookRunModel, PlaybookRunStepModel
from schemas.playbook_run import (
    PlaybookRunCreateRequest,
    PlaybookRunResponse,
    PlaybookRunStepResponse,
    PlaybookRunListResponse,
    PlaybookResumeRequest,
    PlaybookResumeResponse,
    PlaybookRunWithStepsResponse,
)
from repositories.playbook_run_repository import PlaybookRunRepository
from playbook_engine import PlaybookExecutionEngine

logger = get_logger(__name__)


class PlaybookRunService:
    """Service for managing playbook runs."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the service.

        Args:
            session: Database session
        """
        self.session = session
        self.run_repo = PlaybookRunRepository(session)
        self.engine = PlaybookExecutionEngine(session)

    async def create_run(
        self,
        request: PlaybookRunCreateRequest,
        created_by_user_id: Optional[str] = None,
    ) -> PlaybookRunResponse:
        """Create and start a new playbook run.

        Args:
            request: Run creation request
            created_by_user_id: User who initiated the run

        Returns:
            PlaybookRunResponse with run details

        Raises:
            ValueError: If playbook is unknown
        """
        result = await self.engine.run_playbook(
            playbook_name=request.playbook_name,
            input_json=request.input_json,
            mode=request.mode,
            created_by_user_id=created_by_user_id,
        )

        run = await self.run_repo.get_by_id(result["run_id"])
        if not run:
            raise ValueError(f"Failed to create run: {result}")

        return PlaybookRunResponse.model_validate(run)

    async def list_runs(
        self,
        playbook_name: Optional[str] = None,
        status: Optional[str] = None,
        created_by_user_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PlaybookRunListResponse:
        """List playbook runs with pagination.

        Args:
            playbook_name: Filter by playbook name
            status: Filter by status
            created_by_user_id: Filter by user
            page: Page number (1-indexed)
            page_size: Items per page

        Returns:
            PlaybookRunListResponse with paginated results
        """
        offset = (page - 1) * page_size
        runs, total = await self.run_repo.list_runs(
            playbook_name=playbook_name,
            status=status,
            created_by_user_id=created_by_user_id,
            limit=page_size,
            offset=offset,
        )

        items = [PlaybookRunResponse.model_validate(run) for run in runs]

        return PlaybookRunListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_run(self, run_id: str) -> Optional[PlaybookRunResponse]:
        """Get a playbook run by ID.

        Args:
            run_id: Run ID

        Returns:
            PlaybookRunResponse or None
        """
        run = await self.run_repo.get_by_id(run_id)
        if not run:
            return None
        return PlaybookRunResponse.model_validate(run)

    async def get_run_with_steps(
        self,
        run_id: str,
    ) -> Optional[PlaybookRunWithStepsResponse]:
        """Get a playbook run with all steps.

        Args:
            run_id: Run ID

        Returns:
            PlaybookRunWithStepsResponse or None
        """
        run = await self.run_repo.get_by_id(run_id)
        if not run:
            return None

        steps = await self.run_repo.get_steps_by_run_id(run_id)
        step_responses = [PlaybookRunStepResponse.model_validate(s) for s in steps]

        return PlaybookRunWithStepsResponse(
            run=PlaybookRunResponse.model_validate(run),
            steps=step_responses,
        )

    async def resume_run(
        self,
        run_id: str,
        request: PlaybookResumeRequest,
    ) -> PlaybookResumeResponse:
        """Resume a failed or partial playbook run.

        Args:
            run_id: Run ID to resume
            request: Resume request parameters

        Returns:
            PlaybookResumeResponse with updated status

        Raises:
            ValueError: If run cannot be resumed
        """
        result = await self.engine.resume_playbook_run(
            run_id=run_id,
            from_step_index=request.from_step_index or 0,
            run_mode=request.run_mode,
        )

        run = await self.run_repo.get_by_id(run_id)
        if not run:
            raise ValueError(f"Run not found after resume: {run_id}")

        return PlaybookResumeResponse(
            run_id=run.id,
            status=run.status,
            from_step=result.get("from_step", 0),
            output_json=run.output_json,
        )

    async def get_available_playbooks(self) -> dict[str, Any]:
        """Get list of available playbooks.

        Returns:
            Dictionary of available playbooks
        """
        from schemas.playbook_run import AVAILABLE_PLAYBOOKS
        return AVAILABLE_PLAYBOOKS
