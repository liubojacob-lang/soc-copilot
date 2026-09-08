"""
Base Repository
Provides common CRUD operations for all repositories with tenant isolation.
"""

from typing import Any, Generic, TypeVar

from sqlalchemy import Column, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Delete as DeleteStmt
from sqlalchemy.sql import Select
from sqlalchemy.sql import Update as UpdateStmt

from db.session import Base

# Generic type for models
ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Base repository with common CRUD operations and tenant isolation.

    Provides:
    - Standard CRUD operations (get, list, create, update, delete)
    - Query builders with tenant filter support
    - Pagination support
    - Bulk operations with tenant scoping

    Tenant isolation:
    - If the model has a 'tenant_id' column and a tenant_id is provided,
      all read/update/delete operations are automatically scoped.
    - Operations without a tenant_id operate across all tenants (admin mode).
    """

    def __init__(self, session: AsyncSession, model: type[ModelType]):
        self.session = session
        self.model = model
        # Cache whether this model has a tenant_id column
        self._has_tenant_col = hasattr(self.model, "tenant_id")

    # ── Tenant filter helper ───────────────────────────────────────

    def _apply_tenant_filter(
        self,
        query: Select | UpdateStmt | DeleteStmt,
        tenant_id: str | None,
    ) -> Select | UpdateStmt | DeleteStmt:
        """Apply tenant_id filter to query if the model supports it.

        Args:
            query: SQLAlchemy query (select/update/delete)
            tenant_id: Tenant identifier; if None, no filter is applied (admin mode)

        Returns:
            Query with tenant filter applied, or unchanged query
        """
        if self._has_tenant_col and tenant_id is not None:
            tenant_col: Column = self.model.tenant_id
            query = query.where(tenant_col == tenant_id)
        return query

    # ── CRUD (tenant-aware) ────────────────────────────────────────

    async def get(self, id: str, tenant_id: str | None = None) -> ModelType | None:
        """Get entity by ID, optionally scoped to tenant."""
        query = select(self.model).where(self.model.id == id)
        query = self._apply_tenant_filter(query, tenant_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_field(
        self,
        field_name: str,
        value: Any,
        tenant_id: str | None = None,
    ) -> ModelType | None:
        """Get entity by field value, optionally scoped to tenant."""
        field = getattr(self.model, field_name)
        query = select(self.model).where(field == value)
        query = self._apply_tenant_filter(query, tenant_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list(
        self,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0,
        order_by: str | None = None,
        ascending: bool = True,
        tenant_id: str | None = None,
    ) -> list[ModelType]:
        """List entities with filters, pagination, ordering, and tenant scoping."""
        query = select(self.model)

        # Tenant filter
        query = self._apply_tenant_filter(query, tenant_id)

        # Apply field filters
        if filters:
            for field_name, value in filters.items():
                if value is not None:
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

    async def count(
        self,
        filters: dict[str, Any] | None = None,
        tenant_id: str | None = None,
    ) -> int:
        """Count entities with filters, optionally scoped to tenant."""
        query = select(func.count(self.model.id))
        query = self._apply_tenant_filter(query, tenant_id)

        # Apply field filters
        if filters:
            for field_name, value in filters.items():
                if value is not None:
                    field = getattr(self.model, field_name)
                    query = query.where(field == value)

        result = await self.session.execute(query)
        return result.scalar() or 0

    async def create(self, **kwargs) -> ModelType:
        """Create new entity.

        Note: tenant_id must be provided in kwargs if the model supports it.
        """
        entity = self.model(**kwargs)
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def update(
        self,
        id: str,
        tenant_id: str | None = None,
        **kwargs,
    ) -> ModelType | None:
        """Update entity by ID, optionally scoped to tenant.

        Args:
            id: Entity primary key
            tenant_id: If provided, only updates if entity belongs to this tenant
            **kwargs: Fields to update

        Returns:
            Updated entity or None if not found
        """
        query = select(self.model).where(self.model.id == id)
        query = self._apply_tenant_filter(query, tenant_id)
        result = await self.session.execute(query)
        entity = result.scalar_one_or_none()

        if entity is None:
            return None

        for field_name, value in kwargs.items():
            if hasattr(entity, field_name):
                setattr(entity, field_name, value)

        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def delete(self, id: str, tenant_id: str | None = None) -> bool:
        """Delete entity by ID, optionally scoped to tenant."""
        query = select(self.model).where(self.model.id == id)
        query = self._apply_tenant_filter(query, tenant_id)
        result = await self.session.execute(query)
        entity = result.scalar_one_or_none()

        if entity is None:
            return False

        await self.session.delete(entity)
        await self.session.flush()
        return True

    async def bulk_update(
        self,
        filters: dict[str, Any],
        tenant_id: str | None = None,
        **kwargs,
    ) -> int:
        """Bulk update entities matching filters, scoped to tenant."""
        stmt = update(self.model)
        stmt = self._apply_tenant_filter(stmt, tenant_id)

        # Apply field filters
        for field_name, value in filters.items():
            if value is not None:
                field = getattr(self.model, field_name)
                stmt = stmt.where(field == value)

        # Set values
        stmt = stmt.values(**kwargs)

        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount

    async def bulk_delete(
        self,
        filters: dict[str, Any],
        tenant_id: str | None = None,
    ) -> int:
        """Bulk delete entities matching filters, scoped to tenant."""
        stmt = delete(self.model)
        stmt = self._apply_tenant_filter(stmt, tenant_id)

        # Apply field filters
        for field_name, value in filters.items():
            if value is not None:
                field = getattr(self.model, field_name)
                stmt = stmt.where(field == value)

        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount

    async def exists(self, id: str, tenant_id: str | None = None) -> bool:
        """Check if entity exists, optionally scoped to tenant."""
        query = select(func.count(self.model.id)).where(self.model.id == id)
        query = self._apply_tenant_filter(query, tenant_id)
        result = await self.session.execute(query)
        return (result.scalar() or 0) > 0

    async def get_or_create(
        self,
        filters: dict[str, Any],
        defaults: dict[str, Any] | None = None,
        tenant_id: str | None = None,
    ) -> tuple[ModelType, bool]:
        """Get entity or create if not exists, optionally scoped to tenant.

        Note: When creating, tenant_id from filters is preserved automatically.
        If you want to scope the lookup but create with a different tenant_id,
        set tenant_id in defaults.
        """
        filter_key = next(iter(filters.keys()))
        filter_val = next(iter(filters.values()))
        entity = await self.get_by_field(filter_key, filter_val, tenant_id=tenant_id)

        if entity is not None:
            return entity, False

        # Create new entity
        create_data = {**filters, **(defaults or {})}
        entity = await self.create(**create_data)
        return entity, True
