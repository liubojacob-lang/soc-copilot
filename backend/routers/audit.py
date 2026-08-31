"""Audit log API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from db.session import get_session
from dependencies.auth import get_current_user, require_role
from models.audit_log import AuditLogModel
from models.user import UserModel, UserRole
from repositories.audit_repository import AuditRepository
from schemas.audit import AuditLogListResponse, AuditLogResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/audit-logs", tags=["Audit Logs"])


@router.get("", response_model=AuditLogListResponse)
async def list_audit_logs(
    user_id: str | None = Query(None),
    action: str | None = Query(None),
    path: str | None = Query(None),
    status_code: Annotated[
        str | None,
        Query(
            description="Status code or category (e.g., '200', '4xx', 'error', 'success')"
        ),
    ] = None,
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: UserModel = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """List audit logs with filters.

    - admin/auditor: can see all logs
    - analyst: can only see their own logs
    """
    # Non-admin users can only see their own logs
    if current_user.role != UserRole.ADMIN and current_user.role != UserRole.AUDITOR:
        user_id = current_user.id

    skip = (page - 1) * page_size

    audit_repo = AuditRepository(session)
    logs, total = await audit_repo.list(
        skip=skip,
        limit=page_size,
        user_id=user_id,
        action=action,
        path=path,
        status_code=status_code,
        date_from=date_from,
        date_to=date_to,
    )

    # Batch fetch usernames (avoid N+1 queries)
    user_ids = {log.user_id for log in logs if log.user_id}
    username_map: dict[str, str | None] = {}
    if user_ids:
        user_result = await session.execute(
            select(UserModel.id, UserModel.username).where(UserModel.id.in_(user_ids))
        )
        username_map = dict(user_result.all())

    response_logs = []
    for log in logs:
        username = username_map.get(log.user_id) if log.user_id else None

        response_logs.append(
            AuditLogResponse(
                id=log.id,
                user_id=log.user_id,
                username=username,
                action=log.action,
                method=log.method,
                path=log.path,
                status_code=log.status_code,
                target_type=log.target_type,
                target_id=log.target_id,
                ip_address=log.ip_address,
                user_agent=log.user_agent,
                duration_ms=log.duration_ms,
                extra_json=log.extra_json,
                created_at=log.created_at,
            )
        )

    return AuditLogListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=response_logs,
    )


@router.get("/stats/summary")
async def get_audit_stats(
    current_user: UserModel = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get audit log statistics summary."""
    from datetime import datetime, timedelta

    from sqlalchemy import func

    # Time range: last 7 days
    (datetime.now() - timedelta(days=7)).isoformat()

    # Build base query
    query = select(func.count(AuditLogModel.id))
    if current_user.role != UserRole.ADMIN and current_user.role != UserRole.AUDITOR:
        query = query.where(AuditLogModel.user_id == current_user.id)

    # Total requests
    total_result = await session.execute(query)
    total = total_result.scalar_one() or 0

    # Failed requests (4xx, 5xx)
    query_failed = query.where(AuditLogModel.status_code >= 400)
    failed_result = await session.execute(query_failed)
    failed = failed_result.scalar_one() or 0

    # Last 24 hours
    day_ago = (datetime.now() - timedelta(days=1)).isoformat()
    query_day = query.where(AuditLogModel.created_at >= day_ago)
    day_result = await session.execute(query_day)
    last_24h = day_result.scalar_one() or 0

    # Top actions

    action_query = select(
        AuditLogModel.action, func.count(AuditLogModel.id).label("count")
    )
    if current_user.role != UserRole.ADMIN and current_user.role != UserRole.AUDITOR:
        action_query = action_query.where(AuditLogModel.user_id == current_user.id)
    action_query = (
        action_query.group_by(AuditLogModel.action)
        .order_by(func.count(AuditLogModel.id).desc())
        .limit(10)
    )
    action_result = await session.execute(action_query)
    top_actions = [{"action": row[0], "count": row[1]} for row in action_result.all()]

    return {
        "total_requests": total,
        "failed_requests": failed,
        "last_24h_requests": last_24h,
        "top_actions": top_actions,
    }


@router.get("/target/{target_type}/{target_id}")
async def get_target_audit_logs(
    target_type: str,
    target_id: str,
    current_user: UserModel = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get audit logs for a specific target (e.g., playbook_run, user)."""
    audit_repo = AuditRepository(session)

    # Non-admin users can only see logs for their own targets
    if current_user.role != UserRole.ADMIN and current_user.role != UserRole.AUDITOR:
        # Only allow if target is their own user
        if target_type != "user" or target_id != current_user.id:
            raise HTTPException(status_code=403, detail="Permission denied")

    logs = await audit_repo.get_by_target(target_type, target_id)

    return {
        "target_type": target_type,
        "target_id": target_id,
        "logs": [
            {
                "id": log.id,
                "user_id": log.user_id,
                "action": log.action,
                "method": log.method,
                "path": log.path,
                "status_code": log.status_code,
                "created_at": log.created_at,
                "extra_json": log.extra_json,
            }
            for log in logs
        ],
    }


@router.post("/cleanup")
async def cleanup_old_logs(
    days: int = Query(90, ge=30, le=365),
    current_user: UserModel = Depends(require_role(UserRole.ADMIN)),
    session: AsyncSession = Depends(get_session),
):
    """Clean up audit logs older than specified days (admin only)."""
    audit_repo = AuditRepository(session)
    deleted = await audit_repo.delete_old_logs(days=days)

    # Create audit log for the cleanup itself
    await audit_repo.create(
        action="audit:cleanup",
        method="POST",
        path="/api/v1/audit-logs/cleanup",
        status_code=200,
        user_id=current_user.id,
        extra_json={"days": days, "deleted_count": deleted},
    )
    await session.commit()

    return {"message": f"Deleted {deleted} old audit logs"}
