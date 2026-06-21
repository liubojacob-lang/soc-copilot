"""Prompt Registry repository."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.prompt_registry import PromptEnvironment, PromptRegistryModel
from repositories.base import BaseRepository


class PromptRegistryRepository(BaseRepository[PromptRegistryModel]):
    """Repository for prompt registry operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, PromptRegistryModel)

    async def get_by_name_version_env(
        self, name: str, version: str, environment: str
    ) -> PromptRegistryModel | None:
        """Get prompt by name, version and environment."""
        result = await self.session.execute(
            select(PromptRegistryModel).where(
                PromptRegistryModel.name == name,
                PromptRegistryModel.version == version,
                PromptRegistryModel.environment == environment,
            )
        )
        return result.scalar_one_or_none()

    async def get_active_by_name_env(
        self, name: str, environment: str
    ) -> PromptRegistryModel | None:
        """Get active prompt by name and environment."""
        result = await self.session.execute(
            select(PromptRegistryModel).where(
                PromptRegistryModel.name == name,
                PromptRegistryModel.environment == environment,
                PromptRegistryModel.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def list_by_environment(
        self,
        environment: str,
        name: str | None = None,
        is_active: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PromptRegistryModel]:
        """List prompts filtered by environment."""
        query = select(PromptRegistryModel).where(
            PromptRegistryModel.environment == environment
        )

        if name:
            query = query.where(PromptRegistryModel.name == name)
        if is_active is not None:
            query = query.where(PromptRegistryModel.is_active.is_(is_active))

        query = (
            query.order_by(
                PromptRegistryModel.name.asc(),
                PromptRegistryModel.created_at.desc(),
            )
            .limit(limit)
            .offset(offset)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def list_all_versions(
        self, name: str, environment: str
    ) -> list[PromptRegistryModel]:
        """List all versions of a prompt in an environment."""
        result = await self.session.execute(
            select(PromptRegistryModel)
            .where(
                PromptRegistryModel.name == name,
                PromptRegistryModel.environment == environment,
            )
            .order_by(PromptRegistryModel.created_at.desc())
        )
        return list(result.scalars().all())

    async def activate_version(
        self, name: str, version: str, environment: str
    ) -> PromptRegistryModel | None:
        """Activate a specific version and deactivate others."""
        # Deactivate all versions for this name+env
        await self.bulk_update(
            filters={
                "name": name,
                "environment": environment,
            },
            is_active=False,
        )

        # Activate target version
        target = await self.get_by_name_version_env(name, version, environment)
        if target:
            target.is_active = True
            await self.session.flush()
            await self.session.refresh(target)

        return target
