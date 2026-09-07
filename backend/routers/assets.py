"""Assets router for asset management API."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from db.session import get_session
from dependencies.auth import (
    get_current_user,
    require_admin,
    require_analyst_or_admin,
)
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

router = APIRouter(prefix="/api/v1/assets", tags=["assets"])
logger = get_logger(__name__)


@router.post("", response_model=AssetResponse, status_code=201)
async def create_asset(
    data: AssetCreate,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(require_analyst_or_admin),
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
    current_user: UserModel = Depends(require_analyst_or_admin),
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
    current_user: UserModel = Depends(require_admin),
) -> None:
    """Delete an asset (admin only)."""
    try:
        service = AssetService(session)
        await service.delete(asset_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Not found")


@router.post("/discover", status_code=200)
async def discover_assets(
    targets: str | None = Query(
        None, description="IP ranges to scan (comma-separated)"
    ),
    provider: str = Query(
        "network", description="Discovery provider: network, aws, azure, gcp, all"
    ),
    ports: str | None = Query(
        None, description="Port specification for nmap (e.g. 1-1024)"
    ),
    session: AsyncSession = Depends(get_session),
    # Network/cloud discovery has intrusive side effects; auditors are read-only
    current_user: UserModel = Depends(require_analyst_or_admin),
):
    """
    Discover assets via network scan or cloud API.

    Supports:
    - network: NMAP scan of IP ranges
    - aws/azure/gcp: Cloud API stub discovery
    - all: Combined network + cloud discovery

    Discovered hosts are automatically registered as assets (skip existing).
    """
    from services.asset_discovery_service import AssetDiscoveryService

    try:
        service = AssetDiscoveryService(session=session)

        target_list = None
        if targets:
            target_list = [t.strip() for t in targets.split(",") if t.strip()]

        if provider == "all":
            result = await service.discover_all(
                network_targets=target_list,
                cloud_providers=["aws", "azure", "gcp"],
            )
        elif provider in ("aws", "azure", "gcp"):
            result = await service.discover_cloud(provider)
        else:
            result = await service.discover_network(
                targets=target_list, ports=ports, fast_mode=True
            )

        return {
            "status": "completed",
            "hosts_found": len(result.hosts),
            "new_assets": result.new_assets,
            "skipped_assets": result.skipped_assets,
            "scanned_targets": result.scanned_count,
            "scan_duration_ms": result.scan_duration_ms,
            "errors": result.errors,
            "discovered": [
                {
                    "hostname": h.hostname,
                    "ip": h.ip,
                    "source": h.source,
                    "open_ports": h.open_ports,
                    "services": h.services,
                    "os": h.os,
                    "status": h.status,
                }
                for h in result.hosts
            ],
        }
    except Exception as e:
        logger.error(f"Asset discovery failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Asset discovery failed: {e!s}",
        )


@router.get("/discover/preview", status_code=200)
async def preview_discovery(
    targets: str = Query(default="192.168.1.0/24", description="IP range to preview"),
    session: AsyncSession = Depends(get_session),
    # Preview performs a real network scan; auditors are read-only
    current_user: UserModel = Depends(require_analyst_or_admin),
):
    """
    Preview what a discovery scan would find without registering assets.

    Useful for validating scan configuration before committing.
    """
    from services.asset_discovery_service import AssetDiscoveryService

    try:
        service = AssetDiscoveryService(session=session)
        target_list = [t.strip() for t in targets.split(",") if t.strip()]
        result = await service.discover_network(targets=target_list, fast_mode=True)
        return {
            "targets": target_list,
            "hosts_found": len(result.hosts),
            "scanned_count": result.scanned_count,
            "scan_duration_ms": result.scan_duration_ms,
            "hosts": [
                {
                    "hostname": h.hostname,
                    "ip": h.ip,
                    "os": h.os,
                    "open_ports": h.open_ports,
                    "services": h.services,
                }
                for h in result.hosts
            ],
            "errors": result.errors,
        }
    except Exception as e:
        logger.error(f"Discovery preview failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Discovery preview failed: {e!s}",
        )


@router.post("/import", response_model=AssetImportResponse)
async def import_assets(
    data: AssetImportRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(require_analyst_or_admin),
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
