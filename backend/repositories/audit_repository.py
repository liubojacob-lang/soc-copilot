"""Repository for audit log operations."""

import builtins
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.audit_log import AuditLogModel


def _parse_date(value: str | datetime) -> datetime:
    """Coerce a date filter (ISO string or datetime) to a datetime object.

    created_at is a DateTime column; comparing it against a raw string only
    works by accident on SQLite and fails outright on PostgreSQL.
    """
    if isinstance(value, datetime):
        return value
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


class AuditRepository:
    """Repository for audit log operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        action: str,
        method: str,
        path: str,
        status_code: int,
        user_id: str | None = None,
        target_type: str | None = None,
        target_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        duration_ms: int | None = None,
        extra_json: dict | None = None,
    ) -> AuditLogModel:
        """Create an audit log entry."""
        audit_log = AuditLogModel(
            user_id=user_id,
            action=action,
            method=method,
            path=path,
            status_code=status_code,
            target_type=target_type,
            target_id=target_id,
            ip_address=ip_address,
            user_agent=user_agent,
            duration_ms=duration_ms,
            extra_json=extra_json or {},
        )
        self.session.add(audit_log)
        await self.session.flush()
        await self.session.refresh(audit_log)
        return audit_log

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        user_id: str | None = None,
        action: str | None = None,
        path: str | None = None,
        status_code: str | None = None,  # Changed to str to support ranges
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> tuple[list[AuditLogModel], int]:
        """List audit logs with optional filters.

        Supports wildcard patterns:
        - action="login:*" matches all login actions
        - status_code="4xx" matches all 4xx codes
        - status_code="success" matches 2xx codes
        - status_code="error" matches 4xx+5xx codes
        """
        query = select(AuditLogModel)

        conditions = []
        if user_id:
            conditions.append(AuditLogModel.user_id == user_id)

        # Action filter with wildcard support (e.g., "login:*")
        if action:
            if action.endswith(":*"):
                # Wildcard: match all actions with this prefix
                prefix = action[:-2]  # Remove ":*" suffix
                conditions.append(AuditLogModel.action.like(f"{prefix}:%"))
            elif "*" in action:
                # Generic wildcard support
                conditions.append(AuditLogModel.action.like(action.replace("*", "%")))
            else:
                # Exact match
                conditions.append(AuditLogModel.action == action)

        # Path filter (already uses LIKE for partial matching)
        if path:
            # Support prefix matching with wildcard (e.g., "/api/playbook*")
            if path.endswith("*"):
                prefix = path[:-1]
                conditions.append(AuditLogModel.path.like(f"{prefix}%"))
            else:
                conditions.append(AuditLogModel.path.like(f"%{path}%"))

        # Status code filter with category support
        if status_code is not None:
            if status_code == "success" or status_code == "2xx":
                conditions.append(AuditLogModel.status_code.between(200, 299))
            elif status_code == "error" or status_code == "4xx+5xx":
                conditions.append(AuditLogModel.status_code >= 400)
            elif status_code == "4xx":
                conditions.append(AuditLogModel.status_code.between(400, 499))
            elif status_code == "5xx":
                conditions.append(AuditLogModel.status_code.between(500, 599))
            elif status_code == "3xx":
                conditions.append(AuditLogModel.status_code.between(300, 399))
            else:
                # Try to parse as integer
                try:
                    conditions.append(AuditLogModel.status_code == int(status_code))
                except (ValueError, TypeError):
                    pass  # Invalid status code, ignore filter

        if date_from:
            conditions.append(AuditLogModel.created_at >= _parse_date(date_from))
        if date_to:
            conditions.append(AuditLogModel.created_at <= _parse_date(date_to))

        if conditions:
            query = query.where(and_(*conditions))

        # Get total count
        count_query = select(func.count(AuditLogModel.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        count_result = await self.session.execute(count_query)
        total = count_result.scalar_one()

        # Get paginated results
        query = (
            query.order_by(AuditLogModel.created_at.desc()).offset(skip).limit(limit)
        )
        result = await self.session.execute(query)
        audit_logs = list(result.scalars().all())

        return audit_logs, total

    async def get_by_user(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[builtins.list[AuditLogModel], int]:
        """Get audit logs for a specific user."""
        return await self.list(skip=skip, limit=limit, user_id=user_id)

    async def get_by_target(
        self,
        target_type: str,
        target_id: str,
        skip: int = 0,
        limit: int = 50,
    ) -> builtins.list[AuditLogModel]:
        """Get audit logs for a specific target."""
        result = await self.session.execute(
            select(AuditLogModel)
            .where(
                and_(
                    AuditLogModel.target_type == target_type,
                    AuditLogModel.target_id == target_id,
                )
            )
            .order_by(AuditLogModel.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def delete_old_logs(self, days: int = 90) -> int:
        """Delete audit logs older than specified days. Returns count deleted."""
        cutoff = datetime.now(UTC) - timedelta(days=days)
        result = await self.session.execute(
            select(AuditLogModel.id).where(AuditLogModel.created_at < cutoff)
        )
        old_ids = [row[0] for row in result.all()]

        # Delete in batches
        batch_size = 1000
        deleted = 0
        for i in range(0, len(old_ids), batch_size):
            batch = old_ids[i : i + batch_size]
            await self.session.execute(
                select(AuditLogModel).where(AuditLogModel.id.in_(batch))
            )
            for log_id in batch:
                log = await self.session.get(AuditLogModel, log_id)
                if log:
                    await self.session.delete(log)
            deleted += len(batch)

        await self.session.flush()
        return deleted
