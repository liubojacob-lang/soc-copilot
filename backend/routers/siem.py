"""
SIEM Log Management API Routes.

Provides endpoints for ingesting and searching security event logs
with Elasticsearch-backed search and SQLite fallback.

Endpoints:
- POST   /api/v1/siem/ingest      Bulk log ingestion (max 500/req)
- GET    /api/v1/siem/logs        Search logs with filtering
- GET    /api/v1/siem/logs/{id}   Get single log entry
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from core.response import APIResponse
from db.session import get_session
from dependencies.auth import get_current_user
from dependencies.siem import get_siem_service
from models.user import UserModel
from schemas.common import PaginatedData, PaginatedResponse, paginated_response, success_response
from services.integration.elasticsearch_service import (
    get_log_by_id,
    index_logs_batch,
    search_logs,
)

router = APIRouter(prefix="/api/v1/siem", tags=["SIEM"])
logger = get_logger(__name__)

# ── Request/Response Schemas ────────────────────────────────────────────────


class LogEntry(BaseModel):
    """Single log entry for ingestion."""

    timestamp: str | None = Field(
        default=None,
        description="Event timestamp in ISO 8601 format (default: now)",
    )
    source: str = Field(..., description="Log source identifier (e.g., wazuh, syslog)")
    log_type: str = Field(
        default="raw",
        description="Log format type: syslog, cef, json, raw",
    )
    raw_data: str = Field(..., description="Raw log content")
    parsed_fields: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured parsed fields",
    )
    alert_id: str | None = Field(
        default=None,
        description="Associated security alert ID",
    )


class IngestRequest(BaseModel):
    """Batch ingestion request body."""

    logs: list[LogEntry] = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Log entries to ingest (1-500 per request)",
    )


class IngestResponse(BaseModel):
    """Batch ingestion response."""

    ingested: int = Field(..., description="Number of logs successfully ingested")
    failed: int = Field(default=0, description="Number of logs that failed")
    log_ids: list[str] = Field(default_factory=list, description="IDs of ingested logs")


class LogDetailResponse(BaseModel):
    """Single log entry response."""

    id: str
    tenant_id: str
    timestamp: str | None
    source: str
    log_type: str
    raw_data: str
    parsed_fields: dict[str, Any]
    alert_id: str | None
    created_at: str | None


# ── Endpoints ──────────────────────────────────────────────────────────────


@router.post("/ingest", response_model=APIResponse[IngestResponse])
async def ingest_logs(
    body: IngestRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> APIResponse:
    """Bulk ingest security event logs (max 500 per request).

    Logs are persisted to SQLite with optional Elasticsearch indexing
    for advanced search capabilities.
    """
    from dependencies.tenant import get_tenant_id

    # Get tenant context from request state (set by TenantMiddleware)
    # For now, use user ID as tenant fallback
    tenant_id = current_user.id

    try:
        log_dicts = []
        for entry in body.logs:
            log_dicts.append({
                "timestamp": entry.timestamp,
                "source": entry.source,
                "log_type": entry.log_type,
                "raw_data": entry.raw_data,
                "parsed_fields": entry.parsed_fields,
                "alert_id": entry.alert_id,
            })

        results = await index_logs_batch(session, log_dicts, tenant_id)
        await session.commit()

        ingested_ids = [r["id"] for r in results]
        logger.info(
            f"Ingested {len(ingested_ids)} SIEM logs",
            extra={"user_id": current_user.id, "log_count": len(ingested_ids)},
        )

        return success_response(
            data=IngestResponse(
                ingested=len(ingested_ids),
                failed=0,
                log_ids=ingested_ids,
            ),
            message=f"Successfully ingested {len(ingested_ids)} logs",
        )
    except Exception as e:
        await session.rollback()
        logger.error(f"SIEM log ingestion failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.get("/logs", response_model=PaginatedResponse[LogDetailResponse])
async def search_siem_logs(
    timestamp_from: str | None = Query(
        None, description="Filter from timestamp (ISO 8601)"
    ),
    timestamp_to: str | None = Query(
        None, description="Filter to timestamp (ISO 8601)"
    ),
    source: str | None = Query(None, description="Filter by log source"),
    log_type: str | None = Query(None, description="Filter by log type"),
    keyword: str | None = Query(None, description="Search keyword in raw data"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> PaginatedResponse:
    """Search SIEM logs with filters and pagination.

    Uses Elasticsearch for full-text search when available,
    falls back to SQLite LIKE queries otherwise.
    """
    tenant_id = current_user.id

    # Parse timestamps
    ts_from = None
    ts_to = None
    try:
        if timestamp_from:
            ts_from = datetime.fromisoformat(timestamp_from.replace("Z", "+00:00"))
        if timestamp_to:
            ts_to = datetime.fromisoformat(timestamp_to.replace("Z", "+00:00"))
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid timestamp format. Use ISO 8601: {str(e)}",
        )

    try:
        result = await search_logs(
            session=session,
            tenant_id=tenant_id,
            timestamp_from=ts_from,
            timestamp_to=ts_to,
            source=source,
            log_type=log_type,
            keyword=keyword,
            page=page,
            page_size=page_size,
        )

        items = [LogDetailResponse(**item) for item in result["items"]]

        return paginated_response(
            items=items,
            total=result["total"],
            page=result["page"],
            page_size=result["page_size"],
        )
    except Exception as e:
        logger.error(f"SIEM log search failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/logs/{log_id}", response_model=APIResponse[LogDetailResponse])
async def get_siem_log(
    log_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> APIResponse:
    """Get a single SIEM log entry by ID."""
    tenant_id = current_user.id

    try:
        log = await get_log_by_id(session, log_id, tenant_id)
        if log is None:
            raise HTTPException(status_code=404, detail=f"Log {log_id} not found")

        return success_response(
            data=LogDetailResponse(**log),
            message="Log retrieved successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get SIEM log {log_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve log: {str(e)}")
