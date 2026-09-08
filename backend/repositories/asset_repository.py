"""Asset repository for database operations."""

import builtins
import json

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.asset import AssetDB
from schemas.asset import AssetCreate, AssetUpdate, Criticality


class AssetRepository:
    """Repository for asset CRUD operations."""

    async def create(self, session: AsyncSession, data: AssetCreate) -> AssetDB:
        """Create a new asset."""
        import uuid

        asset = AssetDB(
            id=str(uuid.uuid4()),
            hostname=data.hostname,
            ip=data.ip,
            owner=data.owner,
            business=data.business,
            criticality=(
                data.criticality.value
                if isinstance(data.criticality, Criticality)
                else data.criticality
            ),
            tags=json.dumps(data.tags) if data.tags else None,
            notes=data.notes,
            is_active=data.is_active,
        )
        session.add(asset)
        await session.flush()
        return asset

    async def get_by_id(self, session: AsyncSession, asset_id: str) -> AssetDB | None:
        """Get asset by ID."""
        result = await session.execute(select(AssetDB).where(AssetDB.id == asset_id))
        return result.scalar_one_or_none()

    async def get_by_hostname(
        self, session: AsyncSession, hostname: str
    ) -> AssetDB | None:
        """Get asset by hostname (case-insensitive)."""
        result = await session.execute(
            select(AssetDB).where(AssetDB.hostname == hostname)
        )
        return result.scalar_one_or_none()

    async def get_by_ip(self, session: AsyncSession, ip: str) -> AssetDB | None:
        """Get asset by IP."""
        result = await session.execute(select(AssetDB).where(AssetDB.ip == ip))
        return result.scalar_one_or_none()

    async def list(
        self,
        session: AsyncSession,
        query: str | None = None,
        limit: int = 50,
    ) -> list[AssetDB]:
        """List assets with optional search."""
        stmt = select(AssetDB)

        if query:
            search_pattern = f"%{query}%"
            stmt = stmt.where(
                or_(
                    AssetDB.hostname.ilike(search_pattern),
                    AssetDB.ip.ilike(search_pattern),
                    AssetDB.owner.ilike(search_pattern),
                    AssetDB.business.ilike(search_pattern),
                    AssetDB.tags.ilike(search_pattern),
                )
            )

        stmt = stmt.limit(limit)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def update(
        self, session: AsyncSession, asset: AssetDB, data: AssetUpdate
    ) -> AssetDB:
        """Update an asset."""
        if data.hostname is not None:
            asset.hostname = data.hostname
        if data.ip is not None:
            asset.ip = data.ip
        if data.owner is not None:
            asset.owner = data.owner
        if data.business is not None:
            asset.business = data.business
        if data.criticality is not None:
            asset.criticality = (
                data.criticality.value
                if isinstance(data.criticality, Criticality)
                else data.criticality
            )
        if data.tags is not None:
            asset.tags = json.dumps(data.tags)
        if data.notes is not None:
            asset.notes = data.notes
        if data.is_active is not None:
            asset.is_active = data.is_active

        await session.flush()
        return asset

    async def delete(self, session: AsyncSession, asset: AssetDB) -> None:
        """Delete an asset."""
        await session.delete(asset)

    async def get_by_ips(
        self, session: AsyncSession, ips: builtins.list[str]
    ) -> builtins.list[AssetDB]:
        """Get assets by list of IPs."""
        result = await session.execute(select(AssetDB).where(AssetDB.ip.in_(ips)))
        return list(result.scalars().all())

    async def get_by_hostnames(
        self, session: AsyncSession, hostnames: builtins.list[str]
    ) -> builtins.list[AssetDB]:
        """Get assets by list of hostnames."""
        result = await session.execute(
            select(AssetDB).where(AssetDB.hostname.in_(hostnames))
        )
        return list(result.scalars().all())

    async def count(self, session: AsyncSession) -> int:
        """Count total assets."""
        from sqlalchemy import func

        result = await session.execute(select(func.count()).select_from(AssetDB))
        return result.scalar() or 0
