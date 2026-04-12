"""Audit logging dependency for FastAPI endpoints.

Usage:
    @router.post("/users")
    async def create_user(
        audit: AuditContext = Depends(audit_context(action="user:create", target_type="user")),
        ...
    ):
        result = await service.create(data)
        await audit.commit(target_id=result.id, extra={"name": result.name})
        return result

Or simply:
    @router.post("/users")
    async def create_user(
        audit: AuditContext = Depends(audit_context("user:create")),
        ...
    ):
        ...
        await audit.commit()
"""

from dataclasses import dataclass, field

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from repositories.audit_repository import AuditRepository


@dataclass
class AuditContext:
    """Reusable audit context that auto-records on commit."""

    repo: AuditRepository
    action: str
    method: str
    path: str
    status_code: int = 200
    user_id: str | None = None
    target_type: str | None = None
    target_id: str | None = None
    extra: dict = field(default_factory=dict)
    _committed: bool = field(default=False, repr=False)

    async def commit(
        self,
        target_id: str | None = None,
        status_code: int | None = None,
        extra: dict | None = None,
    ) -> None:
        """Create the audit log entry and commit the session."""
        if self._committed:
            return

        await self.repo.create(
            action=self.action,
            method=self.method,
            path=self.path,
            status_code=status_code or self.status_code,
            user_id=self.user_id,
            target_type=self.target_type,
            target_id=target_id or self.target_id,
            extra_json={**self.extra, **(extra or {})},
        )
        await self.repo.session.commit()
        self._committed = True


def audit_context(
    action: str,
    target_type: str | None = None,
):
    """FastAPI dependency factory for audit logging.

    Args:
        action: Audit action name (e.g., "user:create")
        target_type: Optional target type (e.g., "user", "playbook_run")
    """

    async def _create(
        request: Request,
        session: AsyncSession,
    ) -> AuditContext:
        # Import here to avoid circular dependency

        # Try to get current user (may fail for some endpoints)
        user_id = None
        try:
            from core.security import decode_token

            auth_header = request.headers.get("authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]
                payload = decode_token(token)
                if payload:
                    user_id = payload.get("sub")
        except Exception:
            pass

        return AuditContext(
            repo=AuditRepository(session),
            action=action,
            method=request.method,
            path=str(request.url.path),
            user_id=user_id,
            target_type=target_type,
        )

    return _create
