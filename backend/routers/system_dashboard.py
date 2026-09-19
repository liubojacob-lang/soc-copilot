"""System health dashboard for SOC Copilot.

Provides comprehensive system monitoring including:
- Database connection pool status
- Redis connection pool status
- AI model availability
- Disk space and memory usage
- System statistics
"""

import os
import platform
import shutil
import time
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.logger import get_logger
from core.token_blacklist import REDIS_AVAILABLE
from db.session import AsyncSessionLocal, engine
from dependencies.auth import get_current_user
from models.user import UserModel

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/system", tags=["System Dashboard"])


# ==================== Models ====================


class PoolStatus(BaseModel):
    """Connection pool status."""

    size: int
    checked_in: int
    checked_out: int
    overflow: int
    invalid: int


class DatabaseStatus(BaseModel):
    """Database status model."""

    status: str
    latency_ms: float
    pool: PoolStatus | None = None
    version: str | None = None
    database_size: str | None = None
    active_connections: int | None = None


class RedisStatus(BaseModel):
    """Redis status model."""

    status: str
    latency_ms: float | None = None
    version: str | None = None
    connected_clients: int | None = None
    used_memory: str | None = None
    uptime_seconds: int | None = None
    pool_connections: int | None = None


class AIModelStatus(BaseModel):
    """AI model status model."""

    id: str
    name: str
    provider: str
    is_active: bool
    last_used: str | None = None
    total_requests: int = 0


class DiskUsage(BaseModel):
    """Disk usage model."""

    total_gb: float
    used_gb: float
    free_gb: float
    percent_used: float


class MemoryUsage(BaseModel):
    """Memory usage model."""

    total_gb: float
    available_gb: float
    used_gb: float
    percent_used: float


class SystemStats(BaseModel):
    """System statistics model."""

    cpu_percent: float
    memory: MemoryUsage
    disk: DiskUsage
    uptime_seconds: float
    platform: str
    python_version: str


class SystemDashboard(BaseModel):
    """Full system dashboard model."""

    timestamp: str
    version: str
    environment: str
    database: DatabaseStatus
    redis: RedisStatus
    ai_models: list[AIModelStatus]
    system: SystemStats
    features: dict[str, bool]


class DBConnectionItem(BaseModel):
    pid: int
    usename: str
    client_addr: str | None = None
    state: str
    duration_seconds: float = 0.0
    wait_event_type: str | None = None
    wait_event: str | None = None
    query: str
    is_slow: bool = False
    is_idle_tx: bool = False


class DBConnectionsDetail(BaseModel):
    engine: str
    summary: dict[str, int]
    pool: PoolStatus | None = None
    pool_utilization: float = 0.0
    connections: list[DBConnectionItem] = []


class RedisClientItem(BaseModel):
    id: str
    addr: str
    age_seconds: int = 0
    idle_seconds: int = 0
    cmd: str = ""
    flags: str = ""
    name: str = ""


class RedisConnectionsDetail(BaseModel):
    status: str
    summary: dict[str, Any]
    clients: list[RedisClientItem] = []
    queue: dict[str, Any] = {}


class SystemIntegrationsDetail(BaseModel):
    websocket_connections: int = 0
    wazuh: dict[str, Any] = {}
    threat_intel: dict[str, Any] = {}
    ai_models_count: int = 0


class ConnectionsDashboardResponse(BaseModel):
    timestamp: str
    health_score: int
    warnings: list[str]
    database: DBConnectionsDetail
    redis: RedisConnectionsDetail
    integrations: SystemIntegrationsDetail


class DiagnosticItem(BaseModel):
    name: str
    status: str  # "ok" | "warn" | "error"
    latency_ms: float | None = None
    message: str
    details: dict[str, Any] | None = None


class DiagnosticsResponse(BaseModel):
    timestamp: str
    overall_status: str  # "ok" | "warn" | "error"
    items: list[DiagnosticItem]


# ==================== Helper Functions ====================


def get_database_pool_status() -> PoolStatus | None:
    """Get SQLAlchemy connection pool status."""
    try:
        pool = engine.pool
        size_fn = getattr(pool, "size", None)
        if not callable(size_fn):
            return None
        checked_in = getattr(pool, "checkedin", lambda: 0)()
        checked_out = getattr(pool, "checkedout", lambda: 0)()
        overflow = getattr(pool, "overflow", lambda: 0)()
        invalid = (
            getattr(pool, "invalidatedcount", lambda: 0)()
            if hasattr(pool, "invalidatedcount")
            else 0
        )
        return PoolStatus(
            size=size_fn(),
            checked_in=checked_in,
            checked_out=checked_out,
            overflow=max(0, overflow),
            invalid=invalid,
        )
    except Exception as e:
        logger.warning(f"Failed to get pool status: {e}")
        return None


async def get_database_size(session: AsyncSession) -> str | None:
    """Get database size (SQLite fallback)."""
    try:
        if "sqlite" in str(engine.url):
            db_path = (
                str(engine.url)
                .replace("sqlite:///", "")
                .replace("sqlite+aiosqlite:///", "")
            )
            if os.path.exists(db_path):
                size_bytes = os.path.getsize(db_path)
                if size_bytes < 1024:
                    return f"{size_bytes} B"
                elif size_bytes < 1024 * 1024:
                    return f"{size_bytes / 1024:.2f} KB"
                elif size_bytes < 1024 * 1024 * 1024:
                    return f"{size_bytes / (1024 * 1024):.2f} MB"
                else:
                    return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
        return None
    except Exception:
        return None


async def get_database_info(
    session: AsyncSession,
) -> tuple[str | None, str | None, int | None]:
    """Get database version, size, and active connection count."""
    version = None
    db_size = None
    active_connections = None
    try:
        is_postgres = "postgresql" in str(engine.url)
        if is_postgres:
            res = await session.execute(text("SELECT version()"))
            row = res.fetchone()
            if row and row[0]:
                parts = row[0].split()
                # parts[1] is typically the version number, e.g. "15.7"
                version = parts[1] if len(parts) > 1 else row[0]

            size_res = await session.execute(
                text("SELECT pg_size_pretty(pg_database_size(current_database()))")
            )
            size_row = size_res.fetchone()
            if size_row:
                db_size = size_row[0]

            conn_res = await session.execute(
                text(
                    "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()"
                )
            )
            conn_row = conn_res.fetchone()
            if conn_row:
                active_connections = int(conn_row[0])
        else:
            res = await session.execute(text("SELECT sqlite_version()"))
            row = res.fetchone()
            if row and row[0]:
                version = str(row[0])
            db_size = await get_database_size(session)
            active_connections = 1
    except Exception as e:
        logger.warning(f"Failed to get detailed database info: {e}")
    return version, db_size, active_connections


async def get_redis_detailed_status() -> RedisStatus:
    """Get detailed Redis status including latency, version, and memory."""
    if not REDIS_AVAILABLE or not settings.redis_url:
        return RedisStatus(status="disabled")

    start_time = time.time()
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_timeout=3.0,
        )
        try:
            await r.ping()
            latency = (time.time() - start_time) * 1000
            info = await r.info()

            version = info.get("redis_version")
            connected_clients = info.get("connected_clients")
            used_memory = info.get("used_memory_human")
            uptime_seconds = info.get("uptime_in_seconds")

            return RedisStatus(
                status="ok",
                latency_ms=round(latency, 2),
                version=version,
                connected_clients=connected_clients,
                used_memory=used_memory,
                uptime_seconds=uptime_seconds,
                pool_connections=connected_clients,
            )
        finally:
            await r.aclose()
    except Exception as e:
        logger.error(f"Redis status check failed: {e}")
        return RedisStatus(status="error", latency_ms=None)


def get_disk_usage() -> DiskUsage:
    """Get disk usage for the application directory."""
    try:
        total, used, free = shutil.disk_usage("/")
        total_gb = total / (1024**3)
        used_gb = used / (1024**3)
        free_gb = free / (1024**3)
        percent_used = (used / total) * 100

        return DiskUsage(
            total_gb=round(total_gb, 2),
            used_gb=round(used_gb, 2),
            free_gb=round(free_gb, 2),
            percent_used=round(percent_used, 2),
        )
    except Exception as e:
        logger.warning(f"Failed to get disk usage: {e}")
        return DiskUsage(total_gb=0, used_gb=0, free_gb=0, percent_used=0)


def get_memory_usage() -> MemoryUsage:
    """Get memory usage."""
    try:
        import psutil

        mem = psutil.virtual_memory()
        total_gb = mem.total / (1024**3)
        available_gb = mem.available / (1024**3)
        used_gb = mem.used / (1024**3)

        return MemoryUsage(
            total_gb=round(total_gb, 2),
            available_gb=round(available_gb, 2),
            used_gb=round(used_gb, 2),
            percent_used=round(mem.percent, 2),
        )
    except Exception:
        pass

    # Linux /proc/meminfo fallback for container environments
    try:
        if os.path.exists("/proc/meminfo"):
            meminfo = {}
            with open("/proc/meminfo") as f:
                for line in f:
                    parts = line.split(":")
                    if len(parts) == 2:
                        meminfo[parts[0].strip()] = parts[1].strip()
            total_kb = float(meminfo.get("MemTotal", "0 kB").split()[0])
            avail_kb = float(
                meminfo.get("MemAvailable", meminfo.get("MemFree", "0 kB")).split()[0]
            )
            used_kb = max(0.0, total_kb - avail_kb)
            total_gb = total_kb / (1024 * 1024)
            available_gb = avail_kb / (1024 * 1024)
            used_gb = used_kb / (1024 * 1024)
            percent = (used_kb / total_kb * 100) if total_kb > 0 else 0.0
            return MemoryUsage(
                total_gb=round(total_gb, 2),
                available_gb=round(available_gb, 2),
                used_gb=round(used_gb, 2),
                percent_used=round(percent, 2),
            )
    except Exception as e:
        logger.warning(f"Failed to get memory usage: {e}")

    return MemoryUsage(total_gb=0, used_gb=0, available_gb=0, percent_used=0)


def get_cpu_percent() -> float:
    """Get CPU usage percentage."""
    try:
        import psutil

        return round(psutil.cpu_percent(interval=0.1), 2)
    except Exception:
        pass

    # Linux /proc/stat fallback
    try:
        if os.path.exists("/proc/stat"):
            with open("/proc/stat") as f:
                fields1 = [float(x) for x in f.readline().split()[1:]]
            idle1 = fields1[3] + (fields1[4] if len(fields1) > 4 else 0.0)
            total1 = sum(fields1)

            time.sleep(0.05)

            with open("/proc/stat") as f:
                fields2 = [float(x) for x in f.readline().split()[1:]]
            idle2 = fields2[3] + (fields2[4] if len(fields2) > 4 else 0.0)
            total2 = sum(fields2)

            d_total = total2 - total1
            d_idle = idle2 - idle1
            if d_total > 0:
                cpu = max(0.0, min(100.0, 100.0 * (1.0 - d_idle / d_total)))
                return round(cpu, 2)
    except Exception as e:
        logger.warning(f"Failed to get CPU percent: {e}")

    return 0.0


async def get_ai_models_status(session: AsyncSession) -> list[AIModelStatus]:
    """Get status of all AI models."""
    try:
        from sqlalchemy import select

        from models.ai_model import AIModelModel

        result = await session.execute(
            select(AIModelModel).order_by(
                AIModelModel.is_default.desc(), AIModelModel.display_name.asc()
            )
        )
        models = result.scalars().all()

        return [
            AIModelStatus(
                id=str(m.id),
                name=m.display_name,
                provider=m.provider,
                is_active=bool(m.enabled),
                last_used=(
                    str(m.updated_at)
                    if hasattr(m, "updated_at") and m.updated_at
                    else None
                ),
                total_requests=getattr(m, "total_requests", 0) or 0,
            )
            for m in models
        ]
    except Exception as e:
        logger.warning(f"Failed to get AI models status: {e}")
        return []


def get_system_features() -> dict[str, bool]:
    """Get status of feature flags."""
    has_ai = bool(
        getattr(settings, "openai_api_key", None)
        or getattr(settings, "zhipu_api_key", None)
        or getattr(settings, "nvidia_api_key", None)
        or getattr(settings, "anthropic_api_key", None)
        or getattr(settings, "moonshot_api_key", None)
        or getattr(settings, "openrouter_api_key", None)
    )
    has_ti = bool(
        getattr(settings, "otx_api_key", None)
        or getattr(settings, "virustotal_api_key", None)
        or getattr(settings, "misp_api_key", None)
        or getattr(settings, "abuseipdb_api_key", None)
    )
    return {
        "redis_enabled": REDIS_AVAILABLE and bool(settings.redis_url),
        "ai_copilot": has_ai,
        "threat_intel": has_ti,
        "audit_archive": True,
        "websocket": True,
        "rate_limiting": True,
        "csrf_protection": True,
        "idempotency": True,
    }


# ==================== Endpoints ====================


@router.get(
    "/dashboard", response_model=SystemDashboard, summary="Get full system dashboard"
)
async def get_system_dashboard(
    current_user: UserModel = Depends(get_current_user),
):
    """Get comprehensive system health dashboard.

    **Requires:** Authenticated user (admin recommended)

    **Returns:**
    - Database status with connection pool info
    - Redis status with memory usage
    - AI models availability
    - System resources (CPU, memory, disk)
    - Feature flags status
    """
    start_time = time.time()

    # Check database
    db_status = "ok"
    db_latency = 0.0
    db_version = None
    db_size = None
    db_conns = None

    try:
        db_start = time.time()
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            db_latency = (time.time() - db_start) * 1000
            db_version, db_size, db_conns = await get_database_info(session)
    except Exception as e:
        logger.error(f"Database check failed: {e}")
        db_status = "error"

    database_status = DatabaseStatus(
        status=db_status,
        latency_ms=round(db_latency, 2),
        pool=get_database_pool_status(),
        version=db_version,
        database_size=db_size,
        active_connections=db_conns,
    )

    # Check Redis
    redis_status_model = await get_redis_detailed_status()

    # Get AI models
    async with AsyncSessionLocal() as session:
        ai_models = await get_ai_models_status(session)

    # System stats
    system_stats = SystemStats(
        cpu_percent=get_cpu_percent(),
        memory=get_memory_usage(),
        disk=get_disk_usage(),
        uptime_seconds=round(time.time() - _startup_time, 2),
        platform=platform.platform(),
        python_version=platform.python_version(),
    )

    # Feature flags
    features = get_system_features()

    total_latency = (time.time() - start_time) * 1000
    logger.info(
        "System dashboard generated",
        extra={
            "user_id": current_user.id,
            "latency_ms": round(total_latency, 2),
        },
    )

    return SystemDashboard(
        timestamp=datetime.now(UTC).isoformat(),
        version=settings.app_version,
        environment=settings.environment,
        database=database_status,
        redis=redis_status_model,
        ai_models=ai_models,
        system=system_stats,
        features=features,
    )


@router.get("/database", response_model=DatabaseStatus, summary="Get database status")
async def get_database_status(
    current_user: UserModel = Depends(get_current_user),
):
    """Get detailed database status including connection pool."""
    start_time = time.time()
    status = "ok"
    version = None
    db_size = None
    active_connections = None
    latency = 0.0

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            latency = (time.time() - start_time) * 1000
            version, db_size, active_connections = await get_database_info(session)
    except Exception as e:
        status = "error"
        logger.error(f"Database status check failed: {e}")

    return DatabaseStatus(
        status=status,
        latency_ms=round(latency, 2),
        pool=get_database_pool_status(),
        version=version,
        database_size=db_size,
        active_connections=active_connections,
    )


@router.get("/redis", response_model=RedisStatus, summary="Get Redis status")
async def get_redis_status(
    current_user: UserModel = Depends(get_current_user),
):
    """Get detailed Redis status."""
    return await get_redis_detailed_status()


@router.get("/resources", response_model=SystemStats, summary="Get system resources")
async def get_system_resources(
    current_user: UserModel = Depends(get_current_user),
):
    """Get system resource usage (CPU, memory, disk)."""
    return SystemStats(
        cpu_percent=get_cpu_percent(),
        memory=get_memory_usage(),
        disk=get_disk_usage(),
        uptime_seconds=round(time.time() - _startup_time, 2),
        platform=platform.platform(),
        python_version=platform.python_version(),
    )


@router.get("/features", summary="Get feature flags")
async def get_feature_flags(
    current_user: UserModel = Depends(get_current_user),
):
    """Get current feature flag status."""
    return get_system_features()


class ReplayDLQRequest(BaseModel):
    target_stream: str = "events:medium"
    limit: int = 100


@router.get("/queue/stats", summary="Get Redis Streams queue and DLQ stats")
async def get_queue_dashboard_stats(
    current_user: UserModel = Depends(get_current_user),
):
    """Get Redis Streams queue statistics, consumer lag and DLQ status."""
    from services.message_broker import get_message_broker

    broker = get_message_broker()
    stats = broker.get_queue_stats()
    health = broker.health_check()
    return {
        "status": "ok" if health.get("streams", True) else "degraded",
        "health": health,
        "queues": stats,
    }


@router.post("/queue/dlq/replay", summary="Replay dead-letter queue (DLQ) messages")
async def replay_dlq_messages(
    request: ReplayDLQRequest,
    current_user: UserModel = Depends(get_current_user),
):
    """Replay messages from DLQ (events:dlq) back to active processing stream."""
    from services.message_broker import get_message_broker

    broker = get_message_broker()
    replayed = await broker.replay_dlq(
        "events:dlq", request.target_stream, limit=request.limit
    )
    return {
        "status": "success",
        "replayed_count": replayed,
        "target_stream": request.target_stream,
    }


async def get_db_connections_detail(session: AsyncSession) -> DBConnectionsDetail:
    """Retrieve detailed database connection statistics and active query list."""
    is_postgres = "postgresql" in str(engine.url)
    pool_status = get_database_pool_status()
    pool_utilization = 0.0
    if pool_status and pool_status.size > 0:
        pool_utilization = round((pool_status.checked_out / pool_status.size) * 100, 1)

    if not is_postgres:
        return DBConnectionsDetail(
            engine="sqlite",
            summary={
                "active": 1,
                "idle": 0,
                "idle_in_transaction": 0,
                "waiting": 0,
                "total": 1,
            },
            pool=pool_status,
            pool_utilization=pool_utilization,
            connections=[
                DBConnectionItem(
                    pid=1,
                    usename="sqlite_user",
                    client_addr="local",
                    state="active",
                    duration_seconds=0.0,
                    query="SQLite connection pool active",
                )
            ],
        )

    summary: dict[str, int] = {
        "active": 0,
        "idle": 0,
        "idle_in_transaction": 0,
        "waiting": 0,
        "total": 0,
    }
    connections: list[DBConnectionItem] = []

    try:
        res_summary = await session.execute(
            text(
                "SELECT coalesce(state, 'unknown') as st, count(*) "
                "FROM pg_stat_activity WHERE datname = current_database() "
                "GROUP BY state"
            )
        )
        for st, cnt in res_summary.fetchall():
            cnt = int(cnt)
            summary["total"] += cnt
            if "idle in transaction" in st:
                summary["idle_in_transaction"] += cnt
            elif "active" in st:
                summary["active"] += cnt
            elif "idle" in st:
                summary["idle"] += cnt
            else:
                summary["waiting"] += cnt

        query_sql = text("""
            SELECT 
                pid, 
                coalesce(usename, '') as usename,
                coalesce(client_addr::text, 'local') as client_addr,
                coalesce(state, 'unknown') as state,
                case 
                    when query_start is not null then round(extract(epoch from (clock_timestamp() - query_start))::numeric, 2)
                    when state_change is not null then round(extract(epoch from (clock_timestamp() - state_change))::numeric, 2)
                    else 0.0 
                end as duration_seconds,
                wait_event_type,
                wait_event,
                substring(coalesce(query, '') from 1 for 120) as query
            FROM pg_stat_activity
            WHERE datname = current_database()
            ORDER BY 
                case when state = 'active' then 1 when state = 'idle in transaction' then 2 else 3 end,
                duration_seconds desc
            LIMIT 30
        """)
        res_conns = await session.execute(query_sql)
        for row in res_conns.fetchall():
            m = row._mapping
            dur = float(m["duration_seconds"] or 0.0)
            st = str(m["state"])
            is_slow = st == "active" and dur > 3.0
            is_idle_tx = "idle in transaction" in st and dur > 5.0
            connections.append(
                DBConnectionItem(
                    pid=int(m["pid"]),
                    usename=str(m["usename"]),
                    client_addr=str(m["client_addr"]),
                    state=st,
                    duration_seconds=dur,
                    wait_event_type=m["wait_event_type"],
                    wait_event=m["wait_event"],
                    query=str(m["query"]).strip(),
                    is_slow=is_slow,
                    is_idle_tx=is_idle_tx,
                )
            )
    except Exception as e:
        logger.error(f"Failed to query pg_stat_activity: {e}")

    return DBConnectionsDetail(
        engine="postgresql",
        summary=summary,
        pool=pool_status,
        pool_utilization=pool_utilization,
        connections=connections,
    )


async def get_redis_connections_detail() -> RedisConnectionsDetail:
    """Retrieve detailed Redis client list and Queue/Streams status."""
    if not REDIS_AVAILABLE or not settings.redis_url:
        return RedisConnectionsDetail(
            status="disabled",
            summary={"status": "disabled"},
            clients=[],
            queue={},
        )

    summary: dict[str, Any] = {}
    clients: list[RedisClientItem] = []
    queue_data: dict[str, Any] = {}

    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_timeout=3.0,
        )
        try:
            info = await r.info()
            clients_raw = await r.client_list()

            hits = int(info.get("keyspace_hits", 0))
            misses = int(info.get("keyspace_misses", 0))
            total_ops = hits + misses
            hit_rate = round((hits / total_ops * 100), 1) if total_ops > 0 else 100.0

            pubsub_count = sum(
                1
                for c in clients_raw
                if int(c.get("sub", 0)) > 0 or int(c.get("psub", 0)) > 0
            )

            summary = {
                "connected_clients": int(
                    info.get("connected_clients", len(clients_raw))
                ),
                "pubsub_clients": pubsub_count,
                "blocked_clients": int(info.get("blocked_clients", 0)),
                "max_clients": int(info.get("maxclients", 10000)),
                "used_memory": info.get("used_memory_human", "0M"),
                "peak_memory": info.get("used_memory_peak_human", "0M"),
                "fragmentation_ratio": float(info.get("mem_fragmentation_ratio", 1.0)),
                "hit_rate_percent": hit_rate,
            }

            for c in clients_raw[:30]:
                clients.append(
                    RedisClientItem(
                        id=str(c.get("id", "")),
                        addr=str(c.get("addr", "")),
                        age_seconds=int(c.get("age", 0)),
                        idle_seconds=int(c.get("idle", 0)),
                        cmd=str(c.get("cmd", "")),
                        flags=str(c.get("flags", "")),
                        name=str(c.get("name", "")),
                    )
                )
        finally:
            await r.aclose()
    except Exception as e:
        logger.error(f"Failed to query Redis client list: {e}")
        summary = {"error": str(e)}

    # Queue status from broker
    try:
        from services.message_broker import get_message_broker

        broker = get_message_broker()
        queue_data = {
            "health": broker.health_check(),
            "queues": broker.get_queue_stats(),
        }
    except Exception as e:
        queue_data = {"error": str(e)}

    return RedisConnectionsDetail(
        status="ok" if "error" not in summary else "error",
        summary=summary,
        clients=clients,
        queue=queue_data,
    )


async def get_system_integrations_detail() -> SystemIntegrationsDetail:
    """Retrieve status of integrations: WebSocket, Wazuh, Threat Intel, AI."""
    ws_conns = 0
    try:
        from services.websocket_manager import get_websocket_manager

        ws_mgr = get_websocket_manager()
        ws_conns = (
            ws_mgr.get_active_connections_count()
            if hasattr(ws_mgr, "get_active_connections_count")
            else len(getattr(ws_mgr, "_active_connections", {}))
        )
    except Exception:
        pass

    wazuh_info = {
        "enabled": bool(getattr(settings, "wazuh_enabled", False)),
        "api_url": getattr(settings, "wazuh_api_url", "") or "Not configured",
    }

    threat_intel = {
        "otx": bool(getattr(settings, "otx_api_key", None)),
        "virustotal": bool(getattr(settings, "virustotal_api_key", None)),
        "misp": bool(getattr(settings, "misp_api_key", None)),
        "abuseipdb": bool(getattr(settings, "abuseipdb_api_key", None)),
    }

    ai_count = 0
    try:
        async with AsyncSessionLocal() as session:
            ai_list = await get_ai_models_status(session)
            ai_count = len(ai_list)
    except Exception:
        pass

    return SystemIntegrationsDetail(
        websocket_connections=ws_conns,
        wazuh=wazuh_info,
        threat_intel=threat_intel,
        ai_models_count=ai_count,
    )


def compute_health_score_and_warnings(
    db_detail: DBConnectionsDetail,
    redis_detail: RedisConnectionsDetail,
    system_stats: SystemStats,
) -> tuple[int, list[str]]:
    """Compute overall system health score (0-100) and actionable warnings."""
    score = 100
    warnings: list[str] = []

    # CPU check
    if system_stats.cpu_percent > 85:
        score -= 15
        warnings.append(f"CPU 使用率较高 ({system_stats.cpu_percent}%)")
    elif system_stats.cpu_percent > 70:
        score -= 5

    # Memory check
    if system_stats.memory.percent_used > 85:
        score -= 15
        warnings.append(f"系统内存使用率较高 ({system_stats.memory.percent_used}%)")
    elif system_stats.memory.percent_used > 70:
        score -= 5

    # Disk check
    if system_stats.disk.percent_used > 85:
        score -= 15
        warnings.append(f"磁盘剩余空间偏低 ({system_stats.disk.free_gb} GB 可用)")

    # Database checks
    if db_detail.pool_utilization > 80:
        score -= 10
        warnings.append(f"数据库连接池利用率高达 {db_detail.pool_utilization}%")

    slow_queries = sum(1 for c in db_detail.connections if c.is_slow)
    if slow_queries > 0:
        score -= 8
        warnings.append(f"检测到 {slow_queries} 个耗时超过 3 秒的数据库活跃查询")

    idle_tx = sum(1 for c in db_detail.connections if c.is_idle_tx)
    if idle_tx > 0:
        score -= 10
        warnings.append(
            f"检测到 {idle_tx} 个处于事务中空闲 (idle in transaction) 的阻塞连接"
        )

    # Redis and Queue checks
    dlq_pending = 0
    queues = redis_detail.queue.get("queues", {})
    if isinstance(queues, dict) and "dlq" in queues:
        dlq_pending = int(
            queues["dlq"].get("pending", 0) or queues["dlq"].get("length", 0)
        )
    if dlq_pending > 0:
        score -= 10
        warnings.append(f"死信队列 (DLQ) 积压了 {dlq_pending} 条未处理的失败事件")

    if redis_detail.status != "ok" and redis_detail.status != "disabled":
        score -= 20
        warnings.append("Redis 服务状态异常")

    return max(10, min(100, score)), warnings


@router.get(
    "/connections",
    response_model=ConnectionsDashboardResponse,
    summary="Get detailed data connection statistics",
)
async def get_system_connections(
    current_user: UserModel = Depends(get_current_user),
):
    """Get complete connection transparency for PostgreSQL, Redis, and Integrations."""
    async with AsyncSessionLocal() as session:
        db_detail = await get_db_connections_detail(session)

    redis_detail = await get_redis_connections_detail()
    integrations_detail = await get_system_integrations_detail()

    sys_stats = SystemStats(
        cpu_percent=get_cpu_percent(),
        memory=get_memory_usage(),
        disk=get_disk_usage(),
        uptime_seconds=round(time.time() - _startup_time, 2),
        platform=platform.platform(),
        python_version=platform.python_version(),
    )

    health_score, warnings = compute_health_score_and_warnings(
        db_detail, redis_detail, sys_stats
    )

    return ConnectionsDashboardResponse(
        timestamp=datetime.now(UTC).isoformat(),
        health_score=health_score,
        warnings=warnings,
        database=db_detail,
        redis=redis_detail,
        integrations=integrations_detail,
    )


@router.post(
    "/connections/db/{pid}/terminate",
    summary="Terminate a stuck database connection",
)
async def terminate_db_connection(
    pid: int,
    current_user: UserModel = Depends(get_current_user),
):
    """Terminate a stuck or long-running database connection by PID (admin only)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin permission required")

    if "postgresql" not in str(engine.url):
        return {
            "status": "skipped",
            "message": "Connection termination is only available for PostgreSQL",
        }

    try:
        async with AsyncSessionLocal() as session:
            check = await session.execute(
                text(
                    "SELECT pid, pg_backend_pid() as my_pid "
                    "FROM pg_stat_activity WHERE pid = :pid"
                ),
                {"pid": pid},
            )
            row = check.fetchone()
            if not row:
                raise HTTPException(
                    status_code=404, detail=f"Connection PID {pid} not found"
                )
            if row[0] == row[1]:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot terminate current query backend connection",
                )

            term_res = await session.execute(
                text("SELECT pg_terminate_backend(:pid)"),
                {"pid": pid},
            )
            term_row = term_res.fetchone()
            success = bool(term_row[0]) if term_row else False
            return {
                "status": "success" if success else "failed",
                "pid": pid,
                "message": (
                    f"Connection {pid} terminated successfully"
                    if success
                    else f"Failed to terminate connection {pid}"
                ),
            }
    except HTTPException:
        raise
    except Exception:
        logger.exception(f"Failed to terminate connection {pid}")
        raise HTTPException(
            status_code=500, detail=f"Failed to terminate connection {pid}"
        )


@router.post(
    "/diagnostics/ping",
    response_model=DiagnosticsResponse,
    summary="Run live diagnostics on all core components",
)
async def run_system_diagnostics(
    current_user: UserModel = Depends(get_current_user),
):
    """Run real-time active ping diagnostics across core system components."""
    results: list[DiagnosticItem] = []

    # 1. Database
    try:
        t0 = time.time()
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        db_ms = round((time.time() - t0) * 1000, 2)
        results.append(
            DiagnosticItem(
                name="Database (PostgreSQL)",
                status="ok" if db_ms < 50 else "warn",
                latency_ms=db_ms,
                message=f"Connected successfully ({db_ms}ms)",
            )
        )
    except Exception as e:
        results.append(
            DiagnosticItem(
                name="Database (PostgreSQL)",
                status="error",
                latency_ms=None,
                message=f"Database unreachable: {e}",
            )
        )

    # 2. Redis
    if REDIS_AVAILABLE and settings.redis_url:
        try:
            import redis.asyncio as aioredis

            t0 = time.time()
            r = aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_timeout=3.0,
            )
            try:
                await r.ping()
                r_ms = round((time.time() - t0) * 1000, 2)
                results.append(
                    DiagnosticItem(
                        name="Cache & Memory (Redis)",
                        status="ok" if r_ms < 20 else "warn",
                        latency_ms=r_ms,
                        message=f"Connected successfully ({r_ms}ms)",
                    )
                )
            finally:
                await r.aclose()
        except Exception as e:
            results.append(
                DiagnosticItem(
                    name="Cache & Memory (Redis)",
                    status="error",
                    latency_ms=None,
                    message=f"Redis unreachable: {e}",
                )
            )
    else:
        results.append(
            DiagnosticItem(
                name="Cache & Memory (Redis)",
                status="warn",
                latency_ms=None,
                message="Redis not configured or disabled",
            )
        )

    # 3. Message Broker
    try:
        from services.message_broker import get_message_broker

        broker = get_message_broker()
        health = broker.health_check()
        streams_healthy = health.get("streams", True)
        results.append(
            DiagnosticItem(
                name="Message Broker (Streams & DLQ)",
                status="ok" if streams_healthy else "warn",
                latency_ms=None,
                message=(
                    "All Streams online, event queues healthy"
                    if streams_healthy
                    else "Message broker operating in degraded mode"
                ),
            )
        )
    except Exception as e:
        results.append(
            DiagnosticItem(
                name="Message Broker (Streams & DLQ)",
                status="error",
                latency_ms=None,
                message=f"Broker check failed: {e}",
            )
        )

    # 4. AI Provider
    has_ai = bool(
        getattr(settings, "zhipu_api_key", None)
        or getattr(settings, "nvidia_api_key", None)
        or getattr(settings, "openai_api_key", None)
        or getattr(settings, "anthropic_api_key", None)
    )
    if has_ai:
        provider = getattr(settings, "ai_provider", "configured")
        results.append(
            DiagnosticItem(
                name=f"AI Copilot ({provider.capitalize()})",
                status="ok",
                latency_ms=None,
                message=f"API key configured and ready for {provider}",
            )
        )
    else:
        results.append(
            DiagnosticItem(
                name="AI Copilot",
                status="warn",
                latency_ms=None,
                message="No AI provider API key configured",
            )
        )

    has_error = any(item.status == "error" for item in results)
    has_warn = any(item.status == "warn" for item in results)
    overall = "error" if has_error else ("warn" if has_warn else "ok")

    return DiagnosticsResponse(
        timestamp=datetime.now(UTC).isoformat(),
        overall_status=overall,
        items=results,
    )


# Track startup time
_startup_time = time.time()
