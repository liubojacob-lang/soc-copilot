"""Playbook API router for query and action generation."""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select

from core.logger import get_logger
from core.config import settings
from db.session import get_session
from models.user import UserModel, UserRole
from schemas.playbook import (
    GenerateQueriesRequest,
    GenerateQueriesResponse,
    GenerateActionsRequest,
    GenerateActionsResponse,
    PlaybookHistoryResponse,
)
from schemas.playbook_run import (
    PlaybookRunCreateRequest,
    PlaybookRunResponse,
    PlaybookRunListResponse,
    PlaybookResumeRequest,
    PlaybookResumeResponse,
    PlaybookRunWithStepsResponse,
)
from services.playbook_service import PlaybookService
from services.playbook_run_service import PlaybookRunService
from dependencies.auth import get_current_user, require_role, get_current_user_optional
from repositories.audit_repository import AuditRepository

logger = get_logger(__name__)

router = APIRouter(prefix="/api/playbook", tags=["playbook"])


@router.post("/queries", response_model=GenerateQueriesResponse)
async def generate_queries(
    request: GenerateQueriesRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> GenerateQueriesResponse:
    """Generate SIEM queries for multiple platforms.

    Args:
        request: Query generation request with IOCs or history_id
        session: Database session
        current_user: Authenticated user

    Returns:
        Generated queries for specified platforms
    """
    service = PlaybookService(session)
    result = await service.generate_queries(request)

    # Create audit log
    audit_repo = AuditRepository(session)
    await audit_repo.create(
        action="playbook:generate_queries",
        method="POST",
        path="/api/playbook/queries",
        status_code=200,
        user_id=current_user.id,
        extra_json={"module": request.module},
    )
    await session.commit()

    return result


@router.post("/actions", response_model=GenerateActionsResponse)
async def generate_actions(
    request: GenerateActionsRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> GenerateActionsResponse:
    """Generate remediation actions based on history record.

    Args:
        request: Actions generation request
        session: Database session
        current_user: Authenticated user

    Returns:
        Generated remediation actions with steps, verification, and rollback
    """
    service = PlaybookService(session)
    result = await service.generate_actions(request)

    # Create audit log
    audit_repo = AuditRepository(session)
    await audit_repo.create(
        action="playbook:generate_actions",
        method="POST",
        path="/api/playbook/actions",
        status_code=200,
        user_id=current_user.id,
        extra_json={"history_id": request.history_id, "policy": request.policy},
    )
    await session.commit()

    return result


@router.get("/history", response_model=PlaybookHistoryResponse)
async def get_playbook_history(
    history_id: str | None = Query(None, description="Filter by source history ID"),
    limit: int = Query(50, ge=1, le=200, description="Maximum records to return"),
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> PlaybookHistoryResponse:
    """Get playbook generation history.

    Args:
        history_id: Optional filter by source history record ID
        limit: Maximum number of records to return
        session: Database session
        current_user: Authenticated user

    Returns:
        Playbook history records
    """
    service = PlaybookService(session)
    return await service.get_history(history_id=history_id, limit=limit)


@router.get("/health")
async def health() -> dict[str, str]:
    """Playbook module health check."""
    return {"status": "ok", "module": "playbook", "version": "0.6.2"}


# ============================================
# Playbook Run Execution Endpoints (v0.6.1)
# ============================================

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
    user_id = None if current_user.role in [UserRole.ADMIN, UserRole.AUDITOR] else current_user.id

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
        result = await service.resume_run(run_id, request, created_by_user_id=current_user.id)

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

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


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


# ============================================
# DAG-Based Playbook Definition Endpoints (v0.7)
# ============================================

@router.get("/definitions")
async def list_playbook_definitions(
    is_active: bool | None = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict[str, object]:
    """List all DAG-based playbook definitions.

    Args:
        is_active: Optional filter by active status
        page: Page number (1-indexed)
        page_size: Items per page
        session: Database session
        current_user: Authenticated user

    Returns:
        Paginated list of playbook definitions
    """
    from repositories.playbook_definition_repository import PlaybookDefinitionRepository
    from models.playbook_definition import PlaybookDefinitionModel

    repo = PlaybookDefinitionRepository(session)

    stmt = select(PlaybookDefinitionModel)
    if is_active is not None:
        stmt = stmt.where(PlaybookDefinitionModel.is_active == is_active)

    stmt = stmt.order_by(PlaybookDefinitionModel.created_at.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)

    result = await session.execute(stmt)
    definitions = result.scalars().all()

    return {
        "definitions": [
            {
                "id": d.id,
                "name": d.name,
                "description": d.description,
                "version": d.version,
                "is_active": d.is_active,
                "created_at": d.created_at.isoformat(),
                "updated_at": d.updated_at.isoformat(),
            }
            for d in definitions
        ],
        "page": page,
        "page_size": page_size,
    }


@router.post("/definitions")
async def create_playbook_definition(
    request: dict,
    name: str = Query(..., description="Playbook definition name"),
    description: str | None = Query(None, description="Playbook description"),
    version: str = Query("1.0.0", description="Definition version"),
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict[str, object]:
    """Create a new DAG-based playbook definition.

    Args:
        request: Request body containing definition_json
        name: Playbook name
        description: Optional description
        version: Definition version
        session: Database session
        current_user: Authenticated user

    Returns:
        Created definition details
    """
    from models.playbook_definition import PlaybookDefinitionModel
    import uuid

    definition_json = request.get("definition_json", {})

    definition = PlaybookDefinitionModel(
        id=str(uuid.uuid4()),
        name=name,
        description=description,
        version=version,
        definition_json=definition_json,
        created_by=current_user.id,
        is_active=True,
    )

    session.add(definition)
    await session.commit()

    # Create audit log
    audit_repo = AuditRepository(session)
    await audit_repo.create(
        action="playbook:definition_created",
        method="POST",
        path="/api/playbook/definitions",
        status_code=200,
        user_id=current_user.id,
        target_type="playbook_definition",
        target_id=definition.id,
    )
    await session.commit()

    return {
        "id": definition.id,
        "name": definition.name,
        "description": definition.description,
        "version": definition.version,
        "is_active": definition.is_active,
        "created_at": definition.created_at.isoformat(),
    }


@router.get("/definitions/{definition_id}")
async def get_playbook_definition(
    definition_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict[str, object]:
    """Get a DAG-based playbook definition by ID.

    Args:
        definition_id: Definition ID
        session: Database session
        current_user: Authenticated user

    Returns:
        Definition details with nodes and edges
    """
    from models.playbook_definition import PlaybookDefinitionModel

    stmt = select(PlaybookDefinitionModel).where(
        PlaybookDefinitionModel.id == definition_id
    )
    result = await session.execute(stmt)
    definition = result.scalar_one_or_none()

    if not definition:
        raise HTTPException(status_code=404, detail=f"Definition not found: {definition_id}")

    return {
        "id": definition.id,
        "name": definition.name,
        "description": definition.description,
        "version": definition.version,
        "definition_json": definition.definition_json,
        "is_active": definition.is_active,
        "created_at": definition.created_at.isoformat(),
        "updated_at": definition.updated_at.isoformat(),
    }


@router.post("/definitions/{definition_id}/run")
async def execute_dag_definition(
    definition_id: str,
    request: dict,
    mode: str = Query("dry_run", description="Execution mode: dry_run or apply"),
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict[str, object]:
    """Execute a DAG-based playbook definition.

    Args:
        definition_id: Definition ID to execute
        request: Request body containing input_json
        mode: Execution mode (dry_run or apply)
        session: Database session
        current_user: Authenticated user

    Returns:
        Execution result with run_id and status

    Raises:
        HTTPException: If mode is apply and user is not admin
    """
    # Check apply mode permission
    if mode == "apply" and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Playbook apply mode requires admin role",
        )

    from models.playbook_definition import PlaybookDefinitionModel
    from repositories.playbook_run_repository import PlaybookRunRepository
    from playbook_engine.dag import DAGBuilder, DAGExecutionEngine
    import uuid

    input_json = request.get("input_json", {})

    # Get definition
    stmt = select(PlaybookDefinitionModel).where(
        PlaybookDefinitionModel.id == definition_id
    )
    result = await session.execute(stmt)
    definition = result.scalar_one_or_none()

    if not definition:
        raise HTTPException(status_code=404, detail=f"Definition not found: {definition_id}")

    if not definition.is_active:
        raise HTTPException(status_code=400, detail="Definition is not active")

    # Create run record
    run_repo = PlaybookRunRepository(session)
    run_id = str(uuid.uuid4())

    await run_repo.create(
        playbook_name=definition.name,
        playbook_version=definition.version,
        mode=mode,
        status="running",
        created_by_user_id=current_user.id,
        input_json=input_json or {},
        output_json={},
        execution_mode="dag",
        definition_id=definition.id,
        trigger_source="manual",
    )

    await session.flush()

    # Parse and execute DAG
    dag_definition = DAGBuilder.from_json(definition.definition_json)
    engine = DAGExecutionEngine(session)

    result_data = await engine.execute_dag(
        definition=dag_definition,
        run_id=run_id,
        input_json=input_json or {},
        mode=mode,
        created_by_user_id=current_user.id,
    )

    # Create audit log
    audit_repo = AuditRepository(session)
    await audit_repo.create(
        action="playbook:dag_executed",
        method="POST",
        path=f"/api/playbook/definitions/{definition_id}/run",
        status_code=200,
        user_id=current_user.id,
        target_type="playbook_run",
        target_id=run_id,
        extra_json={
            "definition_id": definition_id,
            "mode": mode,
        },
    )
    await session.commit()

    return {
        "run_id": run_id,
        "status": result_data["status"],
        "failed_nodes": result_data.get("failed_nodes", []),
        "skipped_nodes": result_data.get("skipped_nodes", []),
    }


@router.get("/runs/{run_id}/nodes")
async def get_playbook_run_nodes(
    run_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict[str, object]:
    """Get node execution details for a DAG run.

    Args:
        run_id: Run ID
        session: Database session
        current_user: Authenticated user

    Returns:
        Node execution details
    """
    from models.playbook_definition import PlaybookNodeRunModel

    # Verify run access
    from repositories.playbook_run_repository import PlaybookRunRepository
    run_repo = PlaybookRunRepository(session)
    run = await run_repo.get_by_id(run_id)

    if not run:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")

    if current_user.role not in [UserRole.ADMIN, UserRole.AUDITOR]:
        if run.created_by_user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Permission denied")

    # Get node runs
    stmt = select(PlaybookNodeRunModel).where(
        PlaybookNodeRunModel.run_id == run_id
    ).order_by(PlaybookNodeRunModel.created_at)

    result = await session.execute(stmt)
    node_runs = result.scalars().all()

    return {
        "run_id": run_id,
        "nodes": [
            {
                "id": nr.id,
                "node_id": nr.node_id,
                "step_id": nr.step_id,
                "status": nr.status,
                "started_at": nr.started_at.isoformat() if nr.started_at else None,
                "finished_at": nr.finished_at.isoformat() if nr.finished_at else None,
                "duration_ms": nr.duration_ms,
                "output": nr.output_json,
                "error": nr.error_message,
            }
            for nr in node_runs
        ],
    }


# ============================================================================
# Approval API Endpoints (v0.7.2)
# ============================================================================

from datetime import datetime, timezone
from models.playbook_approval import PlaybookApprovalModel
from models.playbook_run import PlaybookRunModel
from sqlalchemy import select, and_, or_
from pydantic import BaseModel


class ApprovalListResponse(BaseModel):
    """Response for approval list."""
    items: list[dict]
    total: int
    page: int
    page_size: int


class ApprovalActionRequest(BaseModel):
    """Request for approve/reject action."""
    comments: str | None = None


@router.get("/approvals", response_model=ApprovalListResponse)
async def list_approvals(
    status: str | None = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> ApprovalListResponse:
    """List approval requests.

    - admin/auditor: can see all pending approvals
    - analyst: can only see their own approval requests
    """
    from repositories.user_repository import UserRepository

    user_repo = UserRepository(session)

    # Build base query
    stmt = select(PlaybookApprovalModel)

    # Role-based filtering
    if current_user.role == UserRole.ANALYST:
        # Analysts can only see their own requests
        stmt = stmt.where(
            PlaybookApprovalModel.requested_by_user_id == current_user.id
        )
    # admin and auditor can see all

    # Status filter
    if status:
        stmt = stmt.where(PlaybookApprovalModel.status == status)

    # Order by created_at desc (newest first)
    stmt = stmt.order_by(PlaybookApprovalModel.created_at.desc())

    # Get total count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await session.execute(count_stmt)
    total = total_result.scalar_one() or 0

    # Apply pagination
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)

    # Execute query
    result = await session.execute(stmt)
    approvals = result.scalars().all()

    # Get usernames
    items = []
    for approval in approvals:
        requested_by = None
        if approval.requested_by_user_id:
            user_result = await session.execute(
                select(UserModel.username).where(UserModel.id == approval.requested_by_user_id)
            )
            requested_by = user_result.scalar_one_or_none()

        approved_by = None
        if approval.approved_by_user_id:
            user_result = await session.execute(
                select(UserModel.username).where(UserModel.id == approval.approved_by_user_id)
            )
            approved_by = user_result.scalar_one_or_none()

        rejected_by = None
        if approval.rejected_by_user_id:
            user_result = await session.execute(
                select(UserModel.username).where(UserModel.id == approval.rejected_by_user_id)
            )
            rejected_by = user_result.scalar_one_or_none()

        items.append({
            "id": approval.id,
            "run_id": approval.run_id,
            "node_id": approval.node_id,
            "status": approval.status,
            "title": approval.title,
            "message": approval.message,
            "comments": approval.comments,
            "requested_by": requested_by,
            "approved_by": approved_by,
            "rejected_by": rejected_by,
            "created_at": approval.created_at.isoformat() if approval.created_at else None,
            "decided_at": approval.decided_at.isoformat() if approval.decided_at else None,
            "expires_at": approval.expires_at.isoformat() if approval.expires_at else None,
        })

    return ApprovalListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/approvals/{approval_id}/approve")
async def approve_approval(
    approval_id: str,
    request: ApprovalActionRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict:
    """Approve an approval request.

    Only admin and auditor roles can approve.
    Analysts cannot approve (to avoid self-approval).

    Approval will:
    1. Update approval status to 'approved'
    2. Log to audit_logs
    3. Resume playbook execution
    """
    from sqlalchemy import func

    # Check permissions - only admin and auditor can approve
    if current_user.role not in [UserRole.ADMIN, UserRole.AUDITOR]:
        raise HTTPException(
            status_code=403,
            detail="Only admin and auditor roles can approve requests"
        )

    # Get approval
    stmt = select(PlaybookApprovalModel).where(
        PlaybookApprovalModel.id == approval_id
    )
    result = await session.execute(stmt)
    approval = result.scalar_one_or_none()

    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")

    if approval.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Approval is not pending (current status: {approval.status})"
        )

    # Check if expired
    if approval.expires_at and approval.expires_at < datetime.now(timezone.utc):
        approval.status = "expired"
        await session.commit()
        raise HTTPException(status_code=400, detail="Approval has expired")

    # Update approval
    approval.status = "approved"
    approval.approved_by_user_id = current_user.id
    approval.decided_at = datetime.now(timezone.utc)
    approval.comments = request.comments

    # Audit log
    audit_repo = AuditRepository(session)
    await audit_repo.create(
        action="approval:approve",
        method="POST",
        path=f"/api/playbook/approvals/{approval_id}/approve",
        status_code=200,
        user_id=current_user.id,
        target_type="approval",
        target_id=approval_id,
        extra_json={
            "run_id": approval.run_id,
            "node_id": approval.node_id,
            "comments": request.comments,
        },
    )

    await session.commit()

    # Resume playbook execution
    try:
        from services.playbook_run_service import PlaybookRunService
        run_service = PlaybookRunService(session)

        await run_service.resume_from_approval(
            run_id=approval.run_id,
            node_id=approval.node_id,
            approved=True,
            comments=request.comments,
        )

        logger.info(
            f"[{approval.run_id}] Approval {approval_id} approved by {current_user.username}, "
            f"resuming execution"
        )

    except Exception as e:
        logger.error(f"[{approval.run_id}] Failed to resume execution: {e}")
        # Don't fail the request - approval was recorded
        pass

    return {
        "message": "Approval approved",
        "approval_id": approval_id,
        "status": "approved",
    }


@router.post("/approvals/{approval_id}/reject")
async def reject_approval(
    approval_id: str,
    request: ApprovalActionRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict:
    """Reject an approval request.

    Only admin and auditor roles can reject.
    """
    from sqlalchemy import func

    # Check permissions - only admin and auditor can reject
    if current_user.role not in [UserRole.ADMIN, UserRole.AUDITOR]:
        raise HTTPException(
            status_code=403,
            detail="Only admin and auditor roles can reject requests"
        )

    # Get approval
    stmt = select(PlaybookApprovalModel).where(
        PlaybookApprovalModel.id == approval_id
    )
    result = await session.execute(stmt)
    approval = result.scalar_one_or_none()

    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")

    if approval.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Approval is not pending (current status: {approval.status})"
        )

    # Check if expired
    if approval.expires_at and approval.expires_at < datetime.now(timezone.utc):
        approval.status = "expired"
        await session.commit()
        raise HTTPException(status_code=400, detail="Approval has expired")

    # Update approval
    approval.status = "rejected"
    approval.rejected_by_user_id = current_user.id
    approval.decided_at = datetime.now(timezone.utc)
    approval.comments = request.comments

    # Audit log
    audit_repo = AuditRepository(session)
    await audit_repo.create(
        action="approval:reject",
        method="POST",
        path=f"/api/playbook/approvals/{approval_id}/reject",
        status_code=200,
        user_id=current_user.id,
        target_type="approval",
        target_id=approval_id,
        extra_json={
            "run_id": approval.run_id,
            "node_id": approval.node_id,
            "comments": request.comments,
        },
    )

    await session.commit()

    # Update node status to failed
    from models.playbook_node_run import PlaybookNodeRunModel

    stmt = select(PlaybookNodeRunModel).where(
        PlaybookNodeRunModel.run_id == approval.run_id,
        PlaybookNodeRunModel.node_id == approval.node_id,
    )
    result = await session.execute(stmt)
    node_run = result.scalar_one_or_none()

    if node_run:
        node_run.status = "failed"
        node_run.error_message = f"Approval rejected: {request.comments or 'No reason provided'}"
        node_run.finished_at = datetime.now(timezone.utc)
        await session.commit()

    logger.info(
        f"[{approval.run_id}] Approval {approval_id} rejected by {current_user.username}"
    )

    return {
        "message": "Approval rejected",
        "approval_id": approval_id,
        "status": "rejected",
    }


@router.get("/approvals/pending/count")
async def get_pending_approvals_count(
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict:
    """Get count of pending approvals.

    - admin/auditor: count of all pending approvals
    - analyst: count of their own pending approvals
    """
    from sqlalchemy import func

    stmt = select(func.count()).select_from(PlaybookApprovalModel).where(
        PlaybookApprovalModel.status == "pending"
    )

    if current_user.role == UserRole.ANALYST:
        stmt = stmt.where(
            PlaybookApprovalModel.requested_by_user_id == current_user.id
        )

    result = await session.execute(stmt)
    count = result.scalar_one() or 0

    return {"count": count, "status": "pending"}


# ============================================
# v0.7.3: Version Management Endpoints
# ============================================

@router.post("/definitions/{definition_id}/publish")
async def publish_playbook_definition(
    definition_id: str,
    request: dict = None,  # Optional: {"change_note": "..."}
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict:
    """Publish a draft playbook definition.

    Creates a version snapshot and sets status to published.
    Published definitions cannot be modified.

    - RBAC: admin and analyst can publish
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.ANALYST]:
        raise HTTPException(status_code=403, detail="Only admin and analyst can publish definitions")

    from services.playbook_version_service import PlaybookVersionService
    from models.playbook_definition import PlaybookDefinitionModel
    from sqlalchemy import select

    version_service = PlaybookVersionService(session)
    change_note = (request or {}).get("change_note") if request else None

    try:
        definition = await version_service.publish_definition(
            definition_id=definition_id,
            change_note=change_note,
            created_by_user_id=current_user.id
        )

        # Audit log
        audit_repo = AuditRepository(session)
        await audit_repo.create(
            action="playbook.publish",
            method="POST",
            path=f"/api/playbook/definitions/{definition_id}/publish",
            status_code=200,
            user_id=current_user.id,
            target_type="playbook_definition",
            target_id=definition_id,
            extra_json={
                "name": definition.name,
                "version_no": definition.current_version_no,
                "change_note": change_note,
            },
        )
        await session.commit()

        return {
            "message": "Playbook definition published successfully",
            "definition_id": definition_id,
            "version_no": definition.current_version_no,
            "status": definition.status,
            "published_at": definition.published_at.isoformat() if definition.published_at else None,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/definitions/{definition_id}/versions")
async def get_playbook_version_history(
    definition_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict:
    """Get version history for a playbook definition.

    - RBAC: All authenticated users can view version history
    """
    from services.playbook_version_service import PlaybookVersionService

    version_service = PlaybookVersionService(session)

    try:
        history = await version_service.get_version_history(definition_id)

        return {
            "definition_id": definition_id,
            "versions": [v.model_dump(mode='json') for v in history.versions],
            "total": history.total,
            "current_version_no": history.current_version_no,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/definitions/{definition_id}/restore/{version_no}")
async def restore_playbook_definition_version(
    definition_id: str,
    version_no: int,
    request: dict = None,  # Optional: {"change_note": "..."}
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict:
    """Restore a playbook definition from a historical version.

    Creates a new draft with content from the specified version.
    Original version is preserved in history.

    - RBAC: admin and analyst can restore versions
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.ANALYST]:
        raise HTTPException(status_code=403, detail="Only admin and analyst can restore versions")

    from services.playbook_version_service import PlaybookVersionService

    version_service = PlaybookVersionService(session)
    change_note = (request or {}).get("change_note") if request else None

    try:
        definition = await version_service.restore_from_version(
            definition_id=definition_id,
            version_no=version_no,
            change_note=change_note or f"Restored from version {version_no}",
            created_by_user_id=current_user.id
        )

        # Audit log
        audit_repo = AuditRepository(session)
        await audit_repo.create(
            action="playbook.restore",
            method="POST",
            path=f"/api/playbook/definitions/{definition_id}/restore/{version_no}",
            status_code=200,
            user_id=current_user.id,
            target_type="playbook_definition",
            target_id=definition_id,
            extra_json={
                "name": definition.name,
                "from_version_no": version_no,
                "new_version_no": definition.current_version_no,
            },
        )
        await session.commit()

        return {
            "message": "Playbook definition restored successfully",
            "definition_id": definition_id,
            "restored_from_version": version_no,
            "new_version_no": definition.current_version_no,
            "status": definition.status,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================
# v0.7.3: Replay Endpoints
# ============================================

@router.post("/runs/{run_id}/replay")
async def replay_playbook_run(
    run_id: str,
    request: dict,  # {"mode": "dry_run"|"apply", "override_context": {...}}
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict:
    """Replay a playbook run with historical input.

    Creates a new run with the same input context and definition.
    Optionally allows overriding context values.

    - RBAC: All users can replay their own runs; admin/auditor can replay any run

    Args:
        run_id: Original run ID to replay
        request: {"mode": "dry_run"|"apply", "override_context": {...}}

    Returns:
        New replay run details
    """
    # Check apply mode permission
    mode = request.get("mode", "dry_run")
    if mode == "apply" and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Playbook replay with apply mode requires admin role",
        )

    from services.playbook_replay_service import get_replay_service
    from models.playbook_run import PlaybookRunModel
    from sqlalchemy import select

    # Check if user can replay this run
    stmt = select(PlaybookRunModel).where(PlaybookRunModel.id == run_id)
    result = await session.execute(stmt)
    original_run = result.scalar_one_or_none()

    if not original_run:
        raise HTTPException(status_code=404, detail="Run not found")

    # Check permissions
    if (original_run.created_by_user_id != current_user.id and
        current_user.role not in [UserRole.ADMIN, UserRole.AUDITOR]):
        raise HTTPException(
            status_code=403,
            detail="You can only replay your own runs",
        )

    replay_service = get_replay_service(session)

    try:
        replay_result = await replay_service.replay_run(
            run_id=run_id,
            mode=mode,
            override_context=request.get("override_context"),
            created_by_user_id=current_user.id
        )

        # Audit log
        audit_repo = AuditRepository(session)
        await audit_repo.create(
            action="playbook.replay",
            method="POST",
            path=f"/api/playbook/runs/{run_id}/replay",
            status_code=200,
            user_id=current_user.id,
            target_type="playbook_run",
            target_id=replay_result.run_id,
            extra_json={
                "original_run_id": run_id,
                "mode": mode,
            },
        )
        await session.commit()

        return {
            "run_id": replay_result.run_id,
            "original_run_id": replay_result.original_run_id,
            "mode": replay_result.mode,
            "status": replay_result.status,
            "message": replay_result.message,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/runs/{run_id}/replay-chain")
async def get_playbook_replay_chain(
    run_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict:
    """Get the replay chain for a playbook run.

    Traverses from the root run to the latest replay.

    - RBAC: All authenticated users can view replay chains
    """
    from services.playbook_replay_service import get_replay_service

    replay_service = get_replay_service(session)

    try:
        chain = await replay_service.get_replay_chain(run_id)

        return {
            "root_run_id": chain.root_run_id,
            "chain": [node.model_dump(mode='json') for node in chain.chain],
            "total": chain.total,
            "depth": chain.depth,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ============================================
# v0.7.3: Import/Export Endpoints
# ============================================

@router.get("/definitions/{definition_id}/export")
async def export_playbook_definition(
    definition_id: str,
    format: str = Query("json", regex="^(json|yaml)$", description="Export format"),
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict:
    """Export a playbook definition to JSON or YAML.

    - RBAC: All authenticated users can export definitions

    Args:
        definition_id: ID of the definition to export
        format: Export format ('json' or 'yaml')

    Returns:
        Export data with content and mime_type
    """
    from services.playbook_import_export_service import get_import_export_service

    export_service = get_import_export_service(session)

    try:
        content, mime_type = await export_service.export_definition(
            definition_id=definition_id,
            format=format
        )

        # Audit log
        audit_repo = AuditRepository(session)
        await audit_repo.create(
            action="playbook.export",
            method="GET",
            path=f"/api/playbook/definitions/{definition_id}/export",
            status_code=200,
            user_id=current_user.id,
            target_type="playbook_definition",
            target_id=definition_id,
            extra_json={"format": format},
        )
        await session.commit()

        return {
            "definition_id": definition_id,
            "format": format,
            "content": content,
            "mime_type": mime_type,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/definitions/import")
async def import_playbook_definition(
    request: dict,  # {"format": "json"|"yaml", "content": "...", "name": "...", "publish": bool}
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict:
    """Import a playbook definition from JSON or YAML.

    Creates a new draft definition (or published if publish=true).

    - RBAC: admin and analyst can import definitions

    Args:
        request: {
            "format": "json"|"yaml",
            "content": "...",
            "name": "...",  # Optional: override name
            "publish": false  # Optional: auto-publish
        }

    Returns:
        Imported definition details
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.ANALYST]:
        raise HTTPException(status_code=403, detail="Only admin and analyst can import definitions")

    from services.playbook_import_export_service import get_import_export_service

    import_service = get_import_export_service(session)

    format = request.get("format", "json")
    content = request.get("content", "")
    name_override = request.get("name")
    publish = request.get("publish", False)

    if not content:
        raise HTTPException(status_code=400, detail="Content is required")

    try:
        result = await import_service.import_definition(
            content=content,
            format=format,
            name_override=name_override,
            publish=publish,
            created_by_user_id=current_user.id
        )

        # Audit log
        audit_repo = AuditRepository(session)
        await audit_repo.create(
            action="playbook.import",
            method="POST",
            path="/api/playbook/definitions/import",
            status_code=200,
            user_id=current_user.id,
            target_type="playbook_definition",
            target_id=result.definition_id,
            extra_json={
                "name": result.name,
                "version": result.version,
                "format": format,
            },
        )
        await session.commit()

        return {
            "definition_id": result.definition_id,
            "name": result.name,
            "version": result.version,
            "status": result.status,
            "message": result.message,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

