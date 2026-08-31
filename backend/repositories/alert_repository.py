"""
Alert Repository

Provides data-access methods for SecurityAlert CRUD and statistics.
Inherits from BaseRepository for standard ops and adds alert-specific queries.
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from models.security_alert import SecurityAlert
from repositories.base import BaseRepository
from schemas.common import PaginationParams

logger = get_logger(__name__)


class AlertRepository(BaseRepository[SecurityAlert]):
    """
    Repository for SecurityAlert CRUD and query operations.

    Extends BaseRepository with alert-specific listing, filtering, and statistics.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session=session, model=SecurityAlert)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def get_by_id(self, alert_id: int) -> SecurityAlert | None:
        """Get an alert by its integer primary key."""
        result = await self.session.execute(
            select(SecurityAlert).where(SecurityAlert.id == alert_id)
        )
        return result.scalar_one_or_none()

    async def list_alerts(
        self,
        filters: dict[str, Any] | None = None,
        search: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        pagination: PaginationParams | None = None,
    ) -> tuple[list[SecurityAlert], int]:
        """
        List alerts with optional full-text search, multi-field filtering,
        time-range filtering, ordering, and pagination.

        Returns a tuple of (alerts, total_count).
        """
        query = select(SecurityAlert)

        # --- exact-match filters ---
        if filters:
            for field_name, value in filters.items():
                if value is not None:
                    col = getattr(SecurityAlert, field_name)
                    query = query.where(col == value)

        # --- full-text search across title, description, source_ip, and full_log ---
        if search and search.strip():
            pattern = f"%{search.strip()}%"
            query = query.where(
                or_(
                    SecurityAlert.title.ilike(pattern),
                    SecurityAlert.description.ilike(pattern),
                    SecurityAlert.source_ip.ilike(pattern),
                    SecurityAlert.destination_ip.ilike(pattern),
                    SecurityAlert.external_event_id.ilike(pattern),
                    SecurityAlert.agent_name.ilike(pattern),
                )
            )

        # --- time-range filter ---
        if created_from is not None:
            query = query.where(SecurityAlert.created_at >= created_from)
        if created_to is not None:
            query = query.where(SecurityAlert.created_at <= created_to)

        # --- count *before* pagination ---
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # --- ordering ---
        if pagination and pagination.sort_by:
            sort_col = getattr(SecurityAlert, pagination.sort_by, None)
            if sort_col is not None:
                query = query.order_by(
                    sort_col.desc()
                    if pagination.sort_order == "desc"
                    else sort_col.asc()
                )
            else:
                query = query.order_by(SecurityAlert.created_at.desc())
        else:
            query = query.order_by(SecurityAlert.created_at.desc())

        # --- pagination ---
        if pagination:
            query = query.limit(pagination.limit).offset(pagination.offset)

        result = await self.session.execute(query)
        return list(result.scalars().all()), total

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    async def create_alert(self, **kwargs) -> SecurityAlert:
        """Create a new SecurityAlert and flush to obtain the id."""
        alert = SecurityAlert(**kwargs)
        self.session.add(alert)
        await self.session.flush()
        await self.session.refresh(alert)
        return alert

    async def update_alert(self, alert_id: int, **kwargs) -> SecurityAlert | None:
        """Update an existing alert.  Returns the refreshed alert or None."""
        alert = await self.get_by_id(alert_id)
        if alert is None:
            return None

        for field_name, value in kwargs.items():
            if value is not None and hasattr(alert, field_name):
                setattr(alert, field_name, value)

        await self.session.flush()
        await self.session.refresh(alert)
        return alert

    async def delete_alert(self, alert_id: int) -> bool:
        """Permanently delete an alert by id."""
        alert = await self.get_by_id(alert_id)
        if alert is None:
            return False
        await self.session.delete(alert)
        await self.session.flush()
        return True

    async def batch_update_status(
        self,
        alert_ids: list[int],
        new_status: str,
        resolved_by: str | None = None,
        resolution_note: str | None = None,
        updated_at: datetime | None = None,
    ) -> int:
        """
        Batch-update the status for a set of alerts using a bulk UPDATE statement.
        Returns the number of affected rows.
        """
        values: dict[str, Any] = {"status": new_status}
        if updated_at is not None:
            values["updated_at"] = updated_at
        if resolved_by is not None:
            values["resolved_by"] = resolved_by
        if resolution_note is not None:
            values["resolution_note"] = resolution_note
        # auto-set resolved_at when moving to a terminal state
        if new_status in ("resolved", "false_positive"):
            values["resolved_at"] = datetime.now(UTC)

        stmt = (
            update(SecurityAlert)
            .where(SecurityAlert.id.in_(alert_ids))
            .values(**values)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    async def get_alert_stats(self, tenant_id: str | None = None) -> dict[str, Any]:
        """
        Return aggregate statistics:
        - total count
        - by_status / by_severity / by_source
        - last 24h / 7d / 30d counts
        """
        now = datetime.now(UTC)
        base = select(SecurityAlert)

        if tenant_id:
            base = base.where(SecurityAlert.tenant_id == tenant_id)

        # Total
        total_q = select(func.count()).select_from(base.subquery())
        total = (await self.session.execute(total_q)).scalar() or 0

        async def _grouped(column) -> dict[str, int]:
            q = select(column, func.count(SecurityAlert.id)).select_from(SecurityAlert)
            if tenant_id:
                q = q.where(SecurityAlert.tenant_id == tenant_id)
            q = q.group_by(column)
            rows = (await self.session.execute(q)).all()
            return {row[0] or "unknown": row[1] for row in rows}

        by_status = await _grouped(SecurityAlert.status)
        by_severity = await _grouped(SecurityAlert.severity)
        by_source = await _grouped(SecurityAlert.source)

        async def _time_count(hours: int) -> int:
            q = (
                select(func.count())
                .select_from(SecurityAlert)
                .where(
                    SecurityAlert.created_at
                    >= now - func.timedelta(seconds=hours * 3600)
                )
                if hasattr(func, "timedelta")
                else select(func.count()).select_from(
                    base.where(
                        SecurityAlert.created_at
                        >= now.replace(hour=0, minute=0, second=0, microsecond=0)
                    )
                )
            )
            return (await self.session.execute(q)).scalar() or 0

        # Simpler time-based queries using Python datetime arithmetic
        def _time_count_sync(hours: int) -> int:
            """Count alerts since a given number of hours ago."""

            return hours

        # Use raw datetime arithmetic (works across dialects)
        async def _count_since(hours: int) -> int:
            cutoff = now - __import__("datetime").timedelta(hours=hours)
            q = (
                select(func.count())
                .select_from(SecurityAlert)
                .where(SecurityAlert.created_at >= cutoff)
            )
            if tenant_id:
                q = q.where(SecurityAlert.tenant_id == tenant_id)
            return (await self.session.execute(q)).scalar() or 0

        last_24h = await _count_since(24)
        last_7d = await _count_since(24 * 7)
        last_30d = await _count_since(24 * 30)

        return {
            "total": total,
            "by_status": by_status,
            "by_severity": by_severity,
            "by_source": by_source,
            "last_24h": last_24h,
            "last_7d": last_7d,
            "last_30d": last_30d,
        }
