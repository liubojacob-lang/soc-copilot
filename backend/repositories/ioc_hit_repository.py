"""IOC Hit repository for database operations."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.ioc_hit import IOCHitDB
from schemas.ioc_hit import IOCHitCreate, IOCSource, IOCType


class IOCHitRepository:
    """Repository for IOC hit CRUD operations."""

    async def create(self, session: AsyncSession, data: IOCHitCreate) -> IOCHitDB:
        """Create a new IOC hit."""
        hit = IOCHitDB(
            id=str(uuid.uuid4()),
            history_id=data.history_id,
            asset_id=data.asset_id,
            ioc_type=(
                data.ioc_type.value
                if isinstance(data.ioc_type, IOCType)
                else data.ioc_type
            ),
            ioc_value=data.ioc_value,
            confidence=data.confidence,
            source=(
                data.source.value if isinstance(data.source, IOCSource) else data.source
            ),
            context_snippet=data.context_snippet,
            notes=data.notes,
        )
        session.add(hit)
        await session.flush()
        return hit

    async def get_by_id(self, session: AsyncSession, hit_id: str) -> IOCHitDB | None:
        """Get IOC hit by ID."""
        result = await session.execute(select(IOCHitDB).where(IOCHitDB.id == hit_id))
        return result.scalar_one_or_none()

    async def list_by_ioc(
        self, session: AsyncSession, ioc_value: str, limit: int = 100
    ) -> list[IOCHitDB]:
        """List IOC hits by IOC value."""
        result = await session.execute(
            select(IOCHitDB)
            .where(IOCHitDB.ioc_value == ioc_value)
            .order_by(IOCHitDB.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_by_asset(
        self, session: AsyncSession, asset_id: str, limit: int = 100
    ) -> list[IOCHitDB]:
        """List IOC hits by asset ID."""
        result = await session.execute(
            select(IOCHitDB)
            .where(IOCHitDB.asset_id == asset_id)
            .order_by(IOCHitDB.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_by_history(
        self, session: AsyncSession, history_id: str, limit: int = 100
    ) -> list[IOCHitDB]:
        """List IOC hits by history ID."""
        result = await session.execute(
            select(IOCHitDB)
            .where(IOCHitDB.history_id == history_id)
            .order_by(IOCHitDB.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_by_iocs(
        self, session: AsyncSession, ioc_values: list[str], limit: int = 100
    ) -> list[IOCHitDB]:
        """List IOC hits by multiple IOC values."""
        result = await session.execute(
            select(IOCHitDB)
            .where(IOCHitDB.ioc_value.in_(ioc_values))
            .order_by(IOCHitDB.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_by_ioc(self, session: AsyncSession, ioc_value: str) -> int:
        """Count IOC hits by IOC value."""
        from sqlalchemy import func

        result = await session.execute(
            select(func.count())
            .select_from(IOCHitDB)
            .where(IOCHitDB.ioc_value == ioc_value)
        )
        return result.scalar() or 0

    async def get_recent_by_iocs(
        self, session: AsyncSession, ioc_values: list[str], limit: int = 20
    ) -> list[IOCHitDB]:
        """Get recent IOC hits for given IOC values."""
        result = await session.execute(
            select(IOCHitDB)
            .where(IOCHitDB.ioc_value.in_(ioc_values))
            .order_by(IOCHitDB.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_recent(
        self, session: AsyncSession, limit: int = 100
    ) -> list[IOCHitDB]:
        """List recent IOC hits."""
        result = await session.execute(
            select(IOCHitDB).order_by(IOCHitDB.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def count_all(self, session: AsyncSession) -> int:
        """Count total IOC hits."""
        from sqlalchemy import func

        result = await session.execute(select(func.count()).select_from(IOCHitDB))
        return result.scalar() or 0
