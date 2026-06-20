"""
Enhanced health check and metrics endpoints.

Provides:
- /health/live - Liveness probe (simple check)
- /health/ready - Readiness probe (checks DB, Redis)
- /api/health - Detailed health check with all components
- /metrics - Prometheus metrics endpoint
"""

import time
from datetime import UTC, datetime

from fastapi import APIRouter, Response
from pydantic import BaseModel
from sqlalchemy import text

from core.config import settings
from core.logger import get_logger
from core.token_blacklist import REDIS_AVAILABLE, get_token_blacklist
from db.session import AsyncSessionLocal

logger = get_logger(__name__)

router = APIRouter(tags=["health"])


class HealthStatus(BaseModel):
    """Health status response model."""

    status: str  # "ok", "degraded", "error"
    version: str
    timestamp: str
    uptime_seconds: float
    components: dict


class ComponentHealth(BaseModel):
    """Individual component health."""

    status: str  # "ok", "error", "disabled"
    latency_ms: float | None = None
    message: str | None = None
    details: dict | None = None


# Track startup time
_startup_time = time.time()


async def check_database() -> ComponentHealth:
    """Check database connectivity."""
    start = time.time()
    try:
        async with AsyncSessionLocal() as session:
            # Simple query to check connection
            result = await session.execute(text("SELECT 1"))
            result.fetchone()

        latency = (time.time() - start) * 1000
        return ComponentHealth(
            status="ok",
            latency_ms=round(latency, 2),
            message="Database connection successful",
        )
    except Exception as e:
        latency = (time.time() - start) * 1000
        logger.error(f"Database health check failed: {e}")
        return ComponentHealth(
            status="error",
            latency_ms=round(latency, 2),
            message=f"Database connection failed: {str(e)[:100]}",
        )


async def check_redis() -> ComponentHealth:
    """Check Redis connectivity."""
    if not REDIS_AVAILABLE:
        return ComponentHealth(
            status="disabled",
            message="Redis package not installed, using in-memory fallback",
        )

    if not settings.redis_url:
        return ComponentHealth(
            status="disabled",
            message="Redis not configured, using in-memory fallback",
        )

    start = time.time()
    try:
        blacklist = get_token_blacklist()
        info = await blacklist.get_blacklist_info()

        latency = (time.time() - start) * 1000
        if info.get("redis_available"):
            return ComponentHealth(
                status="ok",
                latency_ms=round(latency, 2),
                message="Redis connection successful",
                details={"backend": "redis"},
            )
        else:
            return ComponentHealth(
                status="degraded",
                latency_ms=round(latency, 2),
                message="Redis configured but not connected, using fallback",
            )
    except Exception as e:
        latency = (time.time() - start) * 1000
        logger.error(f"Redis health check failed: {e}")
        return ComponentHealth(
            status="error",
            latency_ms=round(latency, 2),
            message=f"Redis check failed: {str(e)[:100]}",
        )


async def check_token_blacklist() -> ComponentHealth:
    """Check token blacklist status."""
    try:
        blacklist = get_token_blacklist()
        info = await blacklist.get_blacklist_info()

        return ComponentHealth(
            status="ok",
            message="Token blacklist operational",
            details=info,
        )
    except Exception as e:
        logger.error(f"Token blacklist health check failed: {e}")
        return ComponentHealth(
            status="error",
            message=f"Token blacklist error: {str(e)[:100]}",
        )


@router.get("/health/live")
async def liveness() -> dict:
    """Liveness probe - checks if the service is running.

    Used by Kubernetes to determine if the container should be restarted.
    """
    return {"status": "alive"}


@router.get("/health/ready")
async def readiness() -> dict:
    """Readiness probe - checks if the service is ready to accept traffic.

    Used by Kubernetes to determine if the container should receive requests.
    """
    # Check database
    db_health = await check_database()

    if db_health.status == "error":
        return {
            "status": "not_ready",
            "reason": "database_unavailable",
            "message": db_health.message,
        }

    return {"status": "ready"}


@router.get("/api/health")
async def health_detailed() -> HealthStatus:
    """Detailed health check with all components.

    Returns comprehensive status of all system components.
    """
    # Check all components
    db_health = await check_database()
    redis_health = await check_redis()
    blacklist_health = await check_token_blacklist()

    # Determine overall status
    components = {
        "database": db_health.model_dump(),
        "redis": redis_health.model_dump(),
        "token_blacklist": blacklist_health.model_dump(),
    }

    # Calculate overall status
    statuses = [c["status"] for c in components.values()]
    if "error" in statuses:
        overall_status = "error"
    elif "degraded" in statuses:
        overall_status = "degraded"
    else:
        overall_status = "ok"

    return HealthStatus(
        status=overall_status,
        version="0.9.0",
        timestamp=datetime.now(UTC).isoformat(),
        uptime_seconds=round(time.time() - _startup_time, 2),
        components=components,
    )


# Prometheus metrics
METRICS_TEMPLATE = """# HELP soc_copilot_info Application information
# TYPE soc_copilot_info gauge
soc_copilot_info{{version="0.9.0",environment="{environment}"}} 1

# HELP soc_copilot_uptime_seconds Application uptime in seconds
# TYPE soc_copilot_uptime_seconds gauge
soc_copilot_uptime_seconds {uptime}

# HELP soc_copilot_health_status Health status (1=ok, 0.5=degraded, 0=error)
# TYPE soc_copilot_health_status gauge
soc_copilot_health_status{{component="database"}} {db_status}
soc_copilot_health_status{{component="redis"}} {redis_status}
soc_copilot_health_status{{component="token_blacklist"}} {blacklist_status}

# HELP soc_copilot_db_latency_ms Database query latency in milliseconds
# TYPE soc_copilot_db_latency_ms gauge
soc_copilot_db_latency_ms {db_latency}

# HELP soc_copilot_redis_latency_ms Redis query latency in milliseconds
# TYPE soc_copilot_redis_latency_ms gauge
soc_copilot_redis_latency_ms {redis_latency}
"""


def status_to_metric(status: str) -> float:
    """Convert status string to metric value."""
    return {"ok": 1.0, "degraded": 0.5, "error": 0.0, "disabled": 1.0}.get(status, 0.0)


@router.get("/metrics")
async def metrics() -> Response:
    """Prometheus metrics endpoint.

    Returns metrics in Prometheus text format.
    """
    # Get health data
    db_health = await check_database()
    redis_health = await check_redis()
    blacklist_health = await check_token_blacklist()

    metrics_text = METRICS_TEMPLATE.format(
        environment=settings.environment,
        uptime=round(time.time() - _startup_time, 2),
        db_status=status_to_metric(db_health.status),
        redis_status=status_to_metric(redis_health.status),
        blacklist_status=status_to_metric(blacklist_health.status),
        db_latency=db_health.latency_ms or 0,
        redis_latency=redis_health.latency_ms or 0,
    )

    return Response(
        content=metrics_text,
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
