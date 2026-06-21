"""Base Service class with transaction management and common patterns."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger

logger = get_logger(__name__)


class BaseService:
    """Base service with transaction management and repository composition.

    Design principles:
    - Service layer owns transaction boundaries (explicit commit/rollback)
    - Service can compose multiple repositories for business logic
    - Router layer only handles HTTP concerns (validation, cookies, response formatting)
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def commit(self) -> None:
        """Explicitly commit the current transaction."""
        await self.session.commit()

    async def rollback(self) -> None:
        """Explicitly rollback the current transaction."""
        await self.session.rollback()

    async def flush(self) -> None:
        """Flush pending changes to the database without committing."""
        await self.session.flush()

    async def __aenter__(self) -> "BaseService":
        """Enter async context manager."""
        return self

    async def __aexit__(self, exc_type: type | None, exc_val: Any, exc_tb: Any) -> None:
        """Exit async context manager with automatic rollback on error."""
        if exc_type is not None:
            await self.rollback()
