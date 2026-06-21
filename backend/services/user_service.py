"""User management service — business logic for CRUD, password reset, and user administration."""

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from core.security import check_password_history, get_password_hash
from models.user import UserModel, UserRole
from repositories.audit_repository import AuditRepository
from repositories.user_repository import UserRepository
from schemas.user import PasswordResetRequest, UserCreate, UserUpdate
from services.base import BaseService

logger = get_logger(__name__)


class UserService(BaseService):
    """User management service handling CRUD, password reset, and administrative operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.user_repo = UserRepository(session)
        self.audit_repo = AuditRepository(session)

    async def list_users(
        self,
        skip: int = 0,
        limit: int = 50,
        role: UserRole | None = None,
        is_active: bool | None = None,
        search: str | None = None,
    ) -> tuple[list[UserModel], int]:
        """List users with optional filters and pagination."""
        return await self.user_repo.list(
            skip=skip,
            limit=limit,
            role=role,
            is_active=is_active,
            search=search,
        )

    async def create_user(self, admin_id: str, user_data: UserCreate) -> UserModel:
        """Create a new user (admin only)."""
        # Check if username exists
        if await self.user_repo.get_by_username(user_data.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists",
            )

        # Check if email exists
        if await self.user_repo.get_by_email(user_data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists",
            )

        # Create user
        hashed_password = get_password_hash(user_data.password)
        user = await self.user_repo.create(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password,
            role=user_data.role,
        )

        # Create audit log
        await self.audit_repo.create(
            action="user:create",
            method="POST",
            path="/api/users",
            status_code=201,
            user_id=admin_id,
            target_type="user",
            target_id=user.id,
            extra_json={
                "created_username": user.username,
                "created_email": user.email,
                "created_role": user.role,
            },
        )
        await self.commit()

        return user

    async def get_user(self, user_id: str) -> UserModel:
        """Get user by ID."""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return user

    async def update_user(
        self, admin_id: str, user_id: str, user_data: UserUpdate
    ) -> UserModel:
        """Update user fields (admin only)."""
        user = await self.user_repo.update(
            user_id,
            role=user_data.role,
            is_active=user_data.is_active,
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Create audit log
        await self.audit_repo.create(
            action="user:update",
            method="PATCH",
            path=f"/api/users/{user_id}",
            status_code=200,
            user_id=admin_id,
            target_type="user",
            target_id=user_id,
            extra_json={
                "updated_fields": user_data.model_dump(exclude_unset=True),
            },
        )
        await self.commit()

        return user

    async def reset_password(
        self, admin_id: str, user_id: str, request: PasswordResetRequest
    ) -> None:
        """Reset user password (admin only)."""
        user = await self.user_repo.get_by_id(user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # P1-19: Check password history to prevent reuse
        if check_password_history(request.new_password, user.password_history):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot reuse recent passwords",
            )

        # Hash and update password
        hashed_password = get_password_hash(request.new_password)
        await self.user_repo.update_password(user_id, hashed_password)

        # Create audit log
        await self.audit_repo.create(
            action="user:reset_password",
            method="POST",
            path=f"/api/users/{user_id}/reset-password",
            status_code=200,
            user_id=admin_id,
            target_type="user",
            target_id=user_id,
        )
        await self.commit()

    async def delete_user(self, admin_id: str, user_id: str) -> None:
        """Disable (soft delete) a user (admin only)."""
        # Prevent deleting yourself
        if user_id == admin_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot disable your own account",
            )

        success = await self.user_repo.delete(user_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Create audit log
        await self.audit_repo.create(
            action="user:delete",
            method="DELETE",
            path=f"/api/users/{user_id}",
            status_code=200,
            user_id=admin_id,
            target_type="user",
            target_id=user_id,
        )
        await self.commit()
