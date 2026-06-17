"""Router for DAG playbook definitions and execution."""

import traceback
import uuid
from datetime import UTC, datetime
from typing import Any, Union

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
from services.playbook.playbook_dag_compiler import DAGCompiler, DAGValidationError
from services.playbook.playbook_dag_scheduler import DAGScheduler
from services.run_queue_manager import get_run_queue_manager

logger = get_logger(__name__)

router = APIRouter(prefix="/api/playbook-definitions", tags=["playbook-definitions"])

# v0.7.4: Queue stats router
queue_router = APIRouter(prefix="/api/runs", tags=["runs"])


# ============ Playbook Definition CRUD ============


@router.post("", response_model=PlaybookDefinitionResponse, status_code=status.HTTP_201_CREATED)
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
    except DAGValidationError:
        raise HTTPException(status_code=400, detail="Invalid playbook definition")

    definition = await repo.create(
        name=data.name,
        version=data.version,
        description=data.description,
        dag_json=data.dag,
        created_by_user_id=current_user.id,
        is_active=data.is_active,
    )

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
                node_count=len(item.definition_json.get("nodes", [])),
                edge_count=len(item.definition_json.get("edges", [])),
            )
            for item in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


# ============ v0.7.4: Queue Stats ============
# IMPORTANT: This route MUST be defined before /{definition_id} to avoid being matched as a definition_id


@router.get("/queue-stats")
async def get_queue_stats(
    current_user: UserModel = Depends(get_current_user),
):
    """Get run queue statistics (all authenticated users)."""
    queue_manager = get_run_queue_manager()
    if not queue_manager:
        # Use configured max concurrent value for consistency
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
        except DAGValidationError:
            raise HTTPException(status_code=400, detail="Invalid playbook definition")

    update_data = data.model_dump(exclude_unset=True)
    definition = await repo.update(
        definition_id,
        **{k: v for k, v in update_data.items() if k != "dag"},
        dag_json=data.dag if data.dag else None,
    )

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
        raise HTTPException(status_code=403, detail="Only admins can delete definitions")

    repo = PlaybookDefinitionRepository(db)
    success = await repo.delete(definition_id)

    if not success:
        raise HTTPException(status_code=404, detail="Definition not found or has associated runs")


# ============ DAG Playbook Execution ============


@router.post(
    "/{definition_id}/run",
    response_model=Union[DAGPlaybookRunResponse, PlaybookRunErrorResponse],
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

    v0.7.4: Implements queue management, dry_run isolation, and structured error handling.

    dry_run mode guarantees:
    - No database writes (except run record for tracking)
    - No audit_logs entries
    - No external network calls (OTX/VT/etc)
    - DAG validation + mock execution only
    """
    trace_id = str(uuid.uuid4())
    is_dry_run = data.mode == "dry_run"

    try:
        logger.info(
            f"[{trace_id}] Starting playbook run: definition={definition_id}, mode={data.mode}, user={current_user.username}"
        )

        # Permission check
        if data.mode == "apply" and current_user.role != UserRole.ADMIN:
            return PlaybookRunErrorResponse(
                success=False,
                error_code="PERMISSION_DENIED",
                message="Only admins can execute in apply mode",
                details={"user_role": current_user.role, "required_role": "admin"},
                trace_id=trace_id,
            )

        # Get definition
        defn_repo = PlaybookDefinitionRepository(db)
        definition = await defn_repo.get_by_id(definition_id)
        if not definition:
            return PlaybookRunErrorResponse(
                success=False,
                error_code="DEFINITION_NOT_FOUND",
                message=f"Playbook definition not found: {definition_id}",
                details={"definition_id": definition_id},
                trace_id=trace_id,
            )
        if not definition.is_active:
            return PlaybookRunErrorResponse(
                success=False,
                error_code="DEFINITION_INACTIVE",
                message="Definition is not active",
                details={"definition_id": definition_id, "name": definition.name},
                trace_id=trace_id,
            )

        # Validate and compile DAG
        try:
            compiled = await DAGCompiler.validate_and_compile(definition.dag_json, db)
            logger.info(
                f"[{trace_id}] DAG validated: {compiled.get('node_count', 0)} nodes, {compiled.get('edge_count', 0)} edges"
            )
        except DAGValidationError as e:
            return PlaybookRunErrorResponse(
                success=False,
                error_code="DAG_VALIDATION_FAILED",
                message=str(e),
                details={"definition_id": definition_id, "dag_error": str(e)},
                trace_id=trace_id,
            )

        # For dry_run mode, execute mock without database writes
        if is_dry_run:
            return await _execute_dry_run(
                definition=definition,
                compiled_dag=compiled,
                input_context=data.input_context,
                failure_strategy=data.failure_strategy,
                current_user=current_user,
                trace_id=trace_id,
            )

        # Apply mode: Check queue capacity before creating run
        queue_manager = get_run_queue_manager()
        if queue_manager:
            can_start = await queue_manager.can_start_run()
        else:
            can_start = True

        # Create run
        run_repo = PlaybookRunRepository(db)
        run = await run_repo.create(
            playbook_name=definition.name,
            playbook_version=definition.version,
            mode=data.mode,
            input_json=data.input_context,
            created_by_user_id=current_user.id,
            engine_version="v0.7",
            execution_mode="dag",
            definition_id=definition_id,
            failure_strategy=data.failure_strategy,
        )

        # v0.7.4: Queue or start execution
        if not can_start:
            run.status = "queued"
            run.queued_at = datetime.now(UTC)
            await db.commit()
            logger.info(f"[{trace_id}] Run {run.id} queued (capacity reached)")

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
                total_nodes=compiled.get("node_count", 0),
                completed_nodes=0,
                failed_nodes=0,
                running_nodes=0,
                pending_nodes=compiled.get("node_count", 0),
                cancel_requested_at=None,
                can_resume=False,
            )

        # Execute DAG synchronously
        try:
            logger.info(f"[{trace_id}] Starting DAG execution for run {run.id}")
            scheduler = DAGScheduler(
                session=db,
                run_id=run.id,
                compiled_dag=compiled,
                input_context=data.input_context,
                mode=data.mode,
                failure_strategy=data.failure_strategy,
                created_by_user_id=(
                    str(run.created_by_user_id) if run.created_by_user_id else None
                ),
            )
            output = await scheduler.execute()

            final_status = "cancelled" if scheduler.cancelled else "success"
            updates = {
                "status": final_status,
                "output_json": output if not scheduler.cancelled else run.output_json,
            }
            if scheduler.cancelled:
                updates["error_message"] = "Cancelled by user"
            await run_repo.update(run.id, updates)
            run.status = final_status
            logger.info(f"[{trace_id}] Run {run.id} completed with status {final_status}")

        except Exception as e:
            error_trace = traceback.format_exc()
            logger.error(f"[{trace_id}] DAG execution failed: {e}\n{error_trace}")
            await run_repo.update(run.id, {"status": "failed", "error_message": str(e)})

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
            total_nodes=compiled.get("node_count", 0),
            completed_nodes=0,
            failed_nodes=0 if run.status == "success" else 1,
            running_nodes=0,
            pending_nodes=0,
            cancel_requested_at=None,
            can_resume=False,
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Catch-all for any unexpected errors
        error_trace = traceback.format_exc()
        logger.error(f"[{trace_id}] Unexpected error in run_dag_playbook: {e}\n{error_trace}")

        return PlaybookRunErrorResponse(
            success=False,
            error_code="PLAYBOOK_RUN_FAILED",
            message=f"Internal error during playbook execution: {e!s}",
            details={
                "exception": str(e),
                "definition_id": definition_id,
                "mode": data.mode,
            },
            trace_id=trace_id,
        )


async def _execute_dry_run(
    definition: Any,
    compiled_dag: dict[str, Any],
    input_context: dict[str, Any],
    failure_strategy: str,
    current_user: UserModel,
    trace_id: str,
) -> DAGPlaybookRunResponse:
    """Execute playbook in dry_run mode with mock execution.

    dry_run mode guarantees:
    - No database writes (no audit_logs, no node runs)
    - No external network calls
    - DAG validation + mock execution only
    """

    from playbook_engine.v7_dag.registry import get_node_registry

    logger.info(f"[{trace_id}] Executing dry_run mode (no side effects)")

    nodes = compiled_dag.get("nodes", {})
    node_count = len(nodes)
    start_time = datetime.now(UTC)

    # Mock node execution results
    mock_outputs = {}
    completed_nodes = []
    failed_nodes = []

    for node_id, node_def in nodes.items():
        node_type = node_def.get("type", "unknown")
        node_name = node_def.get("name", node_id)

        try:
            # Check if node type is registered
            registry = get_node_registry()
            if registry and node_type in registry.list_plugins():
                # Plugin exists - mock success
                mock_outputs[node_id] = {
                    "status": "success",
                    "node_id": node_id,
                    "node_type": node_type,
                    "message": f"[DRY_RUN] Mock execution for {node_type}",
                    "dry_run": True,
                    "skipped_reason": "dry_run_mode",
                }
                completed_nodes.append(node_id)
            else:
                # Unknown node type - still mock success for dry_run
                mock_outputs[node_id] = {
                    "status": "success",
                    "node_id": node_id,
                    "node_type": node_type,
                    "message": f"[DRY_RUN] Mock execution for unregistered type: {node_type}",
                    "dry_run": True,
                    "skipped_reason": "dry_run_mode",
                }
                completed_nodes.append(node_id)

            logger.info(f"[{trace_id}] [DRY_RUN] Mock executed node {node_id} ({node_type})")

        except Exception as e:
            logger.warning(f"[{trace_id}] [DRY_RUN] Node {node_id} mock failed: {e}")
            mock_outputs[node_id] = {
                "status": "success",  # Always success in dry_run
                "node_id": node_id,
                "error": str(e),
                "dry_run": True,
            }
            completed_nodes.append(node_id)

    end_time = datetime.now(UTC)
    duration_ms = int((end_time - start_time).total_seconds() * 1000)

    return DAGPlaybookRunResponse(
        id=f"dry_run_{trace_id}",  # Virtual ID for dry_run
        playbook_name=definition.name,
        playbook_version=definition.version,
        engine_version="v0.7",
        mode="dry_run",
        status="success",
        failure_strategy=failure_strategy,
        created_by_user_id=current_user.id,
        input_json=input_context,
        output_json={
            "nodes": mock_outputs,
            "dry_run": True,
            "message": "Dry run completed - no actual actions taken",
            "node_count": node_count,
            "duration_ms": duration_ms,
        },
        started_at=start_time,
        finished_at=end_time,
        error_message=None,
        definition_id=definition.id,
        execution_mode="dag",
        total_nodes=node_count,
        completed_nodes=node_count,
        failed_nodes=0,
        running_nodes=0,
        pending_nodes=0,
        cancel_requested_at=None,
        can_resume=False,
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
            node_id=nr.node_id,
            node_name=nr.node_name,
            node_type=nr.node_type,
            status=nr.status,
            started_at=nr.started_at,
            finished_at=nr.finished_at,
            attempt_count=nr.attempt_count,
            last_error=nr.last_error,
            output_json=nr.output_json,
            input_json=nr.input_json,
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

    run_repo = PlaybookRunRepository(db)
    run = await run_repo.get_by_id(run_id)

    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.status not in ("pending", "running"):
        raise HTTPException(status_code=400, detail=f"Cannot cancel run in status: {run.status}")

    from services.playbook.playbook_dag_scheduler import get_running_scheduler

    scheduler = get_running_scheduler(run_id)
    if scheduler:
        await scheduler.cancel(data.reason or "Cancelled by user")
    await run_repo.update(
        run_id,
        {"status": "cancelled", "error_message": data.reason or "Cancelled by user"},
    )

    return PlaybookRunCancelResponse(
        run_id=run_id,
        status="cancelled",
        message="Run cancelled successfully",
    )


# ============ Internal API Endpoints for Playbook Nodes ============

from pydantic import BaseModel


class NormalizeRequest(BaseModel):
    ioc: str
    ioc_type: str = "auto"


class NormalizeResponse(BaseModel):
    status: str
    original_ioc: str
    normalized_ioc: str
    normalized_type: str
    is_valid: bool


@router.post("/internal/normalize", response_model=NormalizeResponse)
async def internal_normalize(
    data: NormalizeRequest,
    current_user: UserModel = Depends(get_current_user),
):
    """Internal API: Normalize IOC input."""
    import re

    ioc = data.ioc.strip().lower()
    ioc_type = data.ioc_type

    # Auto-detect if needed
    if ioc_type == "auto":
        if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", ioc):
            ioc_type = "ip"
        elif ioc.startswith(("http://", "https://")):
            ioc_type = "url"
        elif (
            re.match(r"^[a-f0-9]{32}$", ioc)
            or re.match(r"^[a-f0-9]{40}$", ioc)
            or re.match(r"^[a-f0-9]{64}$", ioc)
        ):
            ioc_type = "hash"
        else:
            ioc_type = "domain"

    # Normalize
    normalized = ioc
    if ioc_type == "url":
        normalized = ioc.rstrip("/").split("#")[0]
    elif ioc_type == "domain":
        if normalized.startswith("www."):
            normalized = normalized[4:]

    is_valid = bool(normalized)

    return NormalizeResponse(
        status="success" if is_valid else "invalid",
        original_ioc=data.ioc,
        normalized_ioc=normalized,
        normalized_type=ioc_type,
        is_valid=is_valid,
    )


class ExtractIOCsRequest(BaseModel):
    otx_result: dict
    case_id: str = ""


class ExtractIOCsResponse(BaseModel):
    status: str
    total_extracted: int
    extracted_iocs: dict
    summary: dict


@router.post("/internal/extract-iocs", response_model=ExtractIOCsResponse)
async def internal_extract_iocs(
    data: ExtractIOCsRequest,
    current_user: UserModel = Depends(get_current_user),
):
    """Internal API: Extract secondary IOCs from OTX result."""
    import re

    ti_result = data.otx_result
    extracted = {"ips": [], "domains": [], "urls": [], "hashes": [], "emails": []}

    if isinstance(ti_result, dict):
        pulses = ti_result.get("matches", [])
        for pulse in pulses:
            text = f"{pulse.get('name', '')} {pulse.get('description', '')}"

            # Extract IPs
            ips = re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", text)
            extracted["ips"].extend(ips)

            # Extract domains
            domains = re.findall(r"\b(?:[a-z0-9](?:[a-z0-9\-]{0,61}[a-z0-9])?\.)+[a-z]{2,}\b", text)
            extracted["domains"].extend(domains)

            # Extract hashes
            hashes = re.findall(
                r"\b[a-fA-F0-9]{32}\b|\b[a-fA-F0-9]{40}\b|\b[a-fA-F0-9]{64}\b", text
            )
            extracted["hashes"].extend(hashes)

    # Deduplicate
    for key in extracted:
        extracted[key] = list(set(extracted[key]))

    total = sum(len(v) for v in extracted.values())

    return ExtractIOCsResponse(
        status="success",
        total_extracted=total,
        extracted_iocs=extracted,
        summary={k: len(v) for k, v in extracted.items()},
    )


class MockBlocklistRequest(BaseModel):
    ioc: str
    ioc_type: str
    case_id: str
    action: str = "block"


class MockBlocklistResponse(BaseModel):
    status: str
    action: str
    ioc: str
    timestamp: str
    message: str


@router.post("/internal/mock-blocklist", response_model=MockBlocklistResponse)
async def internal_mock_blocklist(
    data: MockBlocklistRequest,
    current_user: UserModel = Depends(get_current_user),
):
    """Internal API: Mock blocklist action (for demo)."""
    logger.info(
        f"[MOCK] Blocklist action: {data.action} {data.ioc_type} {data.ioc} for case {data.case_id}"
    )

    return MockBlocklistResponse(
        status="success",
        action=data.action,
        ioc=data.ioc,
        timestamp=datetime.now(datetime.UTC).isoformat(),
        message=f"IOC {data.ioc} has been added to the blocklist (MOCK)",
    )


class GenerateReportRequest(BaseModel):
    case_id: str
    ioc: str
    ioc_type: str
    alert_source: str = "email-gateway"
    severity: str = "medium"
    reporter: str = "soc@company.com"
    otx_result: dict = {}
    secondary_iocs: dict = {}
    action_result: dict = {}
    note: str = ""


class GenerateReportResponse(BaseModel):
    status: str
    report_id: str
    case_id: str
    markdown: str
    report_url: str
    threat_level: str


@router.post("/internal/generate-report", response_model=GenerateReportResponse)
async def internal_generate_report(
    data: GenerateReportRequest,
    current_user: UserModel = Depends(get_current_user),
):
    """Internal API: Generate markdown report."""

    ti_result = data.otx_result if isinstance(data.otx_result, dict) else {}
    threat_score = ti_result.get("threat_score", 0)
    is_malicious = threat_score >= 3
    threat_level = "high" if is_malicious else "low"

    # Generate markdown
    lines = [
        f"# Incident Response Report: {data.case_id}",
        "",
        f"**Generated:** {datetime.now(datetime.UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC",
        "",
        "## Executive Summary",
        "",
        f"{'⚠️ **THREAT CONFIRMED**' if is_malicious else 'ℹ️ **LOW CONFIDENCE**'} - IOC `{data.ioc}`",
        "",
        "## IOC Details",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| **Case ID** | {data.case_id} |",
        f"| **IOC** | `{data.ioc}` |",
        f"| **Type** | {data.ioc_type} |",
        f"| **Source** | {data.alert_source} |",
        f"| **Severity** | {data.severity} |",
        "",
        "## Threat Intelligence",
        "",
        f"- **Threat Score:** {threat_score}/10",
        f"- **OTX Matches:** {ti_result.get('match_count', 0)} pulses",
        "",
        "## Recommendations",
        "",
    ]

    if is_malicious:
        lines.extend(
            [
                "1. ✅ Block the IOC at network perimeter",
                "2. 🔍 Hunt for secondary IOCs",
                "3. 📧 Check for related phishing emails",
            ]
        )
    else:
        lines.extend(
            [
                "1. 👁️ Continue monitoring",
                "2. 📊 Review alert source configuration",
            ]
        )

    if data.note:
        lines.extend(["", "## Notes", "", data.note])

    lines.extend(["", "---", "*Auto-generated by SOC Copilot*"])

    report_id = f"RPT-{data.case_id}-{datetime.now(datetime.UTC).strftime('%Y%m%d%H%M%S')}"

    return GenerateReportResponse(
        status="success",
        report_id=report_id,
        case_id=data.case_id,
        markdown="\n".join(lines),
        report_url=f"/api/reports/{report_id}",
        threat_level=threat_level,
    )


class CaseUpdateRequest(BaseModel):
    case_id: str
    status: str
    reason: str = ""
    playbook_run_id: str = ""
    report_url: str = ""


class CaseUpdateResponse(BaseModel):
    status: str
    case_id: str
    updated_at: str
    message: str


@router.post("/internal/case-update", response_model=CaseUpdateResponse)
async def internal_case_update(
    data: CaseUpdateRequest,
    current_user: UserModel = Depends(get_current_user),
):
    """Internal API: Mock case system callback."""
    logger.info(f"[MOCK] Case update: {data.case_id} -> {data.status}")

    return CaseUpdateResponse(
        status="success",
        case_id=data.case_id,
        updated_at=datetime.now(datetime.UTC).isoformat(),
        message=f"Case {data.case_id} updated to {data.status}",
    )
