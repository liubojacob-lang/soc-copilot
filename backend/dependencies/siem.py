"""
SIEM service dependency injection.

Provides get_siem_service for dependency injection into route handlers.
Automatically selects Elasticsearch or SQLite backend based on availability.
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_session
from services.integration.elasticsearch_service import check_es_availability


async def get_siem_service(
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Dependency that provides SIEM service configuration.

    Returns a dict with:
    - session: AsyncSession for database operations
    - backend: "elasticsearch" if ES is available, else "sqlite"
    - es_available: bool indicating ES health

    Usage:
        @router.get("/logs")
        async def search(siem: dict = Depends(get_siem_service)):
            session = siem["session"]
            backend = siem["backend"]
            ...
    """
    es_available = await check_es_availability()
    return {
        "session": session,
        "backend": "elasticsearch" if es_available else "sqlite",
        "es_available": es_available,
    }
