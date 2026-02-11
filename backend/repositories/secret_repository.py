"""Secret Repository for database operations (v0.7.4)."""

from typing import Optional, List
from datetime import datetime, timezone

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from models.secret import SecretModel
from core.logger import get_logger

logger = get_logger(__name__)


class SecretRepository:
    """Repository for secret CRUD operations."""

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session.

        Args:
            session: Async database session
        """
        self.session = session

    async def create(
        self,
        name: str,
        encrypted_value: str,
        created_by_user_id: Optional[str] = None,
    ) -> SecretModel:
        """Create a new secret.

        Args:
            name: Unique secret name
            encrypted_value: Encrypted secret value
            created_by_user_id: User ID of creator

        Returns:
            Created SecretModel

        Raises:
            Exception: If secret name already exists
        """
        secret = SecretModel(
            name=name,
            encrypted_value=encrypted_value,
            created_by_user_id=created_by_user_id,
        )

        self.session.add(secret)
        await self.session.flush()

        logger.info(f"Created secret: {name}")
        return secret

    async def get_by_name(self, name: str) -> Optional[SecretModel]:
        """Get secret by name.

        Args:
            name: Secret name

        Returns:
            SecretModel or None if not found
        """
        stmt = select(SecretModel).where(SecretModel.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, secret_id: str) -> Optional[SecretModel]:
        """Get secret by ID.

        Args:
            secret_id: Secret ID

        Returns:
            SecretModel or None if not found
        """
        stmt = select(SecretModel).where(SecretModel.id == secret_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> List[SecretModel]:
        """List all secrets.

        Args:
            limit: Maximum number of secrets to return
            offset: Number of secrets to skip

        Returns:
            List of SecretModel
        """
        stmt = (
            select(SecretModel)
            .order_by(SecretModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count(self) -> int:
        """Count total number of secrets.

        Returns:
            Number of secrets
        """
        from sqlalchemy import func
        stmt = select(func.count(SecretModel.id))
        result = await self.session.execute(stmt)
        return result.scalar()

    async def update(
        self,
        name: str,
        encrypted_value: str,
    ) -> Optional[SecretModel]:
        """Update an existing secret's value.

        Args:
            name: Secret name
            encrypted_value: New encrypted value

        Returns:
            Updated SecretModel or None if not found
        """
        stmt = (
            update(SecretModel)
            .where(SecretModel.name == name)
            .values(
                encrypted_value=encrypted_value,
                updated_at=datetime.now(timezone.utc),
            )
            .returning(SecretModel)
        )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete(self, name: str) -> bool:
        """Delete a secret by name.

        Args:
            name: Secret name

        Returns:
            True if deleted, False if not found
        """
        stmt = delete(SecretModel).where(SecretModel.name == name)
        result = await self.session.execute(stmt)
        return result.rowcount > 0

    async def get_secret_names(self) -> List[str]:
        """Get list of all secret names.

        Returns:
            List of secret names
        """
        stmt = select(SecretModel.name).order_by(SecretModel.name)
        result = await self.session.execute(stmt)
        return [row[0] for row in result.all()]

    async def get_secrets_dict(self) -> dict[str, str]:
        """Get all secrets as a dictionary of name -> encrypted_value.

        Returns:
            Dictionary mapping secret names to encrypted values
        """
        stmt = select(SecretModel.name, SecretModel.encrypted_value)
        result = await self.session.execute(stmt)
        return {row[0]: row[1] for row in result.all()}
