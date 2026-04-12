"""
Performance monitoring API endpoints.
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_session
from services.observability.performance_monitor import PerformanceMonitor, PerformanceMetricType
from dependencies.auth import get_current_user
from schemas.user import User

router = APIRouter(prefix="/api/performance", tags=["performance"])


@router.get("/report")
async def get_performance_report(
    time_window_minutes: int = Query(
        60, ge=1, le=1440, description="Time window in minutes (1-1440)"
    ),
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_session),
):
    """
    Get performance report for the specified time window.

    Requires admin or analyst role.
    """
    if current_user.role not in ["admin", "analyst"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    monitor = PerformanceMonitor(db_session)
    report = await monitor.generate_performance_report(time_window_minutes)

    return {
        "period_start": report.period_start.isoformat(),
        "period_end": report.period_end.isoformat(),
        "summary": report.summary,
        "recommendations": report.recommendations,
        "metric_count": len(report.metrics),
    }


@router.get("/metrics/api")
async def get_api_metrics(
    time_window_minutes: int = Query(
        30, ge=1, le=1440, description="Time window in minutes (1-1440)"
    ),
    limit: int = Query(20, ge=1, le=100, description="Number of endpoints to return"),
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_session),
):
    """
    Get API performance metrics (response times, throughput).

    Requires admin or analyst role.
    """
    if current_user.role not in ["admin", "analyst"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    monitor = PerformanceMonitor(db_session)
    metrics = await monitor.collect_api_metrics(time_window_minutes)

    # Group metrics by endpoint
    endpoint_metrics = {}
    for metric in metrics:
        if metric.metric_type == PerformanceMetricType.API_RESPONSE_TIME:
            key = f"{metric.labels.get('method')} {metric.labels.get('path')}"
            if key not in endpoint_metrics:
                endpoint_metrics[key] = {
                    "method": metric.labels.get("method"),
                    "path": metric.labels.get("path"),
                    "response_times": {},
                    "request_count": 0,
                }

            statistic = metric.labels.get("statistic", "unknown")
            endpoint_metrics[key]["response_times"][statistic] = metric.value

        elif metric.metric_type == PerformanceMetricType.API_THROUGHPUT:
            key = f"{metric.labels.get('method')} {metric.labels.get('path')}"
            if key in endpoint_metrics:
                endpoint_metrics[key]["request_count"] = metric.value

    # Convert to list and sort by average response time (descending)
    endpoints = list(endpoint_metrics.values())
    endpoints.sort(key=lambda x: x.get("response_times", {}).get("average", 0), reverse=True)

    return {
        "time_window_minutes": time_window_minutes,
        "endpoints": endpoints[:limit],
        "total_endpoints": len(endpoints),
    }


@router.get("/metrics/cache")
async def get_cache_metrics(
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_session),
):
    """
    Get cache performance metrics (hit rates).

    Requires admin or analyst role.
    """
    if current_user.role not in ["admin", "analyst"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    monitor = PerformanceMonitor(db_session)
    metrics = await monitor.collect_cache_metrics()

    cache_stats = []
    for metric in metrics:
        if metric.metric_type == PerformanceMetricType.CACHE_HIT_RATE:
            cache_stats.append(
                {
                    "cache_name": metric.labels.get("cache_name"),
                    "hit_rate_percent": metric.value,
                    "timestamp": metric.timestamp.isoformat(),
                }
            )

    return {
        "cache_stats": cache_stats,
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/metrics/database")
async def get_database_metrics(
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_session),
):
    """
    Get database performance metrics.

    Requires admin or analyst role.
    """
    if current_user.role not in ["admin", "analyst"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    monitor = PerformanceMonitor(db_session)
    metrics = await monitor.collect_database_metrics()

    # Get table statistics
    try:
        query = """
            SELECT 
                name as table_name,
                COUNT(*) as row_count
            FROM sqlite_master 
            WHERE type='table' 
              AND name NOT LIKE 'sqlite_%'
            GROUP BY name
            ORDER BY row_count DESC
        """

        result = await db_session.execute(query)
        tables = result.fetchall()

        table_stats = []
        for table_name, row_count in tables:
            table_stats.append(
                {
                    "table_name": table_name,
                    "row_count": row_count,
                    "size_category": "large"
                    if row_count > 100000
                    else "medium"
                    if row_count > 10000
                    else "small",
                }
            )

    except Exception as e:
        table_stats = []

    # Get performance issues from metrics
    performance_issues = []
    for metric in metrics:
        if metric.metric_type == PerformanceMetricType.DATABASE_QUERY_TIME:
            if metric.labels.get("issue") == "large_table":
                performance_issues.append(
                    {
                        "type": "large_table",
                        "table": metric.labels.get("table"),
                        "row_count": int(metric.value),
                        "recommendation": "Consider archiving old data or adding indexes",
                    }
                )

    return {
        "table_statistics": table_stats,
        "performance_issues": performance_issues,
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/trends/{metric_type}")
async def get_performance_trends(
    metric_type: str,
    time_window_hours: int = Query(24, ge=1, le=168, description="Time window in hours (1-168)"),
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_session),
):
    """
    Get performance trends for a specific metric type.

    Requires admin or analyst role.
    """
    if current_user.role not in ["admin", "analyst"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # Validate metric type
    try:
        metric_type_enum = PerformanceMetricType(metric_type)
    except ValueError:
        valid_types = [t.value for t in PerformanceMetricType]
        raise HTTPException(
            status_code=400, detail=f"Invalid metric type. Valid types: {valid_types}"
        )

    monitor = PerformanceMonitor(db_session)
    trends = await monitor.get_performance_trends(metric_type_enum, time_window_hours)

    return trends


@router.get("/health")
async def get_performance_health(
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_session),
):
    """
    Get overall system performance health status.

    Returns a simple health status based on key performance indicators.
    """
    if current_user.role not in ["admin", "analyst"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    monitor = PerformanceMonitor(db_session)

    # Generate a quick health check report
    report = await monitor.generate_performance_report(time_window_minutes=15)

    # Determine overall health status
    health_status = "healthy"
    issues = []

    # Check for critical issues
    if "api_response_time_stats" in report.summary:
        avg_response_time = report.summary["api_response_time_stats"]["average_ms"]
        if avg_response_time > 1000:
            health_status = "degraded"
            issues.append(f"High API response time: {avg_response_time:.0f}ms")

    if "error_rate" in report.summary:
        error_rate = report.summary["error_rate"]
        if error_rate > 0.05:
            health_status = "unhealthy"
            issues.append(f"High error rate: {error_rate * 100:.1f}%")

    return {"status": health_status, "issues": issues, "summary": report.summary}
