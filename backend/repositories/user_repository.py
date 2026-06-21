"""Repository for user operations."""

from datetime import UTC, datetime

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import UserModel, UserRole


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

    async def get_by_id(self, user_id: str) -> UserModel | None:
        """Get user by ID."""
        result = await self.session.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> UserModel | None:
        """Get user by username."""
        result = await self.session.execute(
            select(UserModel).where(UserModel.username == username)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> UserModel | None:
        """Get user by email."""
        result = await self.session.execute(
            select(UserModel).where(UserModel.email == email)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        role: UserRole | None = None,
        is_active: bool | None = None,
        search: str | None = None,
    ) -> tuple[list[UserModel], int]:
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
            select(UserModel.id).where(and_(*conditions))
            if conditions
            else select(UserModel.id)
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
        role: UserRole | None = None,
        is_active: bool | None = None,
    ) -> UserModel | None:
        """Update user fields and refresh updated_at for token invalidation."""
        user = await self.get_by_id(user_id)
        if not user:
            return None

        if role is not None:
            user.role = role
        if is_active is not None:
            user.is_active = is_active

        user.updated_at = datetime.now(UTC).isoformat()

        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def update_last_login(self, user_id: str) -> None:
        """Update user's last login timestamp."""
        user = await self.get_by_id(user_id)
        if user:
            user.last_login_at = datetime.now(UTC).isoformat()
            self.session.add(user)
            await self.session.flush()

    async def update_password(self, user_id: str, hashed_password: str) -> bool:
        """Update user's password and clear must_change_password flag.

        P1-19: Saves previous password to history (retains last 5 entries)
        to prevent reuse.
        """
        user = await self.get_by_id(user_id)
        if not user:
            return False

        # Save current password to history before updating
        if user.hashed_password:
            history = user.password_history or []
            history.insert(
                0,
                {
                    "hashed_password": user.hashed_password,
                    "changed_at": datetime.now(UTC).isoformat(),
                },
            )
            # Retain only the last 5 entries
            user.password_history = history[:5]

        user.hashed_password = hashed_password
        user.must_change_password = False
        user.password_changed_at = datetime.now(UTC).isoformat()
        self.session.add(user)
        await self.session.flush()
        return True

    async def delete(self, user_id: str) -> bool:
        """Soft delete (disable) a user and update timestamp for token invalidation."""
        user = await self.get_by_id(user_id)
        if not user:
            return False
        user.is_active = False
        user.updated_at = datetime.now(UTC).isoformat()
        self.session.add(user)
        await self.session.flush()
        return True

    async def count(self) -> int:
        """Get total user count."""
        result = await self.session.execute(select(UserModel.id))
        return len(result.all())
