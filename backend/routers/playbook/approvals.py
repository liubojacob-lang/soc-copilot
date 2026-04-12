"""Approval workflow endpoints.

This module contains endpoints for:
- Listing approval requests
- Approving/rejecting approvals
- Getting pending approval count
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from db.session import get_session
from dependencies.auth import get_current_user
from models.playbook_approval import PlaybookApprovalModel
from models.user import UserModel, UserRole
from repositories.audit_repository import AuditRepository

logger = get_logger(__name__)

router = APIRouter(tags=["playbook-approvals"])


class ApprovalListResponse(BaseModel):
    """Response for approval list."""

    items: list[dict]
    total: int
    page: int
    page_size: int


class ApprovalActionRequest(BaseModel):
    """Request for approve/reject action."""

    comments: str | None = None


@router.get("/approvals", response_model=ApprovalListResponse)
async def list_approvals(
    status: str | None = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> ApprovalListResponse:
    """List approval requests.

    - admin/auditor: can see all pending approvals
    - analyst: can only see their own approval requests
    """
    # Build base query
    stmt = select(PlaybookApprovalModel)

    # Role-based filtering
    if current_user.role == UserRole.ANALYST:
        # Analysts can only see their own requests
        stmt = stmt.where(PlaybookApprovalModel.requested_by_user_id == current_user.id)
    # admin and auditor can see all

    # Status filter
    if status:
        stmt = stmt.where(PlaybookApprovalModel.status == status)

    # Order by created_at desc (newest first)
    stmt = stmt.order_by(PlaybookApprovalModel.created_at.desc())

    # Get total count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await session.execute(count_stmt)
    total = total_result.scalar_one() or 0

    # Apply pagination
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)

    # Execute query
    result = await session.execute(stmt)
    approvals = result.scalars().all()

    # Get usernames
    items = []
    for approval in approvals:
        requested_by = None
        if approval.requested_by_user_id:
            user_result = await session.execute(
                select(UserModel.username).where(
                    UserModel.id == approval.requested_by_user_id
                )
            )
            requested_by = user_result.scalar_one_or_none()

        approved_by = None
        if approval.approved_by_user_id:
            user_result = await session.execute(
                select(UserModel.username).where(
                    UserModel.id == approval.approved_by_user_id
                )
            )
            approved_by = user_result.scalar_one_or_none()

        rejected_by = None
        if approval.rejected_by_user_id:
            user_result = await session.execute(
                select(UserModel.username).where(
                    UserModel.id == approval.rejected_by_user_id
                )
            )
            rejected_by = user_result.scalar_one_or_none()

        items.append(
            {
                "id": approval.id,
                "run_id": approval.run_id,
                "node_id": approval.node_id,
                "status": approval.status,
                "title": approval.title,
                "message": approval.message,
                "comments": approval.comments,
                "requested_by": requested_by,
                "approved_by": approved_by,
                "rejected_by": rejected_by,
                "created_at": (
                    approval.created_at.isoformat() if approval.created_at else None
                ),
                "decided_at": (
                    approval.decided_at.isoformat() if approval.decided_at else None
                ),
                "expires_at": (
                    approval.expires_at.isoformat() if approval.expires_at else None
                ),
            }
        )

    return ApprovalListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/approvals/{approval_id}/approve")
async def approve_approval(
    approval_id: str,
    request: ApprovalActionRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict:
    """Approve an approval request.

    Only admin and auditor roles can approve.
    Analysts cannot approve (to avoid self-approval).

    Approval will:
    1. Update approval status to 'approved'
    2. Log to audit_logs
    3. Resume playbook execution
    """
    # Check permissions - only admin and auditor can approve
    if current_user.role not in [UserRole.ADMIN, UserRole.AUDITOR]:
        raise HTTPException(
            status_code=403, detail="Only admin and auditor roles can approve requests"
        )

    # Get approval
    stmt = select(PlaybookApprovalModel).where(PlaybookApprovalModel.id == approval_id)
    result = await session.execute(stmt)
    approval = result.scalar_one_or_none()

    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")

    if approval.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Approval is not pending (current status: {approval.status})",
        )

    # Check if expired
    if approval.expires_at and approval.expires_at < datetime.now(UTC):
        approval.status = "expired"
        await session.commit()
        raise HTTPException(status_code=400, detail="Approval has expired")

    # Update approval
    approval.status = "approved"
    approval.approved_by_user_id = current_user.id
    approval.decided_at = datetime.now(UTC)
    approval.comments = request.comments

    # Audit log
    audit_repo = AuditRepository(session)
    await audit_repo.create(
        action="approval:approve",
        method="POST",
        path=f"/api/playbook/approvals/{approval_id}/approve",
        status_code=200,
        user_id=current_user.id,
        target_type="approval",
        target_id=approval_id,
        extra_json={
            "run_id": approval.run_id,
            "node_id": approval.node_id,
            "comments": request.comments,
        },
    )

    await session.commit()

    # Resume playbook execution
    try:
        from services.playbook.playbook_run_service import PlaybookRunService

        run_service = PlaybookRunService(session)

        await run_service.resume_from_approval(
            run_id=approval.run_id,
            node_id=approval.node_id,
            approved=True,
            comments=request.comments,
        )

        logger.info(
            f"[{approval.run_id}] Approval {approval_id} approved by {current_user.username}, "
            f"resuming execution"
        )

    except Exception as e:
        logger.error(f"[{approval.run_id}] Failed to resume execution: {e}")
        # Don't fail the request - approval was recorded
        pass

    return {
        "message": "Approval approved",
        "approval_id": approval_id,
        "status": "approved",
    }


@router.post("/approvals/{approval_id}/reject")
async def reject_approval(
    approval_id: str,
    request: ApprovalActionRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict:
    """Reject an approval request.

    Only admin and auditor roles can reject.
    """
    # Check permissions - only admin and auditor can reject
    if current_user.role not in [UserRole.ADMIN, UserRole.AUDITOR]:
        raise HTTPException(
            status_code=403, detail="Only admin and auditor roles can reject requests"
        )

    # Get approval
    stmt = select(PlaybookApprovalModel).where(PlaybookApprovalModel.id == approval_id)
    result = await session.execute(stmt)
    approval = result.scalar_one_or_none()

    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")

    if approval.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Approval is not pending (current status: {approval.status})",
        )

    # Check if expired
    if approval.expires_at and approval.expires_at < datetime.now(UTC):
        approval.status = "expired"
        await session.commit()
        raise HTTPException(status_code=400, detail="Approval has expired")

    # Update approval
    approval.status = "rejected"
    approval.rejected_by_user_id = current_user.id
    approval.decided_at = datetime.now(UTC)
    approval.comments = request.comments

    # Audit log
    audit_repo = AuditRepository(session)
    await audit_repo.create(
        action="approval:reject",
        method="POST",
        path=f"/api/playbook/approvals/{approval_id}/reject",
        status_code=200,
        user_id=current_user.id,
        target_type="approval",
        target_id=approval_id,
        extra_json={
            "run_id": approval.run_id,
            "node_id": approval.node_id,
            "comments": request.comments,
        },
    )

    await session.commit()

    # Update node status to failed
    from models.playbook_node_run import PlaybookNodeRunModel

    stmt = select(PlaybookNodeRunModel).where(
        PlaybookNodeRunModel.run_id == approval.run_id,
        PlaybookNodeRunModel.node_id == approval.node_id,
    )
    result = await session.execute(stmt)
    node_run = result.scalar_one_or_none()

    if node_run:
        node_run.status = "failed"
        node_run.error_message = (
            f"Approval rejected: {request.comments or 'No reason provided'}"
        )
        node_run.finished_at = datetime.now(UTC)
        await session.commit()

    logger.info(
        f"[{approval.run_id}] Approval {approval_id} rejected by {current_user.username}"
    )

    return {
        "message": "Approval rejected",
        "approval_id": approval_id,
        "status": "rejected",
    }


@router.get("/approvals/pending/count")
async def get_pending_approvals_count(
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict:
    """Get count of pending approvals.

    - admin/auditor: count of all pending approvals
    - analyst: count of their own pending approvals
    """
    stmt = (
        select(func.count())
        .select_from(PlaybookApprovalModel)
        .where(PlaybookApprovalModel.status == "pending")
    )

    if current_user.role == UserRole.ANALYST:
        stmt = stmt.where(PlaybookApprovalModel.requested_by_user_id == current_user.id)

    result = await session.execute(stmt)
    count = result.scalar_one() or 0

    return {"count": count, "status": "pending"}
