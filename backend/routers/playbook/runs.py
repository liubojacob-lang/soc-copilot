"""Playbook run execution endpoints.

This module contains endpoints for:
- Creating and starting playbook runs
- Listing and getting playbook runs
- Resuming failed or partial runs
- Getting available playbooks
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from db.session import get_session
from dependencies.auth import get_current_user, get_current_user_optional
from models.user import UserModel, UserRole
from repositories.audit_repository import AuditRepository
from schemas.playbook_run import (
    PlaybookResumeRequest,
    PlaybookResumeResponse,
    PlaybookRunCreateRequest,
    PlaybookRunListResponse,
    PlaybookRunResponse,
    PlaybookRunWithStepsResponse,
)
from services.playbook.playbook_run_service import PlaybookRunService

logger = get_logger(__name__)

router = APIRouter(tags=["playbook-runs"])


@router.post("/run", response_model=PlaybookRunResponse)
async def create_playbook_run(
    request: PlaybookRunCreateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> PlaybookRunResponse:
    """Create and start a new playbook run.

    Args:
        request: Run creation request
        session: Database session
        current_user: Authenticated user

    Returns:
        Created playbook run details

    Raises:
        HTTPException: If mode is apply and user is not admin
    """
    # Check apply mode permission
    if request.mode == "apply" and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Playbook apply mode requires admin role",
        )

    service = PlaybookRunService(session)
    result = await service.create_run(request, created_by_user_id=current_user.id)

    # Create audit log
    audit_repo = AuditRepository(session)
    await audit_repo.create(
        action="playbook:run",
        method="POST",
        path="/api/playbook/run",
        status_code=200,
        user_id=current_user.id,
        target_type="playbook_run",
        target_id=result.id,
        extra_json={
            "playbook_name": request.playbook_name,
            "mode": request.mode,
        },
    )
    await session.commit()

    return result


@router.get("/runs", response_model=PlaybookRunListResponse)
async def list_playbook_runs(
    playbook_name: str | None = Query(None, description="Filter by playbook name"),
    status: str | None = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> PlaybookRunListResponse:
    """List playbook runs with pagination.

    Args:
        playbook_name: Optional filter by playbook name
        status: Optional filter by status
        page: Page number (1-indexed)
        page_size: Items per page
        session: Database session
        current_user: Authenticated user

    Returns:
        Paginated list of playbook runs

    Note:
        - admin/auditor: can see all runs
        - analyst: can only see their own runs
    """
    service = PlaybookRunService(session)

    # Non-admin users can only see their own runs
    user_id = (
        None
        if current_user.role in [UserRole.ADMIN, UserRole.AUDITOR]
        else current_user.id
    )

    return await service.list_runs(
        playbook_name=playbook_name,
        status=status,
        page=page,
        page_size=page_size,
        created_by_user_id=user_id,
    )


@router.get("/runs/{run_id}", response_model=PlaybookRunResponse)
async def get_playbook_run(
    run_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> PlaybookRunResponse:
    """Get a playbook run by ID.

    Args:
        run_id: Run ID
        session: Database session
        current_user: Authenticated user

    Returns:
        Playbook run details

    Raises:
        HTTPException: If run not found or user doesn't have permission

    Note:
        - admin/auditor: can see any run
        - analyst: can only see their own runs
    """
    service = PlaybookRunService(session)
    run = await service.get_run(run_id)

    if not run:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")

    # Check permission: non-admin users can only see their own runs
    if current_user.role not in [UserRole.ADMIN, UserRole.AUDITOR]:
        if run.created_by_user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Permission denied")

    return run


@router.get("/runs/{run_id}/steps", response_model=PlaybookRunWithStepsResponse)
async def get_playbook_run_steps(
    run_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> PlaybookRunWithStepsResponse:
    """Get a playbook run with all steps.

    Args:
        run_id: Run ID
        session: Database session
        current_user: Authenticated user

    Returns:
        Playbook run with step details

    Raises:
        HTTPException: If run not found or user doesn't have permission

    Note:
        - admin/auditor: can see any run
        - analyst: can only see their own runs
    """
    service = PlaybookRunService(session)
    result = await service.get_run_with_steps(run_id)

    if not result:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")

    # Check permission: non-admin users can only see their own runs
    if current_user.role not in [UserRole.ADMIN, UserRole.AUDITOR]:
        if result.run.created_by_user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Permission denied")

    return result


@router.post("/runs/{run_id}/resume", response_model=PlaybookResumeResponse)
async def resume_playbook_run(
    run_id: str,
    request: PlaybookResumeRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> PlaybookResumeResponse:
    """Resume a failed or partial playbook run.

    Args:
        run_id: Run ID to resume
        request: Resume request parameters
        session: Database session
        current_user: Authenticated user

    Returns:
        Updated run status

    Raises:
        HTTPException: If run cannot be resumed or user doesn't have permission

    Note:
        - admin/analyst: can resume runs they created or all runs (for admin)
        - auditor: cannot resume runs
        - apply mode: admin only
    """
    # Check permission
    if current_user.role == UserRole.AUDITOR:
        raise HTTPException(
            status_code=403,
            detail="Auditors cannot resume playbook runs",
        )

    # Check apply mode permission
    if request.run_mode == "apply" and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Playbook apply mode requires admin role",
        )

    service = PlaybookRunService(session)

    # Check if user can access this run
    run = await service.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")

    # Non-admin users can only resume their own runs
    if current_user.role != UserRole.ADMIN:
        if run.created_by_user_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="You can only resume your own runs",
            )

    try:
        result = await service.resume_run(
            run_id, request, created_by_user_id=current_user.id
        )

        # Create audit log
        audit_repo = AuditRepository(session)
        await audit_repo.create(
            action="playbook:resume",
            method="POST",
            path=f"/api/playbook/runs/{run_id}/resume",
            status_code=200,
            user_id=current_user.id,
            target_type="playbook_run",
            target_id=run_id,
            extra_json={
                "from_step_index": request.from_step_index,
                "run_mode": request.run_mode,
            },
        )
        await session.commit()

        return result

    except ValueError:
        raise HTTPException(status_code=400, detail="Bad request")


@router.get("/playbooks")
async def list_available_playbooks(
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user_optional),
) -> dict[str, object]:
    """Get list of available playbooks.

    Args:
        session: Database session
        current_user: Authenticated user (optional)

    Returns:
        Dictionary of available playbooks with metadata

    Note:
        This endpoint is accessible without authentication if allow_public_readonly is enabled
    """
    service = PlaybookRunService(session)
    return await service.get_available_playbooks()
