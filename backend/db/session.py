"""Database session management."""

import os
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

# Data directory
DATA_DIR = Path(__file__).parent.parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "app.db"

# SQLite async engine
DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()


async def get_session() -> AsyncSession:
    """Get database session for dependency injection.

    Uses explicit transaction management to ensure data is persisted.
    """
    from core.logger import get_logger
    logger = get_logger(__name__)

    session = AsyncSessionLocal()
    try:
        yield session
        # Explicit commit at the end
        await session.commit()
        logger.info("Session committed successfully")
    except Exception as e:
        logger.error(f"Session error, rolling back: {e}")
        await session.rollback()
        raise
    finally:
        await session.close()


async def init_db() -> None:
    """Initialize database tables."""
    # Import all models to ensure they're registered with Base
    from models import (
        history, asset, ioc_hit, threat_intel_cache, playbook_output,
        playbook_run, user, api_key, audit_log,
    )  # noqa: F401
    from models.playbook_run import PlaybookRunModel, PlaybookRunStepModel  # noqa: F401
    from models.user import UserModel  # noqa: F401
    from models.api_key import APIKeyModel  # noqa: F401
    from models.audit_log import AuditLogModel  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
