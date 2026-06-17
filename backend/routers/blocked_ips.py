"""Blocked IPs router for IP/domain blocking API."""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from db.session import get_session
from dependencies.auth import get_current_user
from models.blocked_ip import BlockedIP
from models.user import UserModel
from schemas.blocked_ip import (
    BlockedIPListResponse,
    BlockedIPResponse,
    BlockedIPUpdate,
    BlockIPRequest,
)

router = APIRouter(prefix="/api/blocked-ips", tags=["blocked-ips"])
logger = get_logger(__name__)


@router.post("", response_model=BlockedIPResponse, status_code=status.HTTP_201_CREATED)
async def block_ip(
    data: BlockIPRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> BlockedIPResponse:
    """Block an IP address or domain."""
    try:
        # Check if already blocked
        existing = await session.execute(
            select(BlockedIP).where(
                BlockedIP.value == data.value,
                BlockedIP.is_active == True,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{data.value} is already blocked",
            )

        # Calculate expiration
        expires_at = None
        if data.expires_in_hours:
            expires_at = datetime.now(datetime.UTC) + timedelta(hours=data.expires_in_hours)

        blocked = BlockedIP(
            value=data.value,
            type=data.type,
            reason=data.reason,
            source="manual",
            created_by=current_user.username,
            alert_id=data.alert_id,
            expires_at=expires_at,
            is_active=True,
        )
        session.add(blocked)
        await session.commit()
        await session.refresh(blocked)

        logger.info(f"Blocked {data.type} {data.value} by {current_user.username}")
        return BlockedIPResponse.model_validate(blocked)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to block IP: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to block IP",
        )


@router.get("", response_model=BlockedIPListResponse)
async def list_blocked_ips(
    type: str | None = Query(
        None, description="Filter by type: ip, domain, url, hash"
    ),
    is_active: bool | None = Query(None, description="Filter by active status"),
    limit: int = Query(50, ge=1, le=500, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> BlockedIPListResponse:
    """List blocked IPs with optional filters."""
    try:
        query = select(BlockedIP)

        if type:
            query = query.where(BlockedIP.type == type)
        if is_active is not None:
            query = query.where(BlockedIP.is_active == is_active)

        # Get total count
        count_query = select(select(BlockedIP).subquery().c.id)
        if type:
            count_query = count_query.where(BlockedIP.type == type)
        if is_active is not None:
            count_query = count_query.where(BlockedIP.is_active == is_active)

        total_result = await session.execute(count_query)
        total = len(total_result.all())

        # Get items
        query = query.order_by(desc(BlockedIP.created_at)).offset(offset).limit(limit)
        result = await session.execute(query)
        items = result.scalars().all()

        return BlockedIPListResponse(
            items=[BlockedIPResponse.model_validate(item) for item in items],
            total=total,
        )
    except Exception as e:
        logger.error(f"Failed to list blocked IPs: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list blocked IPs",
        )


@router.get("/{blocked_id}", response_model=BlockedIPResponse)
async def get_blocked_ip(
    blocked_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> BlockedIPResponse:
    """Get a blocked IP by ID."""
    result = await session.execute(select(BlockedIP).where(BlockedIP.id == blocked_id))
    blocked = result.scalar_one_or_none()

    if not blocked:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blocked IP not found",
        )

    return BlockedIPResponse.model_validate(blocked)


@router.patch("/{blocked_id}", response_model=BlockedIPResponse)
async def update_blocked_ip(
    blocked_id: str,
    data: BlockedIPUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> BlockedIPResponse:
    """Update a blocked IP (reason, expiration, etc.)."""
    try:
        result = await session.execute(
            select(BlockedIP).where(BlockedIP.id == blocked_id)
        )
        blocked = result.scalar_one_or_none()

        if not blocked:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Blocked IP not found",
            )

        if data.reason is not None:
            blocked.reason = data.reason
        if data.expires_at is not None:
            blocked.expires_at = data.expires_at

        await session.commit()
        await session.refresh(blocked)

        return BlockedIPResponse.model_validate(blocked)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update blocked IP: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update blocked IP",
        )


@router.delete("/{blocked_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unblock_ip(
    blocked_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> None:
    """Unblock an IP (soft delete - mark as inactive)."""
    try:
        result = await session.execute(
            select(BlockedIP).where(BlockedIP.id == blocked_id)
        )
        blocked = result.scalar_one_or_none()

        if not blocked:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Blocked IP not found",
            )

        blocked.is_active = False
        blocked.deactivated_at = datetime.now(datetime.UTC)
        blocked.deactivated_by = current_user.username

        await session.commit()

        logger.info(f"Unblocked {blocked.value} by {current_user.username}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to unblock IP: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unblock IP",
        )


@router.post("/check")
async def check_if_blocked(
    value: str,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict:
    """Check if an IP/domain is currently blocked."""
    try:
        result = await session.execute(
            select(BlockedIP).where(
                BlockedIP.value == value,
                BlockedIP.is_active == True,
            )
        )
        blocked = result.scalar_one_or_none()

        if blocked and blocked.expires_at and blocked.expires_at < datetime.now(datetime.UTC):
            # Expired, update status
            blocked.is_active = False
            await session.commit()
            blocked = None

        return {
            "value": value,
            "is_blocked": blocked is not None,
            "details": BlockedIPResponse.model_validate(blocked) if blocked else None,
        }
    except Exception as e:
        logger.error(f"Failed to check blocked status: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check blocked status",
        )
