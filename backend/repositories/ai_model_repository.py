"""Repository for AI model operations."""

from datetime import datetime

from sqlalchemy import and_, select
from sqlalchemy import update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession

from models.ai_model import AIModelModel
from models.ai_user_setting import AIUserSettingModel


class AIModelRepository:
    """Repository for AI model CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, model_id: str) -> AIModelModel | None:
        """Get model by ID."""
        result = await self.session.execute(
            select(AIModelModel).where(AIModelModel.id == model_id)
        )
        return result.scalar_one_or_none()

    async def list_enabled(
        self,
        provider: str | None = None,
    ) -> list[AIModelModel]:
        """List all enabled models."""
        conditions = [AIModelModel.enabled == True]
        if provider:
            conditions.append(AIModelModel.provider == provider)

        query = select(AIModelModel).where(and_(*conditions))
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def list_all(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[AIModelModel], int]:
        """List all models with pagination."""
        # Get total count
        count_result = await self.session.execute(select(AIModelModel.id))
        total = len(count_result.all())

        # Get paginated results
        query = (
            select(AIModelModel)
            .order_by(
                AIModelModel.is_default.desc(),
                AIModelModel.provider.asc(),
                AIModelModel.display_name.asc(),
            )
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        models = list(result.scalars().all())

        return models, total

    async def get_default_model(self) -> AIModelModel | None:
        """Get the default model."""
        result = await self.session.execute(
            select(AIModelModel).where(AIModelModel.is_default == True)
        )
        return result.scalar_one_or_none()

    async def set_default_model(self, model_id: str) -> bool:
        """Set a model as default (unsets others)."""
        # First, unset all defaults
        await self.session.execute(sql_update(AIModelModel).values(is_default=False))

        # Set new default
        model = await self.get_by_id(model_id)
        if not model:
            return False

        model.is_default = True
        model.updated_at = datetime.now().isoformat()
        self.session.add(model)
        await self.session.flush()
        return True

    async def create_model(
        self,
        id: str,
        provider: str,
        display_name: str,
        description: str | None = None,
        enabled: bool = True,
        capabilities: dict | None = None,
        max_tokens: int | None = None,
        config: dict | None = None,
    ) -> AIModelModel:
        """Create a new model."""
        model = AIModelModel(
            id=id,
            provider=provider,
            display_name=display_name,
            description=description,
            enabled=enabled,
            capabilities=capabilities,
            max_tokens=max_tokens,
            config=config,
        )
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return model

    async def update_model(
        self,
        model_id: str,
        display_name: str | None = None,
        description: str | None = None,
        enabled: bool | None = None,
        capabilities: dict | None = None,
        max_tokens: int | None = None,
        config: dict | None = None,
    ) -> AIModelModel | None:
        """Update a model."""
        model = await self.get_by_id(model_id)
        if not model:
            return None

        if display_name is not None:
            model.display_name = display_name
        if description is not None:
            model.description = description
        if enabled is not None:
            model.enabled = enabled
        if capabilities is not None:
            model.capabilities = capabilities
        if max_tokens is not None:
            model.max_tokens = max_tokens
        if config is not None:
            model.config = config

        model.updated_at = datetime.now().isoformat()
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return model


class AIUserSettingRepository:
    """Repository for user AI settings."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_user_id(self, user_id: str) -> AIUserSettingModel | None:
        """Get user's AI settings."""
        result = await self.session.execute(
            select(AIUserSettingModel).where(AIUserSettingModel.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create(self, user_id: str) -> AIUserSettingModel:
        """Get user's settings or create if not exists."""
        settings = await self.get_by_user_id(user_id)
        if not settings:
            settings = AIUserSettingModel(user_id=user_id)
            self.session.add(settings)
            await self.session.flush()
            await self.session.refresh(settings)
        return settings

    async def set_default_model(
        self, user_id: str, model_id: str
    ) -> AIUserSettingModel:
        """Set user's default model."""
        settings = await self.get_or_create(user_id)
        settings.default_model_id = model_id
        settings.updated_at = datetime.now().isoformat()
        self.session.add(settings)
        await self.session.flush()
        await self.session.refresh(settings)
        return settings

    async def get_default_model(self, user_id: str) -> str | None:
        """Get user's default model ID."""
        settings = await self.get_by_user_id(user_id)
        return settings.default_model_id if settings else None
