"""Query and action generation endpoints.

This module contains endpoints for:
- Generating SIEM queries for multiple platforms
- Generating remediation actions
- Getting playbook history
- Health check
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from db.session import get_session
from dependencies.auth import get_current_user
from models.user import UserModel
from repositories.audit_repository import AuditRepository
from schemas.playbook import (
    GenerateActionsRequest,
    GenerateActionsResponse,
    GenerateQueriesRequest,
    GenerateQueriesResponse,
    PlaybookHistoryResponse,
)
from services.playbook.playbook_service import PlaybookService

logger = get_logger(__name__)

router = APIRouter(tags=["playbook-queries"])


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
        path="/api/v1/playbook/queries",
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
        path="/api/v1/playbook/actions",
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
