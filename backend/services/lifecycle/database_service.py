"""Database lifecycle service.

Manages database initialization and connection disposal.
"""

from __future__ import annotations

from core.lifecycle import LifecycleService, ServicePriority
from core.logger import get_logger
from db.session import engine, init_db

logger = get_logger(__name__)


class DatabaseService(LifecycleService):
    """Database initialization and connection management.

    This service handles:
    - Database table creation on startup
    - Connection pool disposal on shutdown

    Priority: CRITICAL (must start first)
    """

    @property
    def name(self) -> str:
        return "database"

    @property
    def priority(self) -> ServicePriority:
        return ServicePriority.CRITICAL

    async def start(self) -> None:
        """Initialize database tables.

        Creates all tables defined in the models if they don't exist.
        """
        logger.info("Initializing database tables...")
        await init_db()
        logger.info("Database initialized successfully")

    async def stop(self) -> None:
        """Dispose database engine and close all connections.

        This ensures clean shutdown of all database connections.
        """
        logger.info("Disposing database engine...")
        await engine.dispose()
        logger.info("Database engine disposed")

    async def health_check(self) -> bool:
        """Check database connectivity.

        Returns:
            True if database is accessible, False otherwise
        """
        try:
            from sqlalchemy import text

            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
