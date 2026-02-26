"""Threat Intel Cache repository for database operations."""

import json
from datetime import datetime, timedelta, UTC
from typing import Optional, List
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models.threat_intel_cache import ThreatIntelCacheDB
from core.config import settings


class ThreatIntelRepository:
    """Repository for threat intelligence cache CRUD operations."""

    async def get_by_ioc(
        self,
        session: AsyncSession,
        provider: str,
        ioc_type: str,
        ioc_value: str,
    ) -> Optional[ThreatIntelCacheDB]:
        """Get cached threat intel by provider, IOC type and value.

        Args:
            session: Database session
            provider: Provider name (e.g., "otx")
            ioc_type: IOC type (ip/domain/url/hash)
            ioc_value: IOC value

        Returns:
            Cached threat intel or None if not found or expired
        """
        result = await session.execute(
            select(ThreatIntelCacheDB).where(
                and_(
                    ThreatIntelCacheDB.provider == provider,
                    ThreatIntelCacheDB.ioc_type == ioc_type,
                    ThreatIntelCacheDB.ioc_value == ioc_value,
                    ThreatIntelCacheDB.expires_at > datetime.now(UTC),
                )
            )
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        session: AsyncSession,
        provider: str,
        ioc_type: str,
        ioc_value: str,
        status: str,
        response_json: dict,
        score: int = None,
        tags: List[str] = None,
        pulse_count: int = None,
        last_seen: datetime = None,
        error_reason: str = None,
    ) -> ThreatIntelCacheDB:
        """Create a new threat intel cache entry.

        Args:
            session: Database session
            provider: Provider name
            ioc_type: IOC type
            ioc_value: IOC value
            status: Cache status (ok/not_found/error)
            response_json: Full response as dict
            score: Threat score 0-100
            tags: List of tags
            pulse_count: Number of pulses/reports
            last_seen: Last seen datetime
            error_reason: Error message if status is error

        Returns:
            Created cache entry
        """
        ttl_hours = settings.ti_cache_ttl_hours
        expires_at = datetime.now(UTC) + timedelta(hours=ttl_hours)

        cache_entry = ThreatIntelCacheDB(
            provider=provider,
            ioc_type=ioc_type,
            ioc_value=ioc_value,
            status=status,
            response_json=json.dumps(response_json),
            score=score,
            tags=json.dumps(tags) if tags else None,
            pulse_count=pulse_count,
            last_seen=last_seen,
            expires_at=expires_at,
            error_reason=error_reason,
        )
        session.add(cache_entry)
        await session.flush()
        return cache_entry

    async def update(
        self,
        session: AsyncSession,
        cache_entry: ThreatIntelCacheDB,
        status: str,
        response_json: dict,
        score: int = None,
        tags: List[str] = None,
        pulse_count: int = None,
        last_seen: datetime = None,
        error_reason: str = None,
    ) -> ThreatIntelCacheDB:
        """Update existing threat intel cache entry.

        Args:
            session: Database session
            cache_entry: Existing cache entry
            status: Cache status
            response_json: Full response as dict
            score: Threat score
            tags: List of tags
            pulse_count: Number of pulses
            last_seen: Last seen datetime
            error_reason: Error message

        Returns:
            Updated cache entry
        """
        ttl_hours = settings.ti_cache_ttl_hours
        expires_at = datetime.now(UTC) + timedelta(hours=ttl_hours)

        cache_entry.status = status
        cache_entry.response_json = json.dumps(response_json)
        cache_entry.score = score
        cache_entry.tags = json.dumps(tags) if tags else None
        cache_entry.pulse_count = pulse_count
        cache_entry.last_seen = last_seen
        cache_entry.expires_at = expires_at
        cache_entry.updated_at = datetime.now(UTC)
        cache_entry.error_reason = error_reason

        await session.flush()
        return cache_entry

    async def delete_expired(self, session: AsyncSession) -> int:
        """Delete expired cache entries.

        Args:
            session: Database session

        Returns:
            Number of deleted entries
        """
        result = await session.execute(
            select(ThreatIntelCacheDB).where(
                ThreatIntelCacheDB.expires_at < datetime.now(UTC)
            )
        )
        expired = result.scalars().all()
        count = len(expired)
        for entry in expired:
            await session.delete(entry)
        return count

    async def get_stats(self, session: AsyncSession) -> dict:
        """Get cache statistics.

        Args:
            session: Database session

        Returns:
            Dictionary with cache stats
        """
        from sqlalchemy import func

        total_result = await session.execute(
            select(func.count()).select_from(ThreatIntelCacheDB)
        )
        total = total_result.scalar() or 0

        active_result = await session.execute(
            select(func.count()).select_from(ThreatIntelCacheDB).where(
                ThreatIntelCacheDB.expires_at > datetime.now(UTC)
            )
        )
        active = active_result.scalar() or 0

        by_provider = {}
        for provider in ["otx"]:
            result = await session.execute(
                select(func.count())
                .select_from(ThreatIntelCacheDB)
                .where(
                    and_(
                        ThreatIntelCacheDB.provider == provider,
                        ThreatIntelCacheDB.expires_at > datetime.now(UTC),
                    )
                )
            )
            by_provider[provider] = result.scalar() or 0

        return {
            "total": total,
            "active": active,
            "expired": total - active,
            "by_provider": by_provider,
        }

    async def delete_by_ioc(
        self,
        session: AsyncSession,
        provider: str,
        ioc_type: str,
        ioc_value: str,
    ) -> int:
        """Delete cache entry by IOC identifier.

        v0.8.3: Added for TI Cache Refresh API.

        Args:
            session: Database session
            provider: Provider name (e.g., "otx")
            ioc_type: IOC type (ip/domain/url/hash)
            ioc_value: IOC value

        Returns:
            Number of deleted entries (0 or 1)
        """
        from sqlalchemy import delete

        result = await session.execute(
            delete(ThreatIntelCacheDB).where(
                and_(
                    ThreatIntelCacheDB.provider == provider,
                    ThreatIntelCacheDB.ioc_type == ioc_type,
                    ThreatIntelCacheDB.ioc_value == ioc_value,
                )
            )
        )
        return result.rowcount
