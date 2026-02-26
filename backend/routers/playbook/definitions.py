"""DAG-based playbook definition endpoints.

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
from models.user import UserModel, UserRole
from dependencies.auth import get_current_user
from repositories.audit_repository import AuditRepository

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
    from models.playbook_definition import PlaybookDefinitionModel
    from sqlalchemy import func

    # Build base query with filter
    base_stmt = select(PlaybookDefinitionModel)
    if is_active is not None:
        base_stmt = base_stmt.where(PlaybookDefinitionModel.is_active == is_active)

    # Get total count efficiently using COUNT
    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    count_result = await session.execute(count_stmt)
    total = count_result.scalar() or 0

    # Get paginated results
    stmt = base_stmt.order_by(PlaybookDefinitionModel.created_at.desc())
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
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
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
