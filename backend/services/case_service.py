"""Case service for business logic.

Handles case lifecycle, status transitions, SLA tracking, timeline
aggregation, and alert association.
"""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from models.case import CaseModel
from repositories.case_repository import CaseRepository
from schemas.case import (
    VALID_TRANSITIONS,
    CaseAlertLink,
    CaseAssign,
    CaseCreate,
    CaseDetailResponse,
    CaseListResponse,
    CaseResponse,
    CaseStatsResponse,
    CaseStatus,
    CaseStatusUpdate,
    CaseUpdate,
    CommentCreate,
    CommentResponse,
    TimelineEntryResponse,
)

logger = get_logger(__name__)


class CaseService:
    """Service for case management and lifecycle operations."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = CaseRepository()

    # ── Helpers ────────────────────────────────────────────────────

    def _to_response(self, case: CaseModel) -> CaseResponse:
        """Convert CaseModel to CaseResponse."""
        return CaseResponse(
            id=case.id,
            title=case.title,
            description=case.description,
            severity=case.severity,
            status=case.status,
            assigned_to=case.assigned_to,
            sla_due_at=case.sla_due_at,
            sla_deadline=case.sla_due_at,
            resolution=case.resolution,
            resolved_at=case.resolved_at,
            closed_at=case.closed_at,
            tenant_id=case.tenant_id,
            created_at=case.created_at,
            updated_at=case.updated_at,
        )

    async def _to_detail(self, case: CaseModel) -> CaseDetailResponse:
        """Convert CaseModel to CaseDetailResponse with relations."""
        alerts = await self.repo.get_case_alerts(self.session, case.id)
        alert_count = await self.repo.count_alerts(self.session, case.id)
        comment_count = await self.repo.count_comments(self.session, case.id)

        # Build assignee info
        assignee = None
        if hasattr(case, "assignee") and case.assignee is not None:
            a = case.assignee
            assignee = {
                "id": a.id,
                "username": a.username,
                "email": a.email,
            }

        return CaseDetailResponse(
            id=case.id,
            title=case.title,
            description=case.description,
            severity=case.severity,
            status=case.status,
            assigned_to=case.assigned_to,
            sla_due_at=case.sla_due_at,
            sla_deadline=case.sla_due_at,
            resolution=case.resolution,
            resolved_at=case.resolved_at,
            closed_at=case.closed_at,
            tenant_id=case.tenant_id,
            created_at=case.created_at,
            updated_at=case.updated_at,
            alert_count=alert_count,
            related_alert_count=alert_count,
            comment_count=comment_count,
            alerts=alerts,
            timeline_entries=[
                TimelineEntryResponse(
                    id=e.id,
                    case_id=e.case_id,
                    entry_type=e.entry_type,
                    summary=e.summary,
                    source_alert_id=e.source_alert_id,
                    performed_by=e.performed_by,
                    occurred_at=e.occurred_at,
                    metadata_json=e.metadata_json,
                )
                for e in (case.timeline_entries or [])
            ],
            comments=[
                CommentResponse(
                    id=c.id,
                    case_id=c.case_id,
                    user_id=c.user_id,
                    username=c.username,
                    content=c.content,
                    created_at=c.created_at,
                    updated_at=c.updated_at,
                )
                for c in (case.comments or [])
            ],
            assignee=assignee,
        )

    # ── CRUD ───────────────────────────────────────────────────────

    async def create(
        self, data: CaseCreate, user_id: str | None = None
    ) -> CaseDetailResponse:
        """Create a new case with initial timeline entry."""
        case = await self.repo.create(
            self.session,
            title=data.title,
            description=data.description,
            severity=data.severity.value,
            status=data.status.value,
            assigned_to=data.assigned_to,
            sla_due_at=data.sla_due_at,
        )

        # Add initial timeline entry
        await self.repo.add_timeline_entry(
            self.session,
            case_id=case.id,
            entry_type="status_change",
            summary=f"Case created with status '{data.status.value}' and severity '{data.severity.value}'",
            performed_by=user_id,
        )

        # Link initial alerts if provided
        if data.alert_ids:
            int_alert_ids = []
            for a_id in data.alert_ids:
                try:
                    int_alert_ids.append(int(a_id))
                except (ValueError, TypeError):
                    pass
            if int_alert_ids:
                from sqlalchemy import select
                from models.security_alert import SecurityAlert

                existing_alerts_res = await self.session.execute(
                    select(SecurityAlert.id).where(SecurityAlert.id.in_(int_alert_ids))
                )
                valid_ids = list(existing_alerts_res.scalars().all())

                if valid_ids:
                    linked = await self.repo.link_alerts(
                        self.session,
                        case_id=case.id,
                        alert_ids=valid_ids,
                        added_by=user_id,
                    )
                    if linked > 0:
                        await self.repo.add_timeline_entry(
                            self.session,
                            case_id=case.id,
                            entry_type="alert",
                            summary=f"Linked {linked} alert(s) on case creation (IDs: {valid_ids})",
                            performed_by=user_id,
                        )

        await self.session.commit()

        logger.info(f"Case created: {case.id} - {case.title}")
        # Re-fetch with relations eagerly loaded; _to_detail reads them
        case = await self.repo.get_by_id(self.session, case.id)
        return await self._to_detail(case)

    async def get_by_id(self, case_id: str) -> CaseDetailResponse | None:
        """Get case detail by ID."""
        case = await self.repo.get_by_id(self.session, case_id)
        if not case:
            return None
        return await self._to_detail(case)

    async def list_cases(
        self,
        status: str | None = None,
        severity: str | None = None,
        assigned_to: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_desc: bool = True,
    ) -> CaseListResponse:
        """List cases with filters and pagination."""
        offset = (page - 1) * page_size
        items, total = await self.repo.list_cases(
            self.session,
            status=status,
            severity=severity,
            assigned_to=assigned_to,
            search=search,
            limit=page_size,
            offset=offset,
            sort_by=sort_by,
            sort_desc=sort_desc,
        )

        # Enrich with counts (optimized: eliminates N+1 queries via bulk counts)
        case_ids = [c.id for c in items]
        alert_counts, comment_counts = await self.repo.get_bulk_counts(
            self.session, case_ids
        )
        responses = []
        for case in items:
            resp = self._to_response(case)
            count = alert_counts.get(case.id, 0)
            resp.alert_count = count
            resp.related_alert_count = count
            resp.comment_count = comment_counts.get(case.id, 0)
            responses.append(resp)

        return CaseListResponse(
            items=responses,
            cases=responses,
            total=total,
            page=page,
            page_size=page_size,
        )

    async def update(
        self,
        case_id: str,
        data: CaseUpdate,
        user_id: str | None = None,
    ) -> CaseDetailResponse:
        """Update a case."""
        case = await self.repo.get_by_id_simple(self.session, case_id)
        if not case:
            raise ValueError(f"Case not found: {case_id}")

        update_data = data.model_dump(exclude_unset=True)
        if update_data.get("severity"):
            update_data["severity"] = (
                update_data["severity"].value
                if hasattr(update_data["severity"], "value")
                else update_data["severity"]
            )

        changes = []
        for key, val in update_data.items():
            if val is not None:
                old_val = getattr(case, key, None)
                if old_val != val:
                    changes.append(f"{key}: '{old_val}' → '{val}'")

        case = await self.repo.update(self.session, case, **update_data)

        if changes:
            await self.repo.add_timeline_entry(
                self.session,
                case_id=case.id,
                entry_type="status_change",
                summary=f"Case updated: {'; '.join(changes)}",
                performed_by=user_id,
            )
        await self.session.commit()

        logger.info(f"Case updated: {case_id}")
        # Re-fetch with relations eagerly loaded; _to_detail reads them
        case = await self.repo.get_by_id(self.session, case_id)
        return await self._to_detail(case)

    async def delete(self, case_id: str) -> None:
        """Delete a case."""
        case = await self.repo.get_by_id_simple(self.session, case_id)
        if not case:
            raise ValueError(f"Case not found: {case_id}")
        await self.repo.delete(self.session, case)
        await self.session.commit()
        logger.info(f"Case deleted: {case_id}")

    # ── Status Management ──────────────────────────────────────────

    async def update_status(
        self,
        case_id: str,
        data: CaseStatusUpdate,
        user_id: str | None = None,
    ) -> CaseDetailResponse:
        """Update case status with validation."""
        case = await self.repo.get_by_id_simple(self.session, case_id)
        if not case:
            raise ValueError(f"Case not found: {case_id}")

        current_status = CaseStatus(case.status)
        new_status = data.status

        # Validate transition
        allowed = VALID_TRANSITIONS.get(current_status, [])
        if new_status not in allowed:
            raise ValueError(
                f"Invalid status transition: '{current_status.value}' → '{new_status.value}'."
                f" Allowed: {[s.value for s in allowed]}"
            )

        update_kwargs = {"status": new_status.value}
        summary = f"Status changed: '{current_status.value}' → '{new_status.value}'"

        if new_status == CaseStatus.resolved:
            update_kwargs["resolved_at"] = datetime.now(UTC)
            update_kwargs["resolution"] = data.resolution
            summary += (
                f" (resolution: {data.resolution[:100]}...)"
                if data.resolution and len(data.resolution) > 100
                else f" (resolution: {data.resolution})" if data.resolution else ""
            )

        if new_status == CaseStatus.closed:
            update_kwargs["closed_at"] = datetime.now(UTC)

        case = await self.repo.update(self.session, case, **update_kwargs)

        await self.repo.add_timeline_entry(
            self.session,
            case_id=case.id,
            entry_type="status_change",
            summary=summary,
            performed_by=user_id,
        )
        await self.session.commit()

        # Reset SLA for investigating
        if new_status == CaseStatus.investigating and not case.sla_due_at:
            # Default SLA: 24 hours for high/critical, 72 hours for medium, 7 days for low
            sla_hours = {"critical": 8, "high": 24, "medium": 72, "low": 168}
            hours = sla_hours.get(case.severity, 72)
            from datetime import timedelta

            sla_due = datetime.now(UTC) + timedelta(hours=hours)
            await self.repo.update(self.session, case, sla_due_at=sla_due)

        logger.info(f"Case status updated: {case_id} → {new_status.value}")

        # Refresh with relations
        case = await self.repo.get_by_id(self.session, case_id)
        return await self._to_detail(case)

    # ── Assignment ─────────────────────────────────────────────────

    async def assign(
        self,
        case_id: str,
        data: CaseAssign,
        user_id: str | None = None,
    ) -> CaseDetailResponse:
        """Assign case to an analyst."""
        case = await self.repo.get_by_id_simple(self.session, case_id)
        if not case:
            raise ValueError(f"Case not found: {case_id}")

        old_assignee = case.assigned_to
        case = await self.repo.update(self.session, case, assigned_to=data.assigned_to)

        summary = (
            f"Assignee changed: '{old_assignee}' → '{data.assigned_to}'"
            if old_assignee
            else f"Assigned to '{data.assigned_to}'"
        )
        await self.repo.add_timeline_entry(
            self.session,
            case_id=case.id,
            entry_type="assignment",
            summary=summary,
            performed_by=user_id,
        )
        await self.session.commit()

        logger.info(f"Case assigned: {case_id} → {data.assigned_to}")
        case = await self.repo.get_by_id(self.session, case_id)
        return await self._to_detail(case)

    # ── Alert Linking ──────────────────────────────────────────────

    async def link_alerts(
        self,
        case_id: str,
        data: CaseAlertLink,
        user_id: str | None = None,
    ) -> CaseDetailResponse:
        """Link alerts to a case."""
        case = await self.repo.get_by_id_simple(self.session, case_id)
        if not case:
            raise ValueError(f"Case not found: {case_id}")

        int_alert_ids = []
        for a in data.alert_ids:
            try:
                int_alert_ids.append(int(a))
            except (ValueError, TypeError):
                pass

        linked = await self.repo.link_alerts(
            self.session,
            case_id=case_id,
            alert_ids=int_alert_ids,
            added_by=user_id,
        )

        if linked > 0:
            await self.repo.add_timeline_entry(
                self.session,
                case_id=case.id,
                entry_type="alert",
                summary=f"Linked {linked} alert(s) to case (IDs: {int_alert_ids})",
                performed_by=user_id,
            )
        await self.session.commit()

        logger.info(f"Linked {linked} alerts to case {case_id}")
        case = await self.repo.get_by_id(self.session, case_id)
        return await self._to_detail(case)

    async def unlink_alert(
        self,
        case_id: str,
        alert_id: int,
        user_id: str | None = None,
    ) -> CaseDetailResponse:
        """Unlink an alert from a case."""
        case = await self.repo.get_by_id_simple(self.session, case_id)
        if not case:
            raise ValueError(f"Case not found: {case_id}")

        removed = await self.repo.unlink_alert(self.session, case_id, alert_id)

        if removed:
            await self.repo.add_timeline_entry(
                self.session,
                case_id=case.id,
                entry_type="alert",
                summary=f"Unlinked alert #{alert_id} from case",
                performed_by=user_id,
            )
        await self.session.commit()

        logger.info(f"Unlinked alert {alert_id} from case {case_id}")
        case = await self.repo.get_by_id(self.session, case_id)
        return await self._to_detail(case)

    # ── Comments ───────────────────────────────────────────────────

    async def add_comment(
        self,
        case_id: str,
        data: CommentCreate,
        user_id: str,
        username: str,
    ) -> CommentResponse:
        """Add a comment to a case."""
        case = await self.repo.get_by_id_simple(self.session, case_id)
        if not case:
            raise ValueError(f"Case not found: {case_id}")

        comment = await self.repo.add_comment(
            self.session,
            case_id=case_id,
            user_id=user_id,
            username=username,
            content=data.content,
        )

        await self.repo.add_timeline_entry(
            self.session,
            case_id=case_id,
            entry_type="comment",
            summary=f"Comment added by {username}",
            performed_by=user_id,
        )
        await self.session.commit()

        logger.info(f"Comment added to case {case_id}")
        return CommentResponse(
            id=comment.id,
            case_id=comment.case_id,
            user_id=comment.user_id,
            username=comment.username,
            content=comment.content,
            created_at=comment.created_at,
            updated_at=comment.updated_at,
        )

    # ── Statistics ─────────────────────────────────────────────────

    async def get_stats(self) -> CaseStatsResponse:
        """Get case statistics for dashboard."""
        stats = await self.repo.get_stats(self.session)
        return CaseStatsResponse(**stats)

    # ── Batch Operations  —  v0.9.0 ─────────────────────────────────

    async def batch_update_status(
        self,
        case_ids: list[str],
        status: CaseStatus,
        resolution: str | None = None,
        user_id: str | None = None,
    ) -> dict:
        """Batch update case statuses with validation.

        Args:
            case_ids: List of case IDs (1-200)
            status: Target status for all cases
            resolution: Optional resolution note
            user_id: User performing the action

        Returns:
            {total, success_count, failed_count, results, errors}
        """
        total = len(case_ids)
        success_count = 0
        failed_count = 0
        results: list[dict] = []
        errors: list[dict] = []

        for case_id in case_ids:
            try:
                case = await self.repo.get_by_id_simple(self.session, case_id)
                if not case:
                    failed_count += 1
                    error_entry = {"case_id": case_id, "error": "Case not found"}
                    errors.append(error_entry)
                    results.append(
                        {
                            "case_id": case_id,
                            "success": False,
                            "error": "Case not found",
                        }
                    )
                    continue

                current_status = CaseStatus(case.status)
                if isinstance(status, str):
                    status_obj = CaseStatus(status)
                else:
                    status_obj = status

                # Validate transition
                allowed = VALID_TRANSITIONS.get(current_status, [])
                if status_obj not in allowed:
                    failed_count += 1
                    msg = (
                        f"Invalid transition: '{current_status.value}' → '{status_obj.value}'. "
                        f"Allowed: {[s.value for s in allowed]}"
                    )
                    errors.append({"case_id": case_id, "error": msg})
                    results.append({"case_id": case_id, "success": False, "error": msg})
                    continue

                update_kwargs = {"status": status_obj.value}

                if status_obj == CaseStatus.resolved:
                    update_kwargs["resolved_at"] = datetime.now(UTC)
                    if resolution:
                        update_kwargs["resolution"] = resolution
                if status_obj == CaseStatus.closed:
                    update_kwargs["closed_at"] = datetime.now(UTC)

                await self.repo.update(self.session, case, **update_kwargs)

                await self.repo.add_timeline_entry(
                    self.session,
                    case_id=case.id,
                    entry_type="status_change",
                    summary=f"Batch status change: '{current_status.value}' → '{status_obj.value}'",
                    performed_by=user_id,
                )
                await self.session.commit()

                success_count += 1
                results.append(
                    {"case_id": case_id, "success": True, "title": case.title}
                )

            except Exception as e:
                await self.session.rollback()
                failed_count += 1
                error_entry = {"case_id": case_id, "error": str(e)}
                errors.append(error_entry)
                results.append({"case_id": case_id, "success": False, "error": str(e)})
                logger.warning(
                    "Batch status update failed for case %s: %s", case_id, str(e)
                )

        logger.info(
            "Batch case status: total=%d success=%d failed=%d → %s",
            total,
            success_count,
            failed_count,
            status_obj.value,
        )
        return {
            "total": total,
            "success_count": success_count,
            "failed_count": failed_count,
            "results": results,
            "errors": errors,
        }

    async def batch_assign(
        self,
        case_ids: list[str],
        assigned_to: str,
        user_id: str | None = None,
    ) -> dict:
        """Batch assign cases to an analyst.

        Args:
            case_ids: List of case IDs (1-200)
            assigned_to: User ID to assign cases to
            user_id: User performing the action

        Returns:
            {total, success_count, failed_count, results, errors}
        """
        total = len(case_ids)
        success_count = 0
        failed_count = 0
        results: list[dict] = []
        errors: list[dict] = []

        for case_id in case_ids:
            try:
                case = await self.repo.get_by_id_simple(self.session, case_id)
                if not case:
                    failed_count += 1
                    error_entry = {"case_id": case_id, "error": "Case not found"}
                    errors.append(error_entry)
                    results.append(
                        {
                            "case_id": case_id,
                            "success": False,
                            "error": "Case not found",
                        }
                    )
                    continue

                old_assignee = case.assigned_to
                await self.repo.update(self.session, case, assigned_to=assigned_to)

                summary = (
                    f"Batch assignment: '{old_assignee}' → '{assigned_to}'"
                    if old_assignee
                    else f"Batch assigned to '{assigned_to}'"
                )
                await self.repo.add_timeline_entry(
                    self.session,
                    case_id=case.id,
                    entry_type="assignment",
                    summary=summary,
                    performed_by=user_id,
                )
                await self.session.commit()

                success_count += 1
                results.append(
                    {"case_id": case_id, "success": True, "title": case.title}
                )

            except Exception as e:
                await self.session.rollback()
                failed_count += 1
                error_entry = {"case_id": case_id, "error": str(e)}
                errors.append(error_entry)
                results.append({"case_id": case_id, "success": False, "error": str(e)})
                logger.warning("Batch assign failed for case %s: %s", case_id, str(e))

        logger.info(
            "Batch case assign: total=%d success=%d failed=%d → %s",
            total,
            success_count,
            failed_count,
            assigned_to,
        )
        return {
            "total": total,
            "success_count": success_count,
            "failed_count": failed_count,
            "results": results,
            "errors": errors,
        }
