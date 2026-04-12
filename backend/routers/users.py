"""User management API endpoints (admin only)."""


from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from core.security import get_password_hash
from db.session import get_session
from dependencies.auth import invalidate_user_permission_cache, require_admin
from models.user import UserModel, UserRole
from repositories.user_repository import UserRepository
from schemas.user import (
    PasswordResetRequest,
    UserCreate,
    UserResponse,
    UserUpdate,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/api/users", tags=["Users"])


@router.get("", response_model=dict[str, list[UserResponse] | int])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    role: UserRole = None,
    is_active: bool = None,
    search: str = None,
    current_user: UserModel = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """List all users (admin only)."""
    user_repo = UserRepository(session)
    users, total = await user_repo.list(
        skip=skip,
        limit=limit,
        role=role,
        is_active=is_active,
        search=search,
    )

    # Convert to response format
    response_users = []
    for user in users:
        from dependencies.auth import user_to_response

        response_users.append(user_to_response(user))

    return {"items": response_users, "total": total}


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    current_user: UserModel = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Create a new user (admin only)."""
    user_repo = UserRepository(session)

    # Check if username exists
    if await user_repo.get_by_username(user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists",
        )

    # Check if email exists
    if await user_repo.get_by_email(user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists",
        )

    # Create user
    hashed_password = get_password_hash(user_data.password)
    user = await user_repo.create(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        role=user_data.role,
    )

    # Create audit log
    from repositories.audit_repository import AuditRepository

    audit_repo = AuditRepository(session)
    await audit_repo.create(
        action="user:create",
        method="POST",
        path="/api/users",
        status_code=201,
        user_id=current_user.id,
        target_type="user",
        target_id=user.id,
        extra_json={
            "created_username": user.username,
            "created_email": user.email,
            "created_role": user.role,
        },
    )
    await session.commit()

    from dependencies.auth import user_to_response

    return user_to_response(user)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: UserModel = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Get user by ID (admin only)."""
    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    from dependencies.auth import user_to_response

    return user_to_response(user)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    current_user: UserModel = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Update user (admin only)."""
    user_repo = UserRepository(session)
    user = await user_repo.update(
        user_id,
        role=user_data.role,
        is_active=user_data.is_active,
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Invalidate permission cache if role was changed
    if user_data.role is not None:
        invalidate_user_permission_cache(user_id)

    # Create audit log
    from repositories.audit_repository import AuditRepository

    audit_repo = AuditRepository(session)
    await audit_repo.create(
        action="user:update",
        method="PATCH",
        path=f"/api/users/{user_id}",
        status_code=200,
        user_id=current_user.id,
        target_type="user",
        target_id=user_id,
        extra_json={
            "updated_fields": user_data.model_dump(exclude_unset=True),
        },
    )
    await session.commit()

    from dependencies.auth import user_to_response

    return user_to_response(user)


@router.post("/{user_id}/reset-password")
async def reset_user_password(
    user_id: str,
    request: PasswordResetRequest,
    current_user: UserModel = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Reset user password (admin only)."""
    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Hash and update password
    hashed_password = get_password_hash(request.new_password)
    await user_repo.update_password(user_id, hashed_password)

    # Create audit log
    from repositories.audit_repository import AuditRepository

    audit_repo = AuditRepository(session)
    await audit_repo.create(
        action="user:reset_password",
        method="POST",
        path=f"/api/users/{user_id}/reset-password",
        status_code=200,
        user_id=current_user.id,
        target_type="user",
        target_id=user_id,
    )
    await session.commit()

    return {"message": "Password reset successfully"}


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    current_user: UserModel = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Disable (soft delete) a user (admin only)."""
    user_repo = UserRepository(session)

    # Prevent deleting yourself
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot disable your own account",
        )

    success = await user_repo.delete(user_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Invalidate permission cache for deleted user
    invalidate_user_permission_cache(user_id)

    # Create audit log
    from repositories.audit_repository import AuditRepository

    audit_repo = AuditRepository(session)
    await audit_repo.create(
        action="user:delete",
        method="DELETE",
        path=f"/api/users/{user_id}",
        status_code=200,
        user_id=current_user.id,
        target_type="user",
        target_id=user_id,
    )
    await session.commit()

    return {"message": "User disabled successfully"}
