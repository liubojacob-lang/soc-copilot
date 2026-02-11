"""Playbook API router for query and action generation."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from db.session import get_session
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
    PlaybookRunStepResponse,
    PlaybookResumeRequest,
    PlaybookResumeResponse,
    PlaybookRunWithStepsResponse,
)
from services.playbook_service import PlaybookService
from services.playbook_run_service import PlaybookRunService

logger = get_logger(__name__)

router = APIRouter(prefix="/api/playbook", tags=["playbook"])


@router.post("/queries", response_model=GenerateQueriesResponse)
async def generate_queries(
    request: GenerateQueriesRequest,
    session: AsyncSession = Depends(get_session),
) -> GenerateQueriesResponse:
    """Generate SIEM queries for multiple platforms.

    Args:
        request: Query generation request with IOCs or history_id
        session: Database session

    Returns:
        Generated queries for specified platforms

    Example request:
    ```json
    {
        "module": "analyzer",
        "history_id": "abc-123",
        "platforms": ["splunk", "elastic_kql", "sentinel_kql"],
        "time_ranges": ["last_24h", "last_7d"]
    }
    ```

    Or with direct IOCs:
    ```json
    {
        "module": "analyzer",
        "iocs": {
            "ips": ["1.2.3.4"],
            "domains": ["evil.com"],
            "urls": [],
            "hashes": []
        },
        "platforms": ["splunk"],
        "time_ranges": ["last_24h"]
    }
    ```
    """
    service = PlaybookService(session)
    return await service.generate_queries(request)


@router.post("/actions", response_model=GenerateActionsResponse)
async def generate_actions(
    request: GenerateActionsRequest,
    session: AsyncSession = Depends(get_session),
) -> GenerateActionsResponse:
    """Generate remediation actions based on history record.

    Args:
        request: Actions generation request
        session: Database session

    Returns:
        Generated remediation actions with steps, verification, and rollback

    Example request:
    ```json
    {
        "history_id": "abc-123",
        "policy": "safe",
        "include_verification_steps": true
    }
    ```
    """
    service = PlaybookService(session)
    return await service.generate_actions(request)


@router.get("/history", response_model=PlaybookHistoryResponse)
async def get_playbook_history(
    history_id: str | None = Query(None, description="Filter by source history ID"),
    limit: int = Query(50, ge=1, le=200, description="Maximum records to return"),
    session: AsyncSession = Depends(get_session),
) -> PlaybookHistoryResponse:
    """Get playbook generation history.

    Args:
        history_id: Optional filter by source history record ID
        limit: Maximum number of records to return
        session: Database session

    Returns:
        Playbook history records

    Example:
        GET /api/playbook/history?history_id=abc-123&limit=20
    """
    service = PlaybookService(session)
    return await service.get_history(history_id=history_id, limit=limit)


@router.get("/health")
async def health() -> dict[str, str]:
    """Playbook module health check."""
    return {"status": "ok", "module": "playbook", "version": "0.6.1"}


# ============================================
# Playbook Run Execution Endpoints (v0.6.1)
# ============================================

@router.post("/run", response_model=PlaybookRunResponse)
async def create_playbook_run(
    request: PlaybookRunCreateRequest,
    session: AsyncSession = Depends(get_session),
) -> PlaybookRunResponse:
    """Create and start a new playbook run.

    Args:
        request: Run creation request
        session: Database session

    Returns:
        Created playbook run details

    Example request:
    ```json
    {
        "playbook_name": "phishing_triage",
        "mode": "dry_run",
        "input_json": {
            "alert_data": {
                "subject": "Urgent: Verify your account",
                "sender": "suspicious@example.com"
            },
            "source_text": "Click here to verify..."
        }
    }
    ```
    """
    service = PlaybookRunService(session)
    return await service.create_run(request)


@router.get("/runs", response_model=PlaybookRunListResponse)
async def list_playbook_runs(
    playbook_name: str | None = Query(None, description="Filter by playbook name"),
    status: str | None = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    session: AsyncSession = Depends(get_session),
) -> PlaybookRunListResponse:
    """List playbook runs with pagination.

    Args:
        playbook_name: Optional filter by playbook name
        status: Optional filter by status
        page: Page number (1-indexed)
        page_size: Items per page
        session: Database session

    Returns:
        Paginated list of playbook runs

    Example:
        GET /api/playbook/runs?playbook_name=phishing_triage&status=success&page=1&page_size=20
    """
    service = PlaybookRunService(session)
    return await service.list_runs(
        playbook_name=playbook_name,
        status=status,
        page=page,
        page_size=page_size,
    )


@router.get("/runs/{run_id}", response_model=PlaybookRunResponse)
async def get_playbook_run(
    run_id: str,
    session: AsyncSession = Depends(get_session),
) -> PlaybookRunResponse:
    """Get a playbook run by ID.

    Args:
        run_id: Run ID
        session: Database session

    Returns:
        Playbook run details

    Raises:
        HTTPException: If run not found

    Example:
        GET /api/playbook/runs/abc-123-def
    """
    service = PlaybookRunService(session)
    run = await service.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    return run


@router.get("/runs/{run_id}/steps", response_model=PlaybookRunWithStepsResponse)
async def get_playbook_run_steps(
    run_id: str,
    session: AsyncSession = Depends(get_session),
) -> PlaybookRunWithStepsResponse:
    """Get a playbook run with all steps.

    Args:
        run_id: Run ID
        session: Database session

    Returns:
        Playbook run with step details

    Raises:
        HTTPException: If run not found

    Example:
        GET /api/playbook/runs/abc-123-def/steps
    """
    service = PlaybookRunService(session)
    result = await service.get_run_with_steps(run_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    return result


@router.post("/runs/{run_id}/resume", response_model=PlaybookResumeResponse)
async def resume_playbook_run(
    run_id: str,
    request: PlaybookResumeRequest,
    session: AsyncSession = Depends(get_session),
) -> PlaybookResumeResponse:
    """Resume a failed or partial playbook run.

    Args:
        run_id: Run ID to resume
        request: Resume request parameters
        session: Database session

    Returns:
        Updated run status

    Raises:
        HTTPException: If run cannot be resumed

    Example request:
    ```json
    {
        "from_step_index": 2,
        "run_mode": "apply"
    }
    ```
    """
    service = PlaybookRunService(session)
    try:
        return await service.resume_run(run_id, request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/playbooks")
async def list_available_playbooks(
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    """Get list of available playbooks.

    Args:
        session: Database session

    Returns:
        Dictionary of available playbooks with metadata

    Example:
        GET /api/playbook/playbooks
    """
    service = PlaybookRunService(session)
    return await service.get_available_playbooks()
