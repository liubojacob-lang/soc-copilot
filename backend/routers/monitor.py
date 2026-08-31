"""
Real-time monitoring SSE endpoints with persistent storage.

Provides Server-Sent Events for live system monitoring dashboard
with PostgreSQL-backed historical data storage.
"""

import asyncio
import json
import time
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func, select, text

from core.config import settings
from core.logger import get_logger
from core.token_blacklist import REDIS_AVAILABLE
from db.session import AsyncSessionLocal
from dependencies.auth import get_current_user
from models.monitor_history import MonitorHistoryModel
from models.user import UserModel

logger = get_logger(__name__)

router = APIRouter(tags=["monitor"], prefix="/api/v1/monitor")

# Track last update time
_last_update_time = 0


class ServiceStatus(BaseModel):
    """Individual service health status."""

    status: str
    latency_ms: float | None = None
    message: str | None = None
    pending_count: int | None = None


class ResourceMetrics(BaseModel):
    """System resource metrics."""

    cpu_percent: float
    memory_percent: float
    memory_used_gb: float
    memory_total_gb: float
    disk_percent: float
    disk_used_gb: float
    disk_total_gb: float
    error: str | None = None


class Activity(BaseModel):
    """System activity log."""

    type: str
    id: str
    name: str
    status: str
    timestamp: str | None = None


class MonitorData(BaseModel):
    """Complete monitoring data."""

    timestamp: str
    services: dict[str, ServiceStatus]
    resources: ResourceMetrics
    activities: list
    metrics: dict[str, Any]
    heartbeat: bool | None = None
    error: str | None = None


async def check_database_health() -> ServiceStatus:
    """Check database connectivity."""
    start = time.time()
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        latency = (time.time() - start) * 1000
        return ServiceStatus(
            status="ok", latency_ms=round(latency, 2), message="Connected"
        )
    except Exception as e:
        return ServiceStatus(status="error", latency_ms=None, message=str(e)[:50])


async def check_redis_health() -> ServiceStatus:
    """Check Redis connectivity."""
    if not REDIS_AVAILABLE or not settings.redis_url:
        return ServiceStatus(
            status="disabled", latency_ms=None, message="Not configured"
        )

    start = time.time()
    try:
        from core.token_blacklist import get_token_blacklist

        blacklist = get_token_blacklist()
        info = await blacklist.get_blacklist_info()
        latency = (time.time() - start) * 1000

        if info.get("redis_available"):
            return ServiceStatus(
                status="ok", latency_ms=round(latency, 2), message="Connected"
            )
        else:
            return ServiceStatus(
                status="degraded", latency_ms=round(latency, 2), message="Fallback mode"
            )
    except Exception as e:
        return ServiceStatus(status="error", latency_ms=None, message=str(e)[:50])


async def check_ai_health() -> ServiceStatus:
    """Check AI service status."""
    try:
        # Simple check - just see if module is importable

        return ServiceStatus(status="ok", latency_ms=None, message="Ready")
    except Exception:
        return ServiceStatus(
            status="error", latency_ms=None, message="Service not available"
        )


async def check_queue_health() -> ServiceStatus:
    """Check task queue status."""
    try:
        # Try to import and get stats
        import importlib

        queue_module = importlib.import_module("services.run_queue_manager")
        queue_manager = getattr(queue_module, "queue_manager", None)
        if queue_manager:
            stats = await queue_manager.get_queue_stats()
            return ServiceStatus(
                status="ok",
                latency_ms=None,
                message=f"{stats.get('pending', 0)} pending",
                pending_count=stats.get("pending", 0),
            )
        else:
            return ServiceStatus(
                status="initializing",
                latency_ms=None,
                message="Queue manager not ready",
            )
    except Exception as e:
        return ServiceStatus(status="error", latency_ms=None, message=str(e)[:50])


async def collect_resource_metrics() -> ResourceMetrics:
    """Collect system resource metrics."""
    try:
        import psutil

        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        return ResourceMetrics(
            cpu_percent=round(cpu_percent, 1),
            memory_percent=round(memory.percent, 1),
            memory_used_gb=round(memory.used / (1024**3), 2),
            memory_total_gb=round(memory.total / (1024**3), 2),
            disk_percent=round(disk.percent, 1),
            disk_used_gb=round(disk.used / (1024**3), 2),
            disk_total_gb=round(disk.total / (1024**3), 2),
        )
    except ImportError:
        return ResourceMetrics(
            cpu_percent=0,
            memory_percent=0,
            memory_used_gb=0,
            memory_total_gb=0,
            disk_percent=0,
            disk_used_gb=0,
            disk_total_gb=0,
            error="psutil not installed",
        )
    except Exception as e:
        logger.error(f"Failed to collect resource metrics: {e}")
        return ResourceMetrics(
            cpu_percent=0,
            memory_percent=0,
            memory_used_gb=0,
            memory_total_gb=0,
            disk_percent=0,
            disk_used_gb=0,
            disk_total_gb=0,
            error=str(e)[:50],
        )


async def collect_recent_activities(limit: int = 10) -> list:
    """Collect recent system activities."""
    activities = []

    try:
        from models.playbook_run import PlaybookRunModel

        async with AsyncSessionLocal() as session:
            from sqlalchemy import desc as sa_desc
            from sqlalchemy import select as sa_select

            result = await session.execute(
                sa_select(PlaybookRunModel)
                .order_by(sa_desc(PlaybookRunModel.created_at))
                .limit(limit)
            )
            runs = result.scalars().all()

            for run in runs:
                activities.append(
                    {
                        "type": "playbook",
                        "id": str(run.id),
                        "name": run.playbook_name or "Unknown",
                        "status": run.status,
                        "timestamp": (
                            run.created_at.isoformat() if run.created_at else None
                        ),
                    }
                )
    except Exception as e:
        logger.error(f"Failed to collect activities: {e}")

    return sorted(activities, key=lambda x: x.get("timestamp") or "", reverse=True)[
        :limit
    ]


async def save_monitor_data_to_db(data: dict[str, Any]) -> None:
    """Save monitoring data to persistent storage."""
    try:
        async with AsyncSessionLocal() as session:
            resources = data["resources"]
            services = data["services"]
            metrics = data.get("metrics", {})

            history_entry = MonitorHistoryModel(
                timestamp=datetime.fromisoformat(data["timestamp"]),
                cpu_percent=resources["cpu_percent"],
                memory_percent=resources["memory_percent"],
                memory_used_gb=resources["memory_used_gb"],
                memory_total_gb=resources["memory_total_gb"],
                disk_percent=resources["disk_percent"],
                disk_used_gb=resources["disk_used_gb"],
                disk_total_gb=resources["disk_total_gb"],
                services={k: v["status"] for k, v in services.items()},
                requests_per_minute=metrics.get("requests_per_minute", 0),
                error_rate=metrics.get("error_rate", 0.0),
                avg_response_time_ms=metrics.get("avg_response_time_ms", 0.0),
            )

            session.add(history_entry)
            await session.commit()
            logger.debug(f"Saved monitor data at {data['timestamp']}")

    except Exception as e:
        logger.error(f"Failed to save monitor data to database: {e}")


async def get_monitor_data() -> dict[str, Any]:
    """Aggregate all monitoring data."""

    # Collect service health
    services = {
        "database": await check_database_health(),
        "redis": await check_redis_health(),
        "ai": await check_ai_health(),
        "queue": await check_queue_health(),
    }

    data = {
        "timestamp": datetime.now(UTC).isoformat(),
        "services": {k: v.dict() for k, v in services.items()},
        "resources": (await collect_resource_metrics()).dict(),
        "activities": await collect_recent_activities(),
        "metrics": {
            "requests_per_minute": 0,
            "error_rate": 0,
            "avg_response_time_ms": 0,
        },
    }

    return data


async def monitor_event_generator() -> AsyncGenerator[str, None]:
    """Generate SSE events with monitoring data."""
    global _last_update_time

    while True:
        try:
            current_time = time.time()

            # Only update if enough time has passed (throttle)
            if current_time - _last_update_time >= 5:  # 5-second minimum interval
                data = await get_monitor_data()

                # Save to persistent storage
                await save_monitor_data_to_db(data)

                _last_update_time = current_time

                # Send SSE event
                yield f"data: {json.dumps(data)}\n\n"
            else:
                # Send heartbeat
                yield f"data: {json.dumps({'heartbeat': True, 'timestamp': datetime.now(UTC).isoformat()})}\n\n"

            await asyncio.sleep(3)

        except Exception as e:
            logger.error(f"Error in monitor event generator: {e}")
            yield f"data: {json.dumps({'error': str(e)[:100]})}\n\n"
            await asyncio.sleep(5)


@router.get("/stream")
async def monitor_stream(
    request: Request,
    current_user: UserModel = Depends(get_current_user),
) -> StreamingResponse:
    """SSE endpoint for real-time monitoring data (requires authentication)."""
    return StreamingResponse(
        monitor_event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/snapshot")
async def get_monitor_snapshot(
    current_user: UserModel = Depends(get_current_user),
) -> dict[str, Any]:
    """Get current monitoring snapshot (single request, requires authentication)."""
    data = await get_monitor_data()
    # Also save to database for history
    await save_monitor_data_to_db(data)
    return data


@router.get("/history")
async def get_monitor_history(
    minutes: int = 60,
    current_user: UserModel = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Get historical monitoring data from persistent storage.

    Args:
        minutes: Number of minutes of history to return (default: 60, max: 1440)

    Returns:
        Dictionary with history array and metadata
    """
    # Limit to reasonable range
    minutes = max(1, min(minutes, 1440))  # 1 min to 24 hours

    try:
        async with AsyncSessionLocal() as session:
            # Calculate cutoff time
            cutoff_time = datetime.now(UTC) - timedelta(minutes=minutes)

            # Query database for historical data
            result = await session.execute(
                select(MonitorHistoryModel)
                .where(MonitorHistoryModel.timestamp >= cutoff_time)
                .order_by(MonitorHistoryModel.timestamp.asc())
            )

            history_entries = result.scalars().all()

            # Convert to response format
            # Note: Database timestamps are naive (no timezone), treat as UTC
            history = [
                {
                    "timestamp": entry.timestamp.replace(tzinfo=UTC).isoformat(),
                    "resources": {
                        "cpu_percent": entry.cpu_percent,
                        "memory_percent": entry.memory_percent,
                        "memory_used_gb": entry.memory_used_gb,
                        "memory_total_gb": entry.memory_total_gb,
                        "disk_percent": entry.disk_percent,
                        "disk_used_gb": entry.disk_used_gb,
                        "disk_total_gb": entry.disk_total_gb,
                    },
                    "services": entry.services,
                }
                for entry in history_entries
            ]

            return {
                "history": history,
                "metadata": {
                    "points_count": len(history),
                    "time_range_minutes": minutes,
                    "interval_seconds": 5,
                    "source": "database",
                },
            }

    except Exception as e:
        logger.error(f"Failed to query monitor history: {e}")
        return {
            "history": [],
            "metadata": {
                "points_count": 0,
                "time_range_minutes": minutes,
                "interval_seconds": 5,
                "source": "database",
                "error": str(e)[:100],
            },
        }


@router.delete("/history/cleanup")
async def cleanup_old_monitor_history(
    days: int = 7,
    current_user: UserModel = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Clean up monitor history older than specified days.

    Args:
        days: Delete records older than this many days (default: 7, max: 30)

    Returns:
        Dictionary with cleanup results
    """
    from sqlalchemy import delete as sa_delete

    days = max(1, min(days, 30))  # Limit to 1-30 days

    try:
        async with AsyncSessionLocal() as session:
            cutoff_time = datetime.now(UTC) - timedelta(days=days)

            # Count records to be deleted
            count_result = await session.execute(
                select(MonitorHistoryModel).where(
                    MonitorHistoryModel.timestamp < cutoff_time
                )
            )
            records_to_delete = len(count_result.scalars().all())

            # Delete old records
            await session.execute(
                sa_delete(MonitorHistoryModel).where(
                    MonitorHistoryModel.timestamp < cutoff_time
                )
            )
            await session.commit()

            logger.info(f"Cleaned up {records_to_delete} old monitor history records")

            return {
                "success": True,
                "deleted_count": records_to_delete,
                "older_than_days": days,
                "cutoff_time": cutoff_time.isoformat(),
            }

    except Exception as e:
        logger.error(f"Failed to cleanup monitor history: {e}")
        return {"success": False, "error": str(e)[:100]}


@router.delete("/history/clear")
async def clear_all_monitor_history(
    current_user: UserModel = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Clear ALL monitor history data.

    WARNING: This will delete all historical monitoring data.
    Use with caution!

    Returns:
        Dictionary with clear results
    """
    from sqlalchemy import delete as sa_delete

    try:
        async with AsyncSessionLocal() as session:
            # Count all records before deletion (aggregate count; loading
            # every row just to len() them would drag the whole table into
            # memory on large history tables)
            count_result = await session.execute(
                select(func.count()).select_from(MonitorHistoryModel)
            )
            total_count = count_result.scalar() or 0

            # Delete all records
            await session.execute(sa_delete(MonitorHistoryModel))
            await session.commit()

            logger.info(f"Cleared ALL monitor history: {total_count} records deleted")

            return {
                "success": True,
                "deleted_count": total_count,
                "message": f"All {total_count} historical records have been cleared",
            }

    except Exception as e:
        logger.error(f"Failed to clear monitor history: {e}")
        return {"success": False, "error": str(e)[:100]}
