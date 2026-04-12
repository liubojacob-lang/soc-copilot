"""Repository for playbook definitions."""

import uuid
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from models.playbook_definition import PlaybookDefinitionModel
from models.playbook_run import PlaybookRunModel

logger = get_logger(__name__)


class PlaybookDefinitionRepository:
    """Repository for playbook definition CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        name: str,
        dag_json: dict[str, Any],
        version: str = "1.0.0",
        description: str | None = None,
        created_by_user_id: str | None = None,
        is_active: bool = True,
    ) -> PlaybookDefinitionModel:
        """Create a new playbook definition."""
        definition = PlaybookDefinitionModel(
            id=str(uuid.uuid4()),
            name=name,
            version=version,
            description=description,
            dag_json=dag_json,  # Uses the dag_json property setter
            created_by=created_by_user_id,  # Model uses created_by not created_by_user_id
            is_active=is_active,
        )
        self.session.add(definition)
        await self.session.flush()
        await self.session.refresh(definition)
        logger.info(f"Created playbook definition: {definition.id} - {name}")
        return definition

    async def get_by_id(self, definition_id: str) -> PlaybookDefinitionModel | None:
        """Get playbook definition by ID."""
        stmt = select(PlaybookDefinitionModel).where(
            PlaybookDefinitionModel.id == definition_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> PlaybookDefinitionModel | None:
        """Get playbook definition by name."""
        stmt = select(PlaybookDefinitionModel).where(
            PlaybookDefinitionModel.name == name
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_definitions(
        self,
        is_active: bool | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[PlaybookDefinitionModel], int]:
        """List playbook definitions with pagination."""
        # Build base query
        stmt = select(PlaybookDefinitionModel)

        # Apply filters
        if is_active is not None:
            stmt = stmt.where(PlaybookDefinitionModel.is_active == is_active)

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar() or 0

        # Apply pagination and ordering
        stmt = stmt.order_by(PlaybookDefinitionModel.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await self.session.execute(stmt)
        items = list(result.scalars().all())

        return items, total

    async def update(
        self,
        definition_id: str,
        name: str | None = None,
        version: str | None = None,
        description: str | None = None,
        dag_json: dict[str, Any] | None = None,
        is_active: bool | None = None,
    ) -> PlaybookDefinitionModel | None:
        """Update a playbook definition."""
        # Get existing definition
        definition = await self.get_by_id(definition_id)
        if not definition:
            return None

        # Build update values
        update_values: dict[str, Any] = {}
        if name is not None:
            update_values["name"] = name
        if version is not None:
            update_values["version"] = version
        if description is not None:
            update_values["description"] = description
        if dag_json is not None:
            update_values["definition_json"] = dag_json  # DB column is definition_json
        if is_active is not None:
            update_values["is_active"] = is_active

        if update_values:
            stmt = (
                update(PlaybookDefinitionModel)
                .where(PlaybookDefinitionModel.id == definition_id)
                .values(**update_values)
            )
            await self.session.execute(stmt)
            await self.session.flush()
            await self.session.refresh(definition)
            logger.info(f"Updated playbook definition: {definition_id}")

        return definition

    async def delete(self, definition_id: str) -> bool:
        """Delete a playbook definition."""
        definition = await self.get_by_id(definition_id)
        if not definition:
            return False

        # Check if there are any runs using this definition
        count_stmt = select(func.count()).select_from(
            select(PlaybookRunModel)
            .where(PlaybookRunModel.definition_id == definition_id)
            .subquery()
        )
        result = await self.session.execute(count_stmt)
        run_count = result.scalar() or 0

        if run_count > 0:
            logger.warning(
                f"Cannot delete definition {definition_id}: has {run_count} associated runs"
            )
            return False

        await self.session.delete(definition)
        await self.session.flush()
        logger.info(f"Deleted playbook definition: {definition_id}")
        return True

    async def count(self) -> int:
        """Count total playbook definitions."""
        stmt = select(func.count()).select_from(PlaybookDefinitionModel)
        result = await self.session.execute(stmt)
        return result.scalar() or 0


# Caching enhancements
try:
    from core.cache import CacheKeys, get_cache

    class PlaybookDefinitionRepositoryCached(PlaybookDefinitionRepository):
        """Extended repository with caching support"""

        async def get_cached(
            self, definition_id: str
        ) -> PlaybookDefinitionModel | None:
            """Get playbook definition from cache or database"""
            cache = get_cache()
            cache_key = f"{CacheKeys.PLAYBOOK_DEFINITION}:{definition_id}"

            # Try cache first
            cached = await cache.get(cache_key)
            if cached is not None:
                logger.debug(f"Cache hit: playbook {definition_id}")
                return PlaybookDefinitionModel(**cached)

            # Query database
            entity = await self.get_by_id(definition_id)
            if entity is not None:
                # Cache for 5 minutes
                await cache.set(cache_key, entity.__dict__, CacheKeys.PLAYBOOK_TTL)

            return entity

        async def list_active_cached(self) -> list[PlaybookDefinitionModel]:
            """List active playbooks with cache"""
            cache = get_cache()
            cache_key = CacheKeys.PLAYBOOK_DEFINITIONS_LIST

            # Try cache first
            cached = await cache.get(cache_key)
            if cached is not None:
                logger.debug("Cache hit: active playbooks list")
                return [PlaybookDefinitionModel(**item) for item in cached]

            # Query database
            items, _ = await self.list_definitions(
                is_active=True, page=1, page_size=1000
            )

            # Cache the list
            await cache.set(
                cache_key, [item.__dict__ for item in items], CacheKeys.PLAYBOOK_TTL
            )

            return items

        async def invalidate_cache(self, definition_id: str | None = None):
            """Invalidate playbook cache"""
            from core.cache import invalidate_playbook_cache

            await invalidate_playbook_cache(definition_id)

        async def create_with_cache(self, **kwargs) -> PlaybookDefinitionModel:
            """Create playbook and invalidate cache"""
            entity = await self.create(**kwargs)
            await self.invalidate_cache()
            return entity

        async def update_with_cache(
            self, definition_id: str, **kwargs
        ) -> PlaybookDefinitionModel | None:
            """Update playbook and invalidate cache"""
            entity = await self.update(definition_id, **kwargs)
            if entity:
                await self.invalidate_cache(definition_id)
            return entity

        async def delete_with_cache(self, definition_id: str) -> bool:
            """Delete playbook and invalidate cache"""
            result = await self.delete(definition_id)
            if result:
                await self.invalidate_cache(definition_id)
            return result

    # Export cached version as default
    PlaybookDefinitionRepository = PlaybookDefinitionRepositoryCached

except ImportError:
    # Cache module not available, use original
    logger.warning("Cache module not available, using uncached repository")
    pass
