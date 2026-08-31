"""Asset service for business logic."""

import builtins
import json

from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from repositories.asset_repository import AssetRepository
from schemas.asset import (
    AssetCreate,
    AssetImportRequest,
    AssetImportResponse,
    AssetResponse,
    AssetUpdate,
)

logger = get_logger(__name__)


class AssetService:
    """Service for asset management."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize asset service.

        Args:
            session: Database session
        """
        self.session = session
        self.repository = AssetRepository()

    async def create(self, data: AssetCreate) -> AssetResponse:
        """Create a new asset.

        Args:
            data: Asset creation data

        Returns:
            Created asset

        Raises:
            ValueError: If hostname and IP are both empty
            ValueError: If hostname or IP already exists
        """
        if not data.hostname and not data.ip:
            raise ValueError("At least one of hostname or ip must be provided")

        # Check for duplicate hostname
        if data.hostname:
            existing = await self.repository.get_by_hostname(
                self.session, data.hostname
            )
            if existing:
                raise ValueError(
                    f"Asset with hostname '{data.hostname}' already exists"
                )

        # Check for duplicate IP
        if data.ip:
            existing = await self.repository.get_by_ip(self.session, data.ip)
            if existing:
                raise ValueError(f"Asset with IP '{data.ip}' already exists")

        asset = await self.repository.create(self.session, data)
        logger.info(f"Created asset: {asset.id}")
        return self._to_response(asset)

    async def get_by_id(self, asset_id: str) -> AssetResponse | None:
        """Get asset by ID.

        Args:
            asset_id: Asset ID

        Returns:
            Asset response or None
        """
        asset = await self.repository.get_by_id(self.session, asset_id)
        if not asset:
            return None
        return self._to_response(asset)

    async def list(
        self, query: str | None = None, limit: int = 50
    ) -> tuple[list[AssetResponse], int]:
        """List assets with optional search.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            Tuple of (assets, total count)
        """
        assets = await self.repository.list(self.session, query=query, limit=limit)
        total = await self.repository.count(self.session)
        return [self._to_response(a) for a in assets], total

    async def update(self, asset_id: str, data: AssetUpdate) -> AssetResponse:
        """Update an asset.

        Args:
            asset_id: Asset ID
            data: Update data

        Returns:
            Updated asset

        Raises:
            ValueError: If asset not found
        """
        asset = await self.repository.get_by_id(self.session, asset_id)
        if not asset:
            raise ValueError(f"Asset not found: {asset_id}")

        # Check for duplicate hostname
        if data.hostname and data.hostname != asset.hostname:
            existing = await self.repository.get_by_hostname(
                self.session, data.hostname
            )
            if existing and existing.id != asset_id:
                raise ValueError(
                    f"Asset with hostname '{data.hostname}' already exists"
                )

        # Check for duplicate IP
        if data.ip and data.ip != asset.ip:
            existing = await self.repository.get_by_ip(self.session, data.ip)
            if existing and existing.id != asset_id:
                raise ValueError(f"Asset with IP '{data.ip}' already exists")

        updated = await self.repository.update(self.session, asset, data)
        logger.info(f"Updated asset: {asset_id}")
        return self._to_response(updated)

    async def delete(self, asset_id: str) -> None:
        """Delete an asset.

        Args:
            asset_id: Asset ID

        Raises:
            ValueError: If asset not found
        """
        asset = await self.repository.get_by_id(self.session, asset_id)
        if not asset:
            raise ValueError(f"Asset not found: {asset_id}")

        await self.repository.delete(self.session, asset)
        logger.info(f"Deleted asset: {asset_id}")

    async def import_assets(self, data: AssetImportRequest) -> AssetImportResponse:
        """Import assets in bulk.

        Args:
            data: Import request with list of assets

        Returns:
            Import result with counts and errors
        """
        imported = 0
        failed = 0
        errors = []

        for asset_data in data.assets:
            try:
                await self.create(asset_data)
                imported += 1
            except ValueError as e:
                failed += 1
                errors.append(f"{asset_data.hostname or asset_data.ip}: {e!s}")
            except Exception as e:
                failed += 1
                errors.append(
                    f"{asset_data.hostname or asset_data.ip}: Unexpected error: {e!s}"
                )

        logger.info(f"Asset import complete: {imported} imported, {failed} failed")
        return AssetImportResponse(imported=imported, failed=failed, errors=errors)

    async def get_by_ips(self, ips: builtins.list[str]) -> builtins.list[AssetResponse]:
        """Get assets by list of IPs.

        Args:
            ips: List of IP addresses

        Returns:
            List of assets
        """
        assets = await self.repository.get_by_ips(self.session, ips)
        return [self._to_response(a) for a in assets]

    async def get_by_hostnames(
        self, hostnames: builtins.list[str]
    ) -> builtins.list[AssetResponse]:
        """Get assets by list of hostnames.

        Args:
            hostnames: List of hostnames

        Returns:
            List of assets
        """
        assets = await self.repository.get_by_hostnames(self.session, hostnames)
        return [self._to_response(a) for a in assets]

    def _to_response(self, asset) -> AssetResponse:
        """Convert database model to response schema.

        Args:
            asset: Asset database model

        Returns:
            Asset response
        """
        return AssetResponse(
            id=asset.id,
            hostname=asset.hostname,
            ip=asset.ip,
            owner=asset.owner,
            business=asset.business,
            criticality=asset.criticality,
            tags=json.loads(asset.tags) if asset.tags else [],
            notes=asset.notes,
            is_active=asset.is_active,
            created_at=asset.created_at,
            updated_at=asset.updated_at,
        )
