"""Case repository for database operations."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.case import (
    CaseAlertAssociation,
    CaseComment,
    CaseModel,
    CaseTimelineEntry,
)
from models.security_alert import SecurityAlert


class CaseRepository:
    """Repository for case CRUD and query operations."""

    # ── Case CRUD ──────────────────────────────────────────────────

    async def create(self, session: AsyncSession, **kwargs) -> CaseModel:
        """Create a new case."""
        case = CaseModel(
            id=str(uuid.uuid4()),
            **kwargs,
        )
        session.add(case)
        await session.flush()
        return case

    async def get_by_id(self, session: AsyncSession, case_id: str) -> CaseModel | None:
        """Get case by ID with relations."""
        result = await session.execute(
            select(CaseModel)
            .options(
                selectinload(CaseModel.timeline_entries),
                selectinload(CaseModel.comments),
                selectinload(CaseModel.assignee),
            )
            .where(CaseModel.id == case_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_simple(
        self, session: AsyncSession, case_id: str
    ) -> CaseModel | None:
        """Get case by ID without loading relations."""
        result = await session.execute(select(CaseModel).where(CaseModel.id == case_id))
        return result.scalar_one_or_none()

    async def list_cases(
        self,
        session: AsyncSession,
        status: str | None = None,
        severity: str | None = None,
        assigned_to: str | None = None,
        search: str | None = None,
        limit: int = 20,
        offset: int = 0,
        sort_by: str = "created_at",
        sort_desc: bool = True,
    ) -> tuple[list[CaseModel], int]:
        """List cases with filters and pagination."""
        # Build base query
        conditions = []

        if status:
            conditions.append(CaseModel.status == status)
        if severity:
            conditions.append(CaseModel.severity == severity)
        if assigned_to:
            conditions.append(CaseModel.assigned_to == assigned_to)
        if search:
            search_pattern = f"%{search}%"
            conditions.append(
                or_(
                    CaseModel.title.ilike(search_pattern),
                    CaseModel.description.ilike(search_pattern),
                )
            )

        # Count query
        count_stmt = select(func.count(CaseModel.id))
        if conditions:
            count_stmt = count_stmt.where(and_(*conditions))
        count_result = await session.execute(count_stmt)
        total = count_result.scalar() or 0

        # List query
        stmt = select(CaseModel).options(
            selectinload(CaseModel.assignee),
        )
        if conditions:
            stmt = stmt.where(and_(*conditions))

        # Sorting
        sort_col = getattr(CaseModel, sort_by, CaseModel.created_at)
        if sort_desc:
            stmt = stmt.order_by(sort_col.desc())
        else:
            stmt = stmt.order_by(sort_col.asc())

        stmt = stmt.limit(limit).offset(offset)
        result = await session.execute(stmt)
        items = list(result.scalars().all())

        return items, total

    async def update(
        self, session: AsyncSession, case: CaseModel, **kwargs
    ) -> CaseModel:
        """Update a case with provided fields."""
        for field_name, value in kwargs.items():
            if value is not None and hasattr(case, field_name):
                setattr(case, field_name, value)
        await session.flush()
        return case

    async def delete(self, session: AsyncSession, case: CaseModel) -> None:
        """Delete a case."""
        await session.delete(case)
        await session.flush()

    # ── Alert Linking ──────────────────────────────────────────────

    async def link_alerts(
        self,
        session: AsyncSession,
        case_id: str,
        alert_ids: list[int],
        added_by: str | None = None,
    ) -> int:
        """Link alerts to a case. Returns count of newly linked."""
        now = datetime.now(UTC)
        linked = 0

        for alert_id in alert_ids:
            # Check if already linked
            existing = await session.execute(
                select(CaseAlertAssociation).where(
                    and_(
                        CaseAlertAssociation.case_id == case_id,
                        CaseAlertAssociation.alert_id == alert_id,
                    )
                )
            )
            if existing.scalar_one_or_none():
                continue

            assoc = CaseAlertAssociation(
                case_id=case_id,
                alert_id=alert_id,
                added_at=now,
                added_by=added_by,
            )
            session.add(assoc)
            linked += 1

        await session.flush()
        return linked

    async def unlink_alert(
        self, session: AsyncSession, case_id: str, alert_id: int
    ) -> bool:
        """Unlink an alert from a case."""
        assoc = await session.execute(
            select(CaseAlertAssociation).where(
                and_(
                    CaseAlertAssociation.case_id == case_id,
                    CaseAlertAssociation.alert_id == alert_id,
                )
            )
        )
        entity = assoc.scalar_one_or_none()
        if entity:
            await session.delete(entity)
            await session.flush()
            return True
        return False

    async def get_case_alerts(self, session: AsyncSession, case_id: str) -> list[dict]:
        """Get alerts linked to a case."""
        result = await session.execute(
            select(SecurityAlert).join(
                CaseAlertAssociation,
                and_(
                    CaseAlertAssociation.alert_id == SecurityAlert.id,
                    CaseAlertAssociation.case_id == case_id,
                ),
            )
        )
        alerts = result.scalars().all()
        return [
            {
                "id": a.id,
                "title": a.title,
                "source": a.source,
                "severity": a.severity,
                "status": a.status,
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "event_timestamp": (
                    a.event_timestamp.isoformat() if a.event_timestamp else None
                ),
            }
            for a in alerts
        ]

    async def count_alerts(self, session: AsyncSession, case_id: str) -> int:
        """Count alerts linked to a case."""
        result = await session.execute(
            select(func.count(CaseAlertAssociation.case_id)).where(
                CaseAlertAssociation.case_id == case_id
            )
        )
        return result.scalar() or 0

    # ── Comments ───────────────────────────────────────────────────

    async def add_comment(
        self,
        session: AsyncSession,
        case_id: str,
        user_id: str,
        username: str,
        content: str,
    ) -> CaseComment:
        """Add a comment to a case."""
        comment = CaseComment(
            id=str(uuid.uuid4()),
            case_id=case_id,
            user_id=user_id,
            username=username,
            content=content,
        )
        session.add(comment)
        await session.flush()
        return comment

    async def count_comments(self, session: AsyncSession, case_id: str) -> int:
        """Count comments on a case."""
        result = await session.execute(
            select(func.count(CaseComment.id)).where(CaseComment.case_id == case_id)
        )
        return result.scalar() or 0

    # ── Timeline ───────────────────────────────────────────────────

    async def add_timeline_entry(
        self,
        session: AsyncSession,
        case_id: str,
        entry_type: str,
        summary: str,
        performed_by: str | None = None,
        source_alert_id: int | None = None,
        metadata_json: str | None = None,
    ) -> CaseTimelineEntry:
        """Add a timeline entry to a case."""
        entry = CaseTimelineEntry(
            id=str(uuid.uuid4()),
            case_id=case_id,
            entry_type=entry_type,
            summary=summary,
            source_alert_id=source_alert_id,
            performed_by=performed_by,
            metadata_json=metadata_json,
        )
        session.add(entry)
        await session.flush()
        return entry

    # ── Statistics / Dashboard ─────────────────────────────────────

    async def get_stats(self, session: AsyncSession) -> dict:
        """Get case statistics for dashboard."""
        now = datetime.now(UTC)

        # Total cases
        total_result = await session.execute(select(func.count(CaseModel.id)))
        total = total_result.scalar() or 0

        # By status
        status_result = await session.execute(
            select(CaseModel.status, func.count(CaseModel.id)).group_by(
                CaseModel.status
            )
        )
        by_status = {row[0]: row[1] for row in status_result.all()}

        # By severity
        sev_result = await session.execute(
            select(CaseModel.severity, func.count(CaseModel.id)).group_by(
                CaseModel.severity
            )
        )
        by_severity = {row[0]: row[1] for row in sev_result.all()}

        # Open cases (not resolved/closed)
        open_result = await session.execute(
            select(func.count(CaseModel.id)).where(
                CaseModel.status.in_(["new", "investigating", "pending_review"])
            )
        )
        open_cases = open_result.scalar() or 0

        # Overdue cases (past SLA and not closed/resolved)
        overdue_result = await session.execute(
            select(func.count(CaseModel.id)).where(
                and_(
                    CaseModel.sla_due_at.isnot(None),
                    CaseModel.sla_due_at < now,
                    CaseModel.status.notin_(["resolved", "closed"]),
                )
            )
        )
        overdue_cases = overdue_result.scalar() or 0

        # Resolved today
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        resolved_today_result = await session.execute(
            select(func.count(CaseModel.id)).where(
                and_(
                    CaseModel.status == "resolved",
                    CaseModel.resolved_at >= today_start,
                )
            )
        )
        resolved_today = resolved_today_result.scalar() or 0

        # Average resolution time in hours
        avg_result = await session.execute(
            select(
                func.avg(
                    func.julianday(CaseModel.resolved_at)
                    - func.julianday(CaseModel.created_at)
                )
                * 24
            ).where(
                and_(
                    CaseModel.resolved_at.isnot(None),
                    CaseModel.status.in_(["resolved", "closed"]),
                )
            )
        )
        avg_res = avg_result.scalar()
        avg_resolution_hours = round(float(avg_res), 1) if avg_res else None

        return {
            "total": total,
            "by_status": by_status,
            "by_severity": by_severity,
            "open_cases": open_cases,
            "overdue_cases": overdue_cases,
            "resolved_today": resolved_today,
            "avg_resolution_hours": avg_resolution_hours,
        }
