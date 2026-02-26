"""
Base Repository
Provides common CRUD operations for all repositories
"""

from typing import Type, TypeVar, Generic, Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from sqlalchemy.orm import Mapped

from db.session import Base

# Generic type for models
ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Base repository with common CRUD operations

    Provides:
    - Standard CRUD operations
    - Query builders
    - Pagination support
    - Caching integration
    """

    def __init__(self, session: AsyncSession, model: Type[ModelType]):
        self.session = session
        self.model = model

    async def get(self, id: str) -> Optional[ModelType]:
        """Get entity by ID"""
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def get_by_field(
        self,
        field_name: str,
        value: Any
    ) -> Optional[ModelType]:
        """Get entity by field value"""
        field = getattr(self.model, field_name)
        result = await self.session.execute(
            select(self.model).where(field == value)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        filters: Dict[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0,
        order_by: str | None = None,
        ascending: bool = True
    ) -> List[ModelType]:
        """List entities with filters, pagination, and ordering"""
        query = select(self.model)

        # Apply filters
        if filters:
            for field_name, value in filters.items():
                field = getattr(self.model, field_name)
                query = query.where(field == value)

        # Apply ordering
        if order_by:
            order_field = getattr(self.model, order_by)
            if ascending:
                query = query.order_by(order_field.asc())
            else:
                query = query.order_by(order_field.desc())

        # Apply pagination
        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count(self, filters: Dict[str, Any] | None = None) -> int:
        """Count entities with filters"""
        query = select(func.count(self.model.id))

        # Apply filters
        if filters:
            for field_name, value in filters.items():
                field = getattr(self.model, field_name)
                query = query.where(field == value)

        result = await self.session.execute(query)
        return result.scalar() or 0

    async def create(self, **kwargs) -> ModelType:
        """Create new entity"""
        entity = self.model(**kwargs)
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def update(
        self,
        id: str,
        **kwargs
    ) -> Optional[ModelType]:
        """Update entity by ID"""
        entity = await self.get(id)
        if entity is None:
            return None

        for field_name, value in kwargs.items():
            if hasattr(entity, field_name):
                setattr(entity, field_name, value)

        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def delete(self, id: str) -> bool:
        """Delete entity by ID"""
        entity = await self.get(id)
        if entity is None:
            return False

        await self.session.delete(entity)
        await self.session.flush()
        return True

    async def bulk_update(
        self,
        filters: Dict[str, Any],
        **kwargs
    ) -> int:
        """Bulk update entities matching filters"""
        # Build update statement
        stmt = update(self.model)

        # Apply filters
        for field_name, value in filters.items():
            field = getattr(self.model, field_name)
            stmt = stmt.where(field == value)

        # Set values
        stmt = stmt.values(**kwargs)

        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount

    async def bulk_delete(
        self,
        filters: Dict[str, Any]
    ) -> int:
        """Bulk delete entities matching filters"""
        # Build delete statement
        stmt = delete(self.model)

        # Apply filters
        for field_name, value in filters.items():
            field = getattr(self.model, field_name)
            stmt = stmt.where(field == value)

        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount

    async def exists(self, id: str) -> bool:
        """Check if entity exists"""
        result = await self.session.execute(
            select(func.count(self.model.id))
            .where(self.model.id == id)
        )
        return (result.scalar() or 0) > 0

    async def get_or_create(
        self,
        filters: Dict[str, Any],
        defaults: Dict[str, Any] | None = None
    ) -> tuple[ModelType, bool]:
        """Get entity or create if not exists"""
        entity = await self.get_by_field(
            list(filters.keys())[0],
            list(filters.values())[0]
        )

        if entity is not None:
            return entity, False

        # Create new entity
        create_data = {**filters, **(defaults or {})}
        entity = await self.create(**create_data)
        return entity, True
