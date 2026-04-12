"""API Key management endpoints."""


from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from db.session import get_session
from dependencies.auth import get_current_user, require_admin
from models.api_key import APIKeyModel
from models.user import UserModel
from repositories.api_key_repository import APIKeyRepository
from schemas.api_key import (
    APIKeyCreate,
    APIKeyCreateResponse,
    APIKeyResponse,
    APIKeyUpdate,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/api/api-keys", tags=["API Keys"])


@router.get("", response_model=dict[str, list[APIKeyResponse] | int])
async def list_api_keys(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    is_active: bool = None,
    current_user: UserModel = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """List current user's API keys."""
    api_key_repo = APIKeyRepository(session)
    api_keys, total = await api_key_repo.list_by_user(
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        is_active=is_active,
    )

    # Convert to response format
    response_keys = []
    for key in api_keys:
        response_keys.append(
            APIKeyResponse(
                id=key.id,
                user_id=key.user_id,
                key_prefix=key.key_prefix,
                description=key.description,
                is_active=key.is_active,
                created_at=key.created_at,
                last_used_at=key.last_used_at,
                expires_at=key.expires_at,
            )
        )

    return {"items": response_keys, "total": total}


@router.post(
    "", response_model=APIKeyCreateResponse, status_code=status.HTTP_201_CREATED
)
async def create_api_key(
    key_data: APIKeyCreate,
    current_user: UserModel = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Create a new API key."""
    api_key_repo = APIKeyRepository(session)

    # Create the key
    plain_key, api_key = await api_key_repo.create(
        user_id=current_user.id,
        description=key_data.description,
        expires_in_days=key_data.expires_in_days,
    )

    # Create audit log
    from repositories.audit_repository import AuditRepository

    audit_repo = AuditRepository(session)
    await audit_repo.create(
        action="api_key:create",
        method="POST",
        path="/api/api-keys",
        status_code=201,
        user_id=current_user.id,
        target_type="api_key",
        target_id=api_key.id,
        extra_json={
            "description": key_data.description,
            "expires_in_days": key_data.expires_in_days,
        },
    )
    await session.commit()

    # Return with the plain key (only shown once)
    return APIKeyCreateResponse(
        key=plain_key,
        api_key=APIKeyResponse(
            id=api_key.id,
            user_id=api_key.user_id,
            key_prefix=api_key.key_prefix,
            description=api_key.description,
            is_active=api_key.is_active,
            created_at=api_key.created_at,
            last_used_at=api_key.last_used_at,
            expires_at=api_key.expires_at,
        ),
    )


@router.patch("/{api_key_id}", response_model=APIKeyResponse)
async def update_api_key(
    api_key_id: str,
    key_data: APIKeyUpdate,
    current_user: UserModel = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Update an API key (description, active status, expiration)."""
    api_key_repo = APIKeyRepository(session)

    # Get the key
    api_key = await api_key_repo.get_by_id(api_key_id)
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    # Check ownership
    if api_key.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not your API key",
        )

    # Update
    updated = await api_key_repo.update(
        api_key_id,
        description=key_data.description,
        is_active=key_data.is_active,
        expires_at=key_data.expires_at,
    )

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    # Create audit log
    from repositories.audit_repository import AuditRepository

    audit_repo = AuditRepository(session)
    await audit_repo.create(
        action="api_key:update",
        method="PATCH",
        path=f"/api/api-keys/{api_key_id}",
        status_code=200,
        user_id=current_user.id,
        target_type="api_key",
        target_id=api_key_id,
        extra_json={
            "updated_fields": key_data.model_dump(exclude_unset=True),
        },
    )
    await session.commit()

    return APIKeyResponse(
        id=updated.id,
        user_id=updated.user_id,
        key_prefix=updated.key_prefix,
        description=updated.description,
        is_active=updated.is_active,
        created_at=updated.created_at,
        last_used_at=updated.last_used_at,
        expires_at=updated.expires_at,
    )


@router.delete("/{api_key_id}")
async def delete_api_key(
    api_key_id: str,
    current_user: UserModel = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Disable (delete) an API key."""
    api_key_repo = APIKeyRepository(session)

    # Get the key
    api_key = await api_key_repo.get_by_id(api_key_id)
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    # Check ownership
    if api_key.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not your API key",
        )

    # Delete
    success = await api_key_repo.delete(api_key_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    # Create audit log
    from repositories.audit_repository import AuditRepository

    audit_repo = AuditRepository(session)
    await audit_repo.create(
        action="api_key:delete",
        method="DELETE",
        path=f"/api/api-keys/{api_key_id}",
        status_code=200,
        user_id=current_user.id,
        target_type="api_key",
        target_id=api_key_id,
    )
    await session.commit()

    return {"message": "API key disabled successfully"}


@router.get("/admin/all", response_model=dict[str, list[APIKeyResponse] | int])
async def list_all_api_keys(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user_id: str = None,
    current_user: UserModel = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """List all API keys (admin only)."""
    from sqlalchemy import select

    query = select(APIKeyModel)
    if user_id:
        query = query.where(APIKeyModel.user_id == user_id)

    # Get total
    from sqlalchemy import func

    count_query = select(func.count(APIKeyModel.id))
    if user_id:
        count_query = count_query.where(APIKeyModel.user_id == user_id)
    count_result = await session.execute(count_query)
    total = count_result.scalar_one()

    # Get paginated
    query = query.order_by(APIKeyModel.created_at.desc()).offset(skip).limit(limit)
    result = await session.execute(query)
    api_keys = list(result.scalars().all())

    # Convert to response
    response_keys = []
    for key in api_keys:
        response_keys.append(
            APIKeyResponse(
                id=key.id,
                user_id=key.user_id,
                key_prefix=key.key_prefix,
                description=key.description,
                is_active=key.is_active,
                created_at=key.created_at,
                last_used_at=key.last_used_at,
                expires_at=key.expires_at,
            )
        )

    return {"items": response_keys, "total": total}
