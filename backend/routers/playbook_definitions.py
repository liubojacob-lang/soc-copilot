"""Router for DAG playbook definitions and execution.

v0.9.0: DAG execution logic extracted to services/playbook/dag_execution_service.py.
        Internal API endpoints moved to routers/playbook/internal.py.

Provides:
- CRUD for playbook definitions
- Playbook execution (dry_run / apply)
- Run status queries and cancellation
- Queue statistics
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.logger import get_logger
from db.session import get_session
from dependencies.auth import get_current_user
from middleware.rate_limiter import rate_limit
from models.user import UserModel, UserRole
from repositories.playbook_definition_repository import PlaybookDefinitionRepository
from repositories.playbook_node_run_repository import PlaybookNodeRunRepository
from repositories.playbook_run_repository import PlaybookRunRepository
from schemas.playbook_run import (
    DAGNodeRunResponse,
    DAGPlaybookRunCreate,
    DAGPlaybookRunResponse,
    PlaybookDefinitionCreate,
    PlaybookDefinitionListResponse,
    PlaybookDefinitionResponse,
    PlaybookDefinitionUpdate,
    PlaybookRunCancelRequest,
    PlaybookRunCancelResponse,
    PlaybookRunErrorResponse,
)
from services.playbook.dag_execution_service import DAGExecutionService
from services.playbook.playbook_dag_compiler import DAGCompiler, DAGValidationError
from services.run_queue_manager import get_run_queue_manager

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/playbook-definitions", tags=["playbook-definitions"])


# ============ Playbook Definition CRUD ============


@router.post(
    "", response_model=PlaybookDefinitionResponse, status_code=status.HTTP_201_CREATED
)
async def create_definition(
    data: PlaybookDefinitionCreate,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Create a new DAG playbook definition (admin/analyst only)."""
    if current_user.role not in (UserRole.ADMIN, UserRole.ANALYST):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    repo = PlaybookDefinitionRepository(db)

    # Validate and compile DAG
    try:
        compiled = await DAGCompiler.validate_and_compile(data.dag)
    except DAGValidationError as e:
        logger.warning(f"DAG validation failed for playbook definition: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"剧本 DAG 验证失败: {e}",
        )

    definition = await repo.create(
        name=data.name,
        version=data.version,
        description=data.description,
        dag_json=data.dag,
        created_by_user_id=current_user.id,
        is_active=data.is_active,
    )
    await db.commit()

    return PlaybookDefinitionResponse(
        id=definition.id,
        name=definition.name,
        version=definition.version,
        description=definition.description,
        dag=definition.definition_json,
        created_by_user_id=definition.created_by,
        created_at=definition.created_at,
        updated_at=definition.updated_at,
        is_active=definition.is_active,
        status=getattr(
            definition, "status", "published" if definition.is_active else "draft"
        ),
        node_count=compiled["node_count"],
        edge_count=compiled["edge_count"],
    )


@router.get("", response_model=PlaybookDefinitionListResponse)
async def list_definitions(
    is_active: bool | None = None,
    page: int = 1,
    page_size: int = 50,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """List all DAG playbook definitions."""
    repo = PlaybookDefinitionRepository(db)
    items, total = await repo.list_definitions(
        is_active=is_active,
        page=page,
        page_size=page_size,
    )

    return PlaybookDefinitionListResponse(
        items=[
            PlaybookDefinitionResponse(
                id=item.id,
                name=item.name,
                version=item.version,
                description=item.description,
                dag=item.definition_json,
                created_by_user_id=item.created_by,
                created_at=item.created_at,
                updated_at=item.updated_at,
                is_active=item.is_active,
                status=getattr(
                    item, "status", "published" if item.is_active else "draft"
                ),
                node_count=len(item.definition_json.get("nodes", [])),
                edge_count=len(item.definition_json.get("edges", [])),
            )
            for item in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


# ============ Queue Stats ============
# IMPORTANT: Must be defined before /{definition_id} to avoid route conflict


@router.get("/queue-stats")
async def get_queue_stats(
    current_user: UserModel = Depends(get_current_user),
):
    """Get run queue statistics (all authenticated users)."""
    queue_manager = get_run_queue_manager()
    if not queue_manager:
        return {
            "running": 0,
            "queued": 0,
            "max_concurrent": settings.run_queue_max,
            "has_capacity": True,
        }
    return await queue_manager.get_queue_stats()


@router.get("/{definition_id}", response_model=PlaybookDefinitionResponse)
async def get_definition(
    definition_id: str,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Get a specific DAG playbook definition."""
    repo = PlaybookDefinitionRepository(db)
    definition = await repo.get_by_id(definition_id)

    if not definition:
        raise HTTPException(status_code=404, detail="Definition not found")

    return PlaybookDefinitionResponse(
        id=definition.id,
        name=definition.name,
        version=definition.version,
        description=definition.description,
        dag=definition.definition_json,
        created_by_user_id=definition.created_by,
        created_at=definition.created_at,
        updated_at=definition.updated_at,
        is_active=definition.is_active,
        status=getattr(
            definition, "status", "published" if definition.is_active else "draft"
        ),
        node_count=len(definition.definition_json.get("nodes", [])),
        edge_count=len(definition.definition_json.get("edges", [])),
    )


@router.patch("/{definition_id}", response_model=PlaybookDefinitionResponse)
async def update_definition(
    definition_id: str,
    data: PlaybookDefinitionUpdate,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Update a DAG playbook definition (admin/analyst only)."""
    if current_user.role not in (UserRole.ADMIN, UserRole.ANALYST):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    repo = PlaybookDefinitionRepository(db)

    # Validate DAG if provided
    if data.dag:
        try:
            await DAGCompiler.validate_and_compile(data.dag)
        except DAGValidationError as e:
            logger.warning(f"DAG validation failed during update: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"剧本 DAG 验证失败: {e}",
            )

    update_data = data.model_dump(exclude_unset=True)
    definition = await repo.update(
        definition_id,
        **{k: v for k, v in update_data.items() if k != "dag"},
        dag_json=data.dag if data.dag else None,
    )

    if not definition:
        raise HTTPException(status_code=404, detail="Definition not found")

    await db.commit()

    return PlaybookDefinitionResponse(
        id=definition.id,
        name=definition.name,
        version=definition.version,
        description=definition.description,
        dag=definition.definition_json,
        created_by_user_id=definition.created_by,
        created_at=definition.created_at,
        updated_at=definition.updated_at,
        is_active=definition.is_active,
        status=getattr(
            definition, "status", "published" if definition.is_active else "draft"
        ),
        node_count=len(definition.definition_json.get("nodes", [])),
        edge_count=len(definition.definition_json.get("edges", [])),
    )


@router.delete("/{definition_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_definition(
    definition_id: str,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Delete a DAG playbook definition (admin only)."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403, detail="Only admins can delete definitions"
        )

    repo = PlaybookDefinitionRepository(db)
    success = await repo.delete(definition_id)

    if not success:
        raise HTTPException(
            status_code=404, detail="Definition not found or has associated runs"
        )

    await db.commit()


# ============ DAG Playbook Execution ============


@router.post(
    "/{definition_id}/run",
    response_model=DAGPlaybookRunResponse | PlaybookRunErrorResponse,
    responses={500: {"model": PlaybookRunErrorResponse}},
)
@rate_limit(max_requests=5, window_seconds=60)
async def run_dag_playbook(
    definition_id: str,
    data: DAGPlaybookRunCreate,
    request: Request,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Execute a DAG playbook (admin/analyst for dry_run, admin only for apply).

    v0.9.0: Execution logic delegated to DAGExecutionService.
    v0.7.4: Supports queue management, dry_run isolation, structured error handling.

    dry_run mode guarantees:
    - No database writes (except run record for tracking)
    - No audit_logs entries
    - No external network calls (OTX/VT/etc)
    - DAG validation + mock execution only
    """
    try:
        svc = DAGExecutionService(session=db)
        return await svc.execute(
            definition_id=definition_id,
            data=data,
            current_user_id=str(current_user.id),
            current_username=current_user.username,
            current_user_role=current_user.role,
        )
    except HTTPException:
        raise
    except Exception:
        trace_id = str(uuid.uuid4())
        logger.exception(f"[{trace_id}] run_dag_playbook failed")
        return PlaybookRunErrorResponse(
            success=False,
            error_code="PLAYBOOK_RUN_FAILED",
            message="Internal error during playbook execution. Check server logs for details.",
            details={"definition_id": definition_id, "mode": data.mode},
            trace_id=trace_id,
        )


# ============ DAG Run Status ============


@router.get("/runs/{run_id}", response_model=DAGPlaybookRunResponse)
async def get_dag_run(
    run_id: str,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Get DAG playbook run status with node summary."""
    run_repo = PlaybookRunRepository(db)
    run = await run_repo.get_by_id(run_id)

    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    node_run_repo = PlaybookNodeRunRepository(db)
    summary = await node_run_repo.get_run_summary(run_id)

    return DAGPlaybookRunResponse(
        id=run.id,
        playbook_name=run.playbook_name,
        playbook_version=run.playbook_version,
        engine_version=run.engine_version,
        mode=run.mode,
        status=run.status,
        failure_strategy=run.failure_strategy,
        created_by_user_id=run.created_by_user_id,
        input_json=run.input_json,
        output_json=run.output_json,
        started_at=run.started_at,
        finished_at=run.finished_at,
        error_message=run.error_message,
        definition_id=run.definition_id,
        execution_mode=run.execution_mode,
        total_nodes=summary.get("total", 0),
        completed_nodes=summary.get("success", 0),
        failed_nodes=summary.get("failed", 0),
        running_nodes=summary.get("running", 0),
        pending_nodes=summary.get("pending", 0),
        cancel_requested_at=None,
        can_resume=run.status in ("failed", "partial"),
    )


@router.get("/runs/{run_id}/nodes", response_model=list[DAGNodeRunResponse])
async def get_dag_run_nodes(
    run_id: str,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Get all node runs for a DAG run."""
    run_repo = PlaybookRunRepository(db)
    run = await run_repo.get_by_id(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    node_run_repo = PlaybookNodeRunRepository(db)
    node_runs = await node_run_repo.list_by_run(run_id)

    return [
        DAGNodeRunResponse(
            id=nr.id,
            run_id=nr.run_id,
            node_id=nr.node_id,
            node_name=nr.node_name,
            node_type=nr.node_type,
            status=nr.status,
            started_at=nr.started_at,
            finished_at=nr.finished_at,
            attempt_count=nr.attempt_count,
            last_error=nr.last_error,
            output_json=nr.output_json or {},
            input_json=nr.input_json or {},
            created_at=nr.created_at,
        )
        for nr in node_runs
    ]


@router.post("/runs/{run_id}/cancel", response_model=PlaybookRunCancelResponse)
async def cancel_dag_run(
    run_id: str,
    data: PlaybookRunCancelRequest,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Cancel a running DAG playbook (admin/analyst only)."""
    if current_user.role not in (UserRole.ADMIN, UserRole.ANALYST):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    svc = DAGExecutionService(session=db)
    result = await svc.cancel_run(run_id, data.reason or "Cancelled by user")

    if result["status"] == "not_found":
        raise HTTPException(status_code=404, detail="Run not found")
    if result["status"] == "invalid_state":
        raise HTTPException(status_code=400, detail=result["message"])

    return PlaybookRunCancelResponse(
        run_id=run_id,
        status="cancelled",
        message="Run cancelled successfully",
    )
