"""Repository for API key operations."""

from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from models.api_key import APIKeyModel
from core.security import hash_api_key, generate_api_key, get_api_key_prefix


class APIKeyRepository:
    """Repository for API key CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        user_id: str,
        description: str,
        expires_in_days: Optional[int] = None,
    ) -> tuple[str, APIKeyModel]:
        """Create a new API key. Returns (plain_key, api_key_model)."""
        plain_key = generate_api_key()
        key_hash = hash_api_key(plain_key)
        key_prefix = get_api_key_prefix(plain_key)

        expires_at = None
        if expires_in_days:
            expires_at = (datetime.now() + timedelta(days=expires_in_days)).isoformat()

        api_key = APIKeyModel(
            user_id=user_id,
            key_hash=key_hash,
            key_prefix=key_prefix,
            description=description,
            expires_at=expires_at,
        )
        self.session.add(api_key)
        await self.session.flush()
        await self.session.refresh(api_key)

        return plain_key, api_key

    async def get_by_id(self, api_key_id: str) -> Optional[APIKeyModel]:
        """Get API key by ID."""
        result = await self.session.execute(
            select(APIKeyModel).where(APIKeyModel.id == api_key_id)
        )
        return result.scalar_one_or_none()

    async def get_by_hash(self, key_hash: str) -> Optional[APIKeyModel]:
        """Get API key by hash."""
        result = await self.session.execute(
            select(APIKeyModel).where(APIKeyModel.key_hash == key_hash)
        )
        return result.scalar_one_or_none()

    async def list_by_user(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 50,
        is_active: Optional[bool] = None,
    ) -> tuple[List[APIKeyModel], int]:
        """List API keys for a user."""
        query = select(APIKeyModel).where(APIKeyModel.user_id == user_id)

        if is_active is not None:
            query = query.where(APIKeyModel.is_active == is_active)

        # Get total count
        count_result = await self.session.execute(
            select(APIKeyModel.id)
            .where(APIKeyModel.user_id == user_id)
            .where(APIKeyModel.is_active == is_active if is_active is not None else True)
        )
        total = len(count_result.all())

        # Get paginated results
        query = query.order_by(APIKeyModel.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        api_keys = list(result.scalars().all())

        return api_keys, total

    async def update(
        self,
        api_key_id: str,
        description: Optional[str] = None,
        is_active: Optional[bool] = None,
        expires_at: Optional[str] = None,
    ) -> Optional[APIKeyModel]:
        """Update API key fields."""
        api_key = await self.get_by_id(api_key_id)
        if not api_key:
            return None

        if description is not None:
            api_key.description = description
        if is_active is not None:
            api_key.is_active = is_active
        if expires_at is not None:
            api_key.expires_at = expires_at

        self.session.add(api_key)
        await self.session.flush()
        await self.session.refresh(api_key)
        return api_key

    async def update_last_used(self, api_key_id: str) -> None:
        """Update API key's last used timestamp."""
        api_key = await self.get_by_id(api_key_id)
        if api_key:
            api_key.last_used_at = datetime.now().isoformat()
            self.session.add(api_key)
            await self.session.flush()

    async def delete(self, api_key_id: str) -> bool:
        """Delete (deactivate) an API key."""
        api_key = await self.get_by_id(api_key_id)
        if not api_key:
            return False
        api_key.is_active = False
        self.session.add(api_key)
        await self.session.flush()
        return True

    async def cleanup_expired(self) -> int:
        """Deactivate all expired API keys. Returns count of deactivated keys."""
        now = datetime.now().isoformat()
        result = await self.session.execute(
            select(APIKeyModel).where(
                and_(
                    APIKeyModel.is_active == True,
                    APIKeyModel.expires_at.isnot(None),
                    APIKeyModel.expires_at < now,
                )
            )
        )
        expired_keys = list(result.scalars().all())

        for key in expired_keys:
            key.is_active = False
            self.session.add(key)

        await self.session.flush()
        return len(expired_keys)
