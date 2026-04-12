"""Assets router for asset management API."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from db.session import get_session
from dependencies.auth import get_current_user
from models.user import UserModel
from schemas.asset import (
    AssetCreate,
    AssetImportRequest,
    AssetImportResponse,
    AssetListResponse,
    AssetResponse,
    AssetUpdate,
)
from services.asset_service import AssetService

router = APIRouter(prefix="/api/assets", tags=["assets"])
logger = get_logger(__name__)


@router.post("", response_model=AssetResponse, status_code=201)
async def create_asset(
    data: AssetCreate,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> AssetResponse:
    """Create a new asset."""
    try:
        service = AssetService(session)
        return await service.create(data)
    except ValueError as e:
        logger.warning(f"Asset creation failed: {e!s}")
        raise HTTPException(status_code=400, detail="Bad request")


@router.get("", response_model=AssetListResponse)
async def list_assets(
    query: str | None = Query(None, description="Search query"),
    limit: int = Query(50, ge=1, le=500, description="Maximum results"),
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> AssetListResponse:
    """List assets with optional search."""
    service = AssetService(session)
    assets, total = await service.list(query=query, limit=limit)
    return AssetListResponse(items=assets, total=total)


@router.get("/{asset_id}", response_model=AssetResponse)
async def get_asset(
    asset_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> AssetResponse:
    """Get asset by ID."""
    service = AssetService(session)
    asset = await service.get_by_id(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.patch("/{asset_id}", response_model=AssetResponse)
async def update_asset(
    asset_id: str,
    data: AssetUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> AssetResponse:
    """Update an asset."""
    try:
        service = AssetService(session)
        return await service.update(asset_id, data)
    except ValueError as e:
        logger.warning(f"Asset update failed: {e!s}")
        raise HTTPException(
            status_code=400 if "not found" in str(e) else 404, detail="Bad request"
        )


@router.delete("/{asset_id}", status_code=204)
async def delete_asset(
    asset_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> None:
    """Delete an asset."""
    try:
        service = AssetService(session)
        await service.delete(asset_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Not found")


@router.post("/import", response_model=AssetImportResponse)
async def import_assets(
    data: AssetImportRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> AssetImportResponse:
    """Import assets in bulk.

    Expects JSON array of assets:
    ```json
    {
      "assets": [
        {"hostname": "web-prod-01", "ip": "10.0.1.10", "criticality": "high"},
        {"hostname": "db-prod-01", "ip": "10.0.2.20", "criticality": "critical"}
      ]
    }
    ```
    """
    service = AssetService(session)
    return await service.import_assets(data)
