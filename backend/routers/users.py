"""User management API endpoints (admin only)."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from db.session import get_session
from dependencies.auth import invalidate_user_permission_cache, require_admin
from models.user import UserModel, UserRole
from schemas.user import (
    PasswordResetRequest,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from services.user_service import UserService

logger = get_logger(__name__)

router = APIRouter(prefix="/api/users", tags=["Users"])


def get_user_service(session: AsyncSession = Depends(get_session)) -> UserService:
    """Dependency: provide UserService instance."""
    return UserService(session)


@router.get("", response_model=dict[str, list[UserResponse] | int])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    role: UserRole = None,
    is_active: bool = None,
    search: str = None,
    current_user: UserModel = Depends(require_admin),
    user_service: UserService = Depends(get_user_service),
):
    """List all users (admin only)."""
    users, total = await user_service.list_users(
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
    user_service: UserService = Depends(get_user_service),
):
    """Create a new user (admin only)."""
    user = await user_service.create_user(
        admin_id=current_user.id,
        user_data=user_data,
    )

    from dependencies.auth import user_to_response

    return user_to_response(user)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: UserModel = Depends(require_admin),
    user_service: UserService = Depends(get_user_service),
):
    """Get user by ID (admin only)."""
    user = await user_service.get_user(user_id)

    from dependencies.auth import user_to_response

    return user_to_response(user)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    current_user: UserModel = Depends(require_admin),
    user_service: UserService = Depends(get_user_service),
):
    """Update user (admin only)."""
    user = await user_service.update_user(
        admin_id=current_user.id,
        user_id=user_id,
        user_data=user_data,
    )

    # Invalidate permission cache if role was changed
    if user_data.role is not None:
        invalidate_user_permission_cache(user_id)

    from dependencies.auth import user_to_response

    return user_to_response(user)


@router.post("/{user_id}/reset-password")
async def reset_user_password(
    user_id: str,
    request: PasswordResetRequest,
    current_user: UserModel = Depends(require_admin),
    user_service: UserService = Depends(get_user_service),
):
    """Reset user password (admin only)."""
    await user_service.reset_password(
        admin_id=current_user.id,
        user_id=user_id,
        request=request,
    )
    return {"message": "Password reset successfully"}


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    current_user: UserModel = Depends(require_admin),
    user_service: UserService = Depends(get_user_service),
):
    """Disable (soft delete) a user (admin only)."""
    await user_service.delete_user(
        admin_id=current_user.id,
        user_id=user_id,
    )

    # Invalidate permission cache for deleted user
    invalidate_user_permission_cache(user_id)

    return {"message": "User disabled successfully"}
