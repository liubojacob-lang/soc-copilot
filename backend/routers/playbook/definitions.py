"""DAG-based playbook definition endpoints (S0-10: Pydantic schemas + S0-8/9: Service layer).

This module contains endpoints for:
- Listing and creating playbook definitions
- Getting definition details
- Executing DAG definitions
- Getting node execution details
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from db.session import get_session
from dependencies.auth import get_current_user
from models.user import UserModel, UserRole
from repositories.audit_repository import AuditRepository
from schemas.playbook import DAGExecutionRequest, PlaybookDefinitionCreate

logger = get_logger(__name__)

router = APIRouter(tags=["playbook-definitions"])


@router.get("/definitions")
async def list_playbook_definitions(
    is_active: bool | None = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict[str, object]:
    """List all DAG-based playbook definitions."""
    from services.playbook.playbook_service import PlaybookService

    svc = PlaybookService(session)
    return await svc.list_definitions(
        is_active=is_active,
        page=page,
        page_size=page_size,
    )


@router.post("/definitions")
async def create_playbook_definition(
    body: PlaybookDefinitionCreate,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict[str, object]:
    """Create a new DAG-based playbook definition."""
    from services.playbook.playbook_service import PlaybookService

    svc = PlaybookService(session)

    definition = await svc.create_definition(
        name=body.name,
        description=body.description,
        version=body.version,
        definition_json=body.definition_json,
        created_by=current_user.id,
    )

    # Create audit log
    audit_repo = AuditRepository(session)
    await audit_repo.create(
        action="playbook:definition_created",
        method="POST",
        path="/api/v1/playbook/definitions",
        status_code=200,
        user_id=current_user.id,
        target_type="playbook_definition",
        target_id=definition["id"],
    )
    await session.commit()

    return definition


@router.get("/definitions/{definition_id}")
async def get_playbook_definition(
    definition_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict[str, object]:
    """Get a DAG-based playbook definition by ID."""
    from services.playbook.playbook_service import PlaybookService

    svc = PlaybookService(session)
    definition = await svc.get_definition(definition_id)

    if not definition:
        raise HTTPException(
            status_code=404, detail=f"Definition not found: {definition_id}"
        )

    return definition


@router.post("/definitions/{definition_id}/run")
async def execute_dag_definition(
    definition_id: str,
    body: DAGExecutionRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict[str, object]:
    """Execute a DAG-based playbook definition."""
    # Check apply mode permission
    if body.mode == "apply" and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Playbook apply mode requires admin role",
        )

    from services.playbook.playbook_service import PlaybookService

    svc = PlaybookService(session)

    try:
        result = await svc.execute_dag_definition(
            definition_id=definition_id,
            input_json=body.input_json,
            mode=body.mode,
            created_by_user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Create audit log
    audit_repo = AuditRepository(session)
    await audit_repo.create(
        action="playbook:dag_executed",
        method="POST",
        path=f"/api/v1/playbook/definitions/{definition_id}/run",
        status_code=200,
        user_id=current_user.id,
        target_type="playbook_run",
        target_id=result["run_id"],
        extra_json={
            "definition_id": definition_id,
            "mode": body.mode,
        },
    )
    await session.commit()

    return result


@router.get("/runs/{run_id}/nodes")
async def get_playbook_run_nodes(
    run_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict[str, object]:
    """Get node execution details for a DAG run."""
    from models.playbook_node_run import PlaybookNodeRunModel
    from repositories.playbook_run_repository import PlaybookRunRepository

    # Verify run access
    run_repo = PlaybookRunRepository(session)
    run = await run_repo.get_by_id(run_id)

    if not run:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")

    if current_user.role not in [UserRole.ADMIN, UserRole.AUDITOR]:
        if run.created_by_user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Permission denied")

    # Get node runs
    stmt = (
        select(PlaybookNodeRunModel)
        .where(PlaybookNodeRunModel.run_id == run_id)
        .order_by(PlaybookNodeRunModel.created_at)
    )

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
