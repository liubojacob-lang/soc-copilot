"""Repository for playbook definitions."""

import uuid
from typing import Any, Optional
from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.playbook_definition import PlaybookDefinitionModel
from models.playbook_run import PlaybookRunModel
from core.logger import get_logger

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
        description: Optional[str] = None,
        created_by_user_id: Optional[str] = None,
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

    async def get_by_id(self, definition_id: str) -> Optional[PlaybookDefinitionModel]:
        """Get playbook definition by ID."""
        stmt = select(PlaybookDefinitionModel).where(
            PlaybookDefinitionModel.id == definition_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Optional[PlaybookDefinitionModel]:
        """Get playbook definition by name."""
        stmt = select(PlaybookDefinitionModel).where(
            PlaybookDefinitionModel.name == name
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_definitions(
        self,
        is_active: Optional[bool] = None,
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
        name: Optional[str] = None,
        version: Optional[str] = None,
        description: Optional[str] = None,
        dag_json: Optional[dict[str, Any]] = None,
        is_active: Optional[bool] = None,
    ) -> Optional[PlaybookDefinitionModel]:
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
            select(PlaybookRunModel).where(
                PlaybookRunModel.definition_id == definition_id
            ).subquery()
        )
        result = await self.session.execute(count_stmt)
        run_count = result.scalar() or 0
        
        if run_count > 0:
            logger.warning(f"Cannot delete definition {definition_id}: has {run_count} associated runs")
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
