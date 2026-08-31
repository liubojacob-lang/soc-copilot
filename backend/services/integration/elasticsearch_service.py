"""
Elasticsearch Integration Service for SIEM Log Storage.

Provides log indexing and search against Elasticsearch with automatic
degradation to SQLite when ES is unavailable.

Architecture:
- Primary: Elasticsearch REST API (httpx.AsyncClient)
- Fallback: SQLite via SIEMLog model (LIKE-based search)

Index naming: soc_copilot_logs-YYYY-MM-DD (daily shard rotation)
"""

import math
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from sqlalchemy import Text, and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.logger import get_logger
from models.siem_log import SIEMLog

logger = get_logger(__name__)

# ── ES Configuration ─────────────────────────────────────────────────────────

ES_HOST = getattr(settings, "elasticsearch_host", "")
ES_PORT = getattr(settings, "elasticsearch_port", 9200)
ES_SCHEME = getattr(settings, "elasticsearch_scheme", "http")
ES_USER = getattr(settings, "elasticsearch_user", "")
ES_PASSWORD = getattr(settings, "elasticsearch_password", "")
ES_VERIFY_SSL = getattr(settings, "elasticsearch_verify_ssl", True)
ES_TIMEOUT = getattr(settings, "elasticsearch_timeout", 10.0)
ES_INDEX_PREFIX = "soc_copilot_logs"

# Connection status tracking
_es_available: bool | None = None  # None = unchecked, True/False = known state
_es_last_check: datetime | None = None
_ES_RECHECK_INTERVAL = timedelta(seconds=60)

# Singleton httpx client
_http_client: httpx.AsyncClient | None = None


async def _get_client() -> httpx.AsyncClient:
    """Get or create the shared httpx.AsyncClient for ES communication."""
    global _http_client
    if _http_client is None:
        auth = None
        if ES_USER and ES_PASSWORD:
            auth = httpx.BasicAuth(ES_USER, ES_PASSWORD)

        _http_client = httpx.AsyncClient(
            auth=auth,
            verify=ES_VERIFY_SSL,
            timeout=httpx.Timeout(ES_TIMEOUT),
        )
    return _http_client


def _es_enabled() -> bool:
    """Check if Elasticsearch is configured."""
    return bool(ES_HOST)


def _daily_index(timestamp: datetime | None = None) -> str:
    """Generate daily index name: soc_copilot_logs-YYYY-MM-DD."""
    ts = timestamp or datetime.now(UTC)
    return f"{ES_INDEX_PREFIX}-{ts.strftime('%Y-%m-%d')}"


async def check_es_availability() -> bool:
    """Check if Elasticsearch is reachable.

    Caches the result for _ES_RECHECK_INTERVAL to avoid
    hammering an unresponsive ES with connection attempts.
    """
    global _es_available, _es_last_check

    if not _es_enabled():
        _es_available = False
        return False

    now = datetime.now(UTC)
    if _es_available is not None and _es_last_check is not None:
        if now - _es_last_check < _ES_RECHECK_INTERVAL:
            return _es_available

    _es_last_check = now

    try:
        client = await _get_client()
        url = f"{ES_SCHEME}://{ES_HOST}:{ES_PORT}/_cluster/health"
        resp = await client.get(url)
        _es_available = resp.status_code < 500
        if _es_available:
            logger.info("Elasticsearch connection verified")
        else:
            logger.warning(f"Elasticsearch returned status {resp.status_code}")
    except Exception as e:
        _es_available = False
        logger.warning(f"Elasticsearch unavailable, falling back to SQLite: {e}")

    return _es_available


# ── ES Index Operations ──────────────────────────────────────────────────────


async def index_log(
    session: AsyncSession,
    log_entry: dict[str, Any],
    tenant_id: str,
) -> dict[str, Any]:
    """Index a log entry. Writes to ES primary, SQLite as guaranteed store.

    Args:
        session: Database session for SQLite fallback/write
        log_entry: Log data dict with keys: timestamp, source, log_type, raw_data,
                   parsed_fields, alert_id (optional)
        tenant_id: Tenant identifier

    Returns:
        The log entry dict with added id field
    """
    import uuid as uuid_mod

    log_id = log_entry.get("id") or str(uuid_mod.uuid4())
    ts = log_entry.get("timestamp", datetime.now(UTC))
    if isinstance(ts, str):
        ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))

    # Always persist to SQLite as the source of truth
    siem_log = SIEMLog(
        id=log_id,
        tenant_id=tenant_id,
        timestamp=ts,
        source=log_entry.get("source", "unknown"),
        log_type=log_entry.get("log_type", "raw"),
        raw_data=log_entry.get("raw_data", ""),
        parsed_fields=log_entry.get("parsed_fields", {}),
        alert_id=log_entry.get("alert_id"),
    )
    session.add(siem_log)

    # Attempt ES indexing (fire-and-forget; SQLite is the durable store)
    if _es_enabled():
        try:
            es_ok = await check_es_availability()
            if es_ok:
                client = await _get_client()
                index_name = _daily_index(ts)

                doc = {
                    "id": log_id,
                    "tenant_id": tenant_id,
                    "timestamp": ts.isoformat(),
                    "source": log_entry.get("source", "unknown"),
                    "log_type": log_entry.get("log_type", "raw"),
                    "raw_data": log_entry.get("raw_data", ""),
                    "parsed_fields": log_entry.get("parsed_fields", {}),
                    "alert_id": log_entry.get("alert_id"),
                    "created_at": datetime.now(UTC).isoformat(),
                }

                url = f"{ES_SCHEME}://{ES_HOST}:{ES_PORT}/{index_name}/_doc/{log_id}"
                resp = await client.put(url, json=doc)
                if resp.status_code >= 400:
                    logger.warning(
                        f"ES index returned {resp.status_code}: {resp.text[:200]}"
                    )
        except Exception as e:
            logger.warning(f"ES indexing failed, relying on SQLite: {e}")

    return {
        "id": log_id,
        "tenant_id": tenant_id,
        "timestamp": ts.isoformat(),
        "source": log_entry.get("source", "unknown"),
        "log_type": log_entry.get("log_type", "raw"),
        "raw_data": log_entry.get("raw_data", ""),
        "parsed_fields": log_entry.get("parsed_fields", {}),
        "alert_id": log_entry.get("alert_id"),
        "created_at": siem_log.created_at.isoformat() if siem_log.created_at else None,
    }


async def index_logs_batch(
    session: AsyncSession,
    logs: list[dict[str, Any]],
    tenant_id: str,
) -> list[dict[str, Any]]:
    """Index multiple log entries in batch.

    Args:
        session: Database session
        logs: List of log entry dicts
        tenant_id: Tenant identifier

    Returns:
        List of created log entries with ids
    """
    results = []
    for log_entry in logs:
        result = await index_log(session, log_entry, tenant_id)
        results.append(result)
    return results


# ── Search Operations ───────────────────────────────────────────────────────


async def search_logs(
    session: AsyncSession,
    tenant_id: str,
    timestamp_from: datetime | None = None,
    timestamp_to: datetime | None = None,
    source: str | None = None,
    log_type: str | None = None,
    keyword: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """Search logs with ES primary, SQLite fallback.

    Args:
        session: Database session
        tenant_id: Tenant identifier
        timestamp_from: Filter logs after this timestamp
        timestamp_to: Filter logs before this timestamp
        source: Filter by log source
        log_type: Filter by log type
        keyword: Search keyword in raw_data
        page: Page number (1-indexed)
        page_size: Items per page

    Returns:
        Dict with items, total, page, page_size, total_pages
    """
    es_ok = _es_enabled() and await check_es_availability()

    if es_ok:
        try:
            return await _search_es(
                tenant_id=tenant_id,
                timestamp_from=timestamp_from,
                timestamp_to=timestamp_to,
                source=source,
                log_type=log_type,
                keyword=keyword,
                page=page,
                page_size=page_size,
            )
        except Exception as e:
            logger.warning(f"ES search failed, falling back to SQLite: {e}")

    # SQLite fallback
    return await _search_sqlite(
        session=session,
        tenant_id=tenant_id,
        timestamp_from=timestamp_from,
        timestamp_to=timestamp_to,
        source=source,
        log_type=log_type,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )


async def _search_es(
    tenant_id: str,
    timestamp_from: datetime | None = None,
    timestamp_to: datetime | None = None,
    source: str | None = None,
    log_type: str | None = None,
    keyword: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """Execute search against Elasticsearch."""
    client = await _get_client()
    index_pattern = f"{ES_INDEX_PREFIX}-*"

    must_clauses: list[dict[str, Any]] = [{"term": {"tenant_id": tenant_id}}]

    if timestamp_from:
        must_clauses.append({
            "range": {"timestamp": {"gte": timestamp_from.isoformat()}}
        })
    if timestamp_to:
        must_clauses.append({
            "range": {"timestamp": {"lte": timestamp_to.isoformat()}}
        })
    if source:
        must_clauses.append({"term": {"source": source}})
    if log_type:
        must_clauses.append({"term": {"log_type": log_type}})
    if keyword:
        safe_keyword = keyword.replace('"', '\\"')
        must_clauses.append({
            "query_string": {
                "query": safe_keyword,
                "fields": ["raw_data", "parsed_fields"],
            }
        })

    es_query = {
        "query": {"bool": {"must": must_clauses}},
        "from": (page - 1) * page_size,
        "size": page_size,
        "sort": [{"timestamp": {"order": "desc"}}],
    }

    url = f"{ES_SCHEME}://{ES_HOST}:{ES_PORT}/{index_pattern}/_search"
    resp = await client.post(url, json=es_query)

    if resp.status_code >= 400:
        raise RuntimeError(f"ES search error: {resp.status_code} {resp.text[:200]}")

    body = resp.json()
    hits = body.get("hits", {})
    total = hits.get("total", {})
    total_value = total.get("value", 0) if isinstance(total, dict) else total

    items = []
    for hit in hits.get("hits", []):
        items.append(hit.get("_source", {}))

    total_pages = max(1, math.ceil(total_value / page_size)) if total_value > 0 else 0

    return {
        "items": items,
        "total": total_value,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


async def _search_sqlite(
    session: AsyncSession,
    tenant_id: str,
    timestamp_from: datetime | None = None,
    timestamp_to: datetime | None = None,
    source: str | None = None,
    log_type: str | None = None,
    keyword: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """Execute search against SQLite using parameterized LIKE queries."""
    conditions = [SIEMLog.tenant_id == tenant_id]

    if timestamp_from:
        conditions.append(SIEMLog.timestamp >= timestamp_from)
    if timestamp_to:
        conditions.append(SIEMLog.timestamp <= timestamp_to)
    if source:
        conditions.append(SIEMLog.source == source)
    if log_type:
        conditions.append(SIEMLog.log_type == log_type)
    if keyword:
        conditions.append(
            or_(
                SIEMLog.raw_data.ilike(f"%{keyword}%"),
                func.json_extract(SIEMLog.parsed_fields, "$")
                .cast(Text)
                .ilike(f"%{keyword}%"),
            )
        )

    # Count query
    count_query = select(func.count(SIEMLog.id)).where(and_(*conditions))
    count_result = await session.execute(count_query)
    total = count_result.scalar() or 0

    # Select query with pagination
    offset = (page - 1) * page_size
    select_query = (
        select(SIEMLog)
        .where(and_(*conditions))
        .order_by(desc(SIEMLog.timestamp))
        .limit(page_size)
        .offset(offset)
    )
    result = await session.execute(select_query)
    rows = result.scalars().all()

    items = []
    for row in rows:
        items.append({
            "id": row.id,
            "tenant_id": row.tenant_id,
            "timestamp": row.timestamp.isoformat() if row.timestamp else None,
            "source": row.source,
            "log_type": row.log_type,
            "raw_data": row.raw_data,
            "parsed_fields": row.parsed_fields,
            "alert_id": row.alert_id,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        })

    total_pages = max(1, math.ceil(total / page_size)) if total > 0 else 0

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


async def get_log_by_id(
    session: AsyncSession,
    log_id: str,
    tenant_id: str,
) -> dict[str, Any] | None:
    """Get a single log entry by ID. Tries ES first, falls back to SQLite.

    Args:
        session: Database session
        log_id: Log entry ID
        tenant_id: Tenant identifier

    Returns:
        Log entry dict or None if not found
    """
    # Try ES first
    es_ok = _es_enabled() and await check_es_availability()
    if es_ok:
        try:
            client = await _get_client()
            index_pattern = f"{ES_INDEX_PREFIX}-*"
            url = f"{ES_SCHEME}://{ES_HOST}:{ES_PORT}/{index_pattern}/_doc/{log_id}"
            resp = await client.get(url)
            if resp.status_code == 200:
                body = resp.json()
                return body.get("_source")
        except Exception as e:
            logger.warning(f"ES get_by_id failed, falling back to SQLite: {e}")

    # SQLite fallback
    query = select(SIEMLog).where(
        and_(SIEMLog.id == log_id, SIEMLog.tenant_id == tenant_id)
    )
    result = await session.execute(query)
    row = result.scalar_one_or_none()

    if row is None:
        return None

    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "timestamp": row.timestamp.isoformat() if row.timestamp else None,
        "source": row.source,
        "log_type": row.log_type,
        "raw_data": row.raw_data,
        "parsed_fields": row.parsed_fields,
        "alert_id": row.alert_id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


async def close_es_client() -> None:
    """Close the shared Elasticsearch HTTP client."""
    global _http_client
    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None
        logger.info("Elasticsearch HTTP client closed")
