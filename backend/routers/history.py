"""History API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from db.session import AsyncSession, get_session
from dependencies import get_current_user, require_admin
from models.user import UserModel
from schemas.history import HistoryListResponse, HistoryResponse
from services.history_service import HistoryService

router = APIRouter(prefix="/api/v1/history", tags=["history"])


@router.get("", response_model=HistoryListResponse)
async def list_history(
    module: Annotated[str | None, Query(description="Filter by module")] = None,
    query: Annotated[str | None, Query(description="Search query")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> HistoryListResponse:
    """List history records with optional filters.

    Args:
        module: Filter by module (analyzer, report, timeline)
        query: Search query for IOCs, text, etc.
        limit: Maximum records to return (1-100)
        session: Database session

    Returns:
        List of history records
    """
    service = HistoryService(session)
    return await service.list_history(module=module, query=query, limit=limit)


@router.get("/{history_id}", response_model=HistoryResponse)
async def get_history(
    history_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> HistoryResponse:
    """Get a specific history record by ID.

    Args:
        history_id: History record ID
        session: Database session

    Returns:
        History record

    Raises:
        HTTPException: If record not found
    """
    service = HistoryService(session)
    result = await service.get_history(history_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"History record {history_id} not found",
        )
    return result


@router.delete("/{history_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_history(
    history_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(require_admin),
) -> None:
    """Delete a specific history record by ID.

    Args:
        history_id: History record ID
        session: Database session

    Raises:
        HTTPException: If record not found
    """
    service = HistoryService(session)
    deleted = await service.delete_history(history_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"History record {history_id} not found",
        )


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_all_history(
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(require_admin),
) -> None:
    """Delete all history records.

    Args:
        session: Database session
    """
    service = HistoryService(session)
    await service.delete_all_history()
