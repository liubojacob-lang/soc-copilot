"""Repository for user operations."""

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from models.user import UserModel, UserRole
from core.security import get_password_hash


class UserRepository:
    """Repository for user CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        username: str,
        email: str,
        hashed_password: str,
        role: UserRole = UserRole.ANALYST,
        must_change_password: bool = False,
    ) -> UserModel:
        """Create a new user."""
        user = UserModel(
            username=username,
            email=email,
            hashed_password=hashed_password,
            role=role,
            must_change_password=must_change_password,
        )
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def get_by_id(self, user_id: str) -> Optional[UserModel]:
        """Get user by ID."""
        result = await self.session.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> Optional[UserModel]:
        """Get user by username."""
        result = await self.session.execute(
            select(UserModel).where(UserModel.username == username)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[UserModel]:
        """Get user by email."""
        result = await self.session.execute(
            select(UserModel).where(UserModel.email == email)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        role: Optional[UserRole] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> tuple[List[UserModel], int]:
        """List users with optional filters."""
        query = select(UserModel)

        conditions = []
        if role:
            conditions.append(UserModel.role == role)
        if is_active is not None:
            conditions.append(UserModel.is_active == is_active)
        if search:
            search_pattern = f"%{search}%"
            conditions.append(
                or_(
                    UserModel.username.ilike(search_pattern),
                    UserModel.email.ilike(search_pattern),
                )
            )

        if conditions:
            query = query.where(and_(*conditions))

        # Get total count
        count_result = await self.session.execute(
            select(UserModel.id).where(and_(*conditions)) if conditions else select(UserModel.id)
        )
        total = len(count_result.all())

        # Get paginated results
        query = query.order_by(UserModel.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        users = list(result.scalars().all())

        return users, total

    async def update(
        self,
        user_id: str,
        role: Optional[UserRole] = None,
        is_active: Optional[bool] = None,
    ) -> Optional[UserModel]:
        """Update user fields."""
        user = await self.get_by_id(user_id)
        if not user:
            return None

        if role is not None:
            user.role = role
        if is_active is not None:
            user.is_active = is_active

        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def update_last_login(self, user_id: str) -> None:
        """Update user's last login timestamp."""
        from datetime import datetime
        user = await self.get_by_id(user_id)
        if user:
            user.last_login_at = datetime.now().isoformat()
            self.session.add(user)
            await self.session.flush()

    async def update_password(self, user_id: str, hashed_password: str) -> bool:
        """Update user's password and clear must_change_password flag."""
        from datetime import datetime
        user = await self.get_by_id(user_id)
        if not user:
            return False
        user.hashed_password = hashed_password
        user.must_change_password = False  # Clear flag after password change
        user.password_changed_at = datetime.now().isoformat()
        self.session.add(user)
        await self.session.flush()
        return True

    async def delete(self, user_id: str) -> bool:
        """Soft delete (disable) a user."""
        user = await self.get_by_id(user_id)
        if not user:
            return False
        user.is_active = False
        self.session.add(user)
        await self.session.flush()
        return True

    async def count(self) -> int:
        """Get total user count."""
        result = await self.session.execute(select(UserModel.id))
        return len(result.all())
