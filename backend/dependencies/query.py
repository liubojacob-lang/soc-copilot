"""
Query parameter dependencies for FastAPI routes.

Provides reusable dependency-injection callables for common query patterns.
"""

from fastapi import Query

from schemas.common import PaginationParams


async def paginated_query(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: str | None = Query(None, description="Field to sort by"),
    sort_order: str = Query(
        "desc", pattern="^(asc|desc)$", description="Sort order (asc/desc)"
    ),
) -> PaginationParams:
    """Dependency that parses pagination/sorting parameters into a PaginationParams model."""
    return PaginationParams(
        page=page, page_size=page_size, sort_by=sort_by, sort_order=sort_order
    )
