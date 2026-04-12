"""
Tests for database session module.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import AsyncSessionLocal, get_session, init_db


class TestDatabaseSession:
    """Test database session functionality."""

    @pytest.mark.asyncio
    async def test_get_session_returns_session(self):
        """get_session should return an async session."""
        session_gen = get_session()
        session = await session_gen.__anext__()

        assert session is not None
        assert isinstance(session, AsyncSession)

        # Cleanup
        try:
            await session_gen.__anext__()
        except StopAsyncIteration:
            pass

    @pytest.mark.asyncio
    async def test_session_can_execute_query(self):
        """Session should be able to execute queries."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1

    @pytest.mark.asyncio
    async def test_session_rollback_on_error(self):
        """Session should handle rollback on error."""
        async with AsyncSessionLocal() as session:
            try:
                # This should fail
                await session.execute(text("SELECT * FROM nonexistent_table"))
                await session.commit()
            except Exception:
                await session.rollback()
                # Session should still be usable
                result = await session.execute(text("SELECT 1"))
                assert result.scalar() == 1

    @pytest.mark.asyncio
    async def test_multiple_sessions(self):
        """Should be able to create multiple sessions."""
        async with AsyncSessionLocal() as session1:
            async with AsyncSessionLocal() as session2:
                result1 = await session1.execute(text("SELECT 1"))
                result2 = await session2.execute(text("SELECT 2"))

                assert result1.scalar() == 1
                assert result2.scalar() == 2


class TestDatabaseInit:
    """Test database initialization."""

    @pytest.mark.asyncio
    async def test_init_db(self):
        """init_db should complete without error."""
        # This should not raise any exceptions
        await init_db()
