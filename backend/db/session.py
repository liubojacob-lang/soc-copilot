"""Database session management.

v0.8.2: Fixed SQLite connection pool parameters issue.
SQLite does not support pool_size, max_overflow, pool_timeout, pool_recycle parameters.
These parameters are only valid for PostgreSQL, MySQL, etc.

v0.8.5: Added test database support for isolated testing.
"""

import os
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from core.config import settings

# Data directory
DATA_DIR = Path(__file__).parent.parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# Check if using test database (for testing)
IS_TEST_ENV = os.getenv("ENVIRONMENT") == "test"

# 统一数据库：默认直连独立仿真 PostgreSQL 数据库 (15432 端口)
SIM_POSTGRES_URL = (
    "postgresql+asyncpg://soc_sim_user:soc_sim_password_123456@127.0.0.1:15432/soc_sim_db"
)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = SIM_POSTGRES_URL

# Determine database type
IS_POSTGRESQL = DATABASE_URL.startswith("postgresql")
IS_SQLITE = DATABASE_URL.startswith("sqlite")

# Use separate test database in test environment (for fast isolated pytest unit tests)
if IS_TEST_ENV:
    TEST_DB_PATH = os.getenv(
        "TEST_DB_PATH", "/tmp/soc_copilot_test.db"
    )  # nosec B108 - test-only path
    DATABASE_URL = f"sqlite+aiosqlite:///{TEST_DB_PATH}"
    IS_SQLITE = True
    IS_POSTGRESQL = False

# Create engine with appropriate settings based on database type
if IS_SQLITE or (IS_TEST_ENV):
    # SQLite: No connection pool parameters (not supported)
    # Use NullPool for SQLite to avoid connection issues
    from sqlalchemy import event
    from sqlalchemy.pool import NullPool

    if IS_TEST_ENV:
        DB_PATH = Path(TEST_DB_PATH)
    else:
        DB_PATH = DATA_DIR / "app.db"

    if not DATABASE_URL.startswith("sqlite+aiosqlite:///"):
        DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"

    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=NullPool,  # SQLite works best with NullPool
    )

    @event.listens_for(engine.sync_engine, "connect")
    def _enable_sqlite_fk(dbapi_connection, _connection_record):
        """Enforce FK constraints (incl. ON DELETE CASCADE) on SQLite.

        SQLite disables foreign key enforcement per-connection by default,
        which silently turned retention deletes into orphan rows in dev.
        """
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
elif IS_POSTGRESQL:
    # PostgreSQL: Use connection pool settings
    # Convert sync URL to async if needed
    if DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif DATABASE_URL.startswith("postgresql+psycopg2://"):
        DATABASE_URL = DATABASE_URL.replace(
            "postgresql+psycopg2://", "postgresql+asyncpg://", 1
        )

    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
        pool_recycle=settings.db_pool_recycle,
        pool_pre_ping=settings.db_pool_pre_ping,
    )
else:
    # Other databases (MySQL, etc.): Use default pool settings
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
        pool_recycle=settings.db_pool_recycle,
        pool_pre_ping=settings.db_pool_pre_ping,
    )

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()


async def get_session() -> AsyncSession:
    """Get database session for dependency injection.

    The caller (route handler) is responsible for explicitly calling
    await session.commit() when the operation succeeds. This prevents
    premature commits if an exception occurs in a response interceptor or
    downstream middleware after the route handler has returned.
    """
    session = AsyncSessionLocal()
    try:
        yield session
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def init_db() -> None:
    """Initialize database tables."""
    # Import all models to ensure they're registered with Base
    import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
