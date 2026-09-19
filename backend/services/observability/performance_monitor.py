"""
Performance monitoring service for collecting and analyzing system performance metrics.
"""

import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger

logger = get_logger(__name__)


class PerformanceMetricType(Enum):
    """Types of performance metrics."""

    API_RESPONSE_TIME = "api_response_time"
    API_THROUGHPUT = "api_throughput"
    CACHE_HIT_RATE = "cache_hit_rate"
    MEMORY_USAGE = "memory_usage"
    CPU_USAGE = "cpu_usage"
    DATABASE_QUERY_TIME = "database_query_time"


@dataclass
class PerformanceMetric:
    """Performance metric data class."""

    metric_type: PerformanceMetricType
    value: float
    timestamp: datetime
    labels: dict[str, str]
    source: str


@dataclass
class PerformanceReport:
    """Performance report data class."""

    period_start: datetime
    period_end: datetime
    metrics: list[PerformanceMetric]
    summary: dict[str, Any]
    recommendations: list[str]


class PerformanceMonitor:
    """Performance monitoring service."""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self._metrics_buffer: list[PerformanceMetric] = []
        self._buffer_size = 1000
        self._last_flush_time = time.time()

    async def collect_api_metrics(
        self, time_window_minutes: int = 5
    ) -> list[PerformanceMetric]:
        """Collect API performance metrics from the database."""
        metrics = []

        # Calculate time window
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=time_window_minutes)

        try:
            # Query for slow API requests from audit logs
            query = text(
                """
                SELECT 
                    method,
                    path,
                    COUNT(*) as request_count,
                    AVG(duration_ms) as avg_duration_ms,
                    MAX(duration_ms) as max_duration_ms,
                    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms) as p95_duration_ms
                FROM audit_logs 
                WHERE created_at >= :start_time 
                  AND created_at <= :end_time
                  AND duration_ms IS NOT NULL
                GROUP BY method, path
                HAVING AVG(duration_ms) > 100  -- Only include slow requests (>100ms avg)
                ORDER BY avg_duration_ms DESC
                LIMIT 20
            """
            )

            result = await self.db_session.execute(
                query, {"start_time": start_time, "end_time": end_time}
            )
            rows = result.fetchall()

            for row in rows:
                method, path, count, avg_duration, max_duration, p95_duration = row

                metrics.append(
                    PerformanceMetric(
                        metric_type=PerformanceMetricType.API_RESPONSE_TIME,
                        value=float(avg_duration),
                        timestamp=end_time,
                        labels={"method": method, "path": path, "statistic": "average"},
                        source="audit_logs",
                    )
                )

                metrics.append(
                    PerformanceMetric(
                        metric_type=PerformanceMetricType.API_RESPONSE_TIME,
                        value=float(p95_duration),
                        timestamp=end_time,
                        labels={"method": method, "path": path, "statistic": "p95"},
                        source="audit_logs",
                    )
                )

                metrics.append(
                    PerformanceMetric(
                        metric_type=PerformanceMetricType.API_THROUGHPUT,
                        value=float(count),
                        timestamp=end_time,
                        labels={"method": method, "path": path},
                        source="audit_logs",
                    )
                )

        except Exception as e:
            logger.error(f"Failed to collect API metrics: {e}")

        return metrics

    async def collect_cache_metrics(self) -> list[PerformanceMetric]:
        """Collect cache performance metrics."""
        metrics = []

        try:
            # Get cache hit rate from Prometheus-style metrics
            # In a real implementation, you would query your metrics storage
            # For now, we'll use the Prometheus client metrics

            # Example: Calculate cache hit rate
            cache_names = ["query_cache", "threat_intel_cache", "alert_cache"]

            for cache_name in cache_names:
                # In a real implementation, you would get actual values
                # For now, we'll use placeholder values
                hit_rate = 0.85  # Placeholder: 85% hit rate

                metrics.append(
                    PerformanceMetric(
                        metric_type=PerformanceMetricType.CACHE_HIT_RATE,
                        value=hit_rate * 100,  # Convert to percentage
                        timestamp=datetime.now(),
                        labels={"cache_name": cache_name},
                        source="cache_monitor",
                    )
                )

        except Exception as e:
            logger.error(f"Failed to collect cache metrics: {e}")

        return metrics

    async def collect_database_metrics(
        self, time_window_minutes: int = 5
    ) -> list[PerformanceMetric]:
        """Collect database performance metrics."""
        metrics = []

        try:
            # Query for slow database queries
            # This would require query logging to be enabled
            # For now, we'll check for common performance issues

            # Check for table sizes and growth
            bind = self.db_session.get_bind() if hasattr(self.db_session, "get_bind") else getattr(self.db_session, "bind", None)
            is_postgres = bind is not None and getattr(bind, "dialect", None) is not None and bind.dialect.name == "postgresql"

            if is_postgres:
                query = text(
                    """
                    SELECT 
                        relname as table_name,
                        n_live_tup as row_count
                    FROM pg_stat_user_tables
                    ORDER BY n_live_tup DESC
                    LIMIT 10
                    """
                )
            else:
                query = text(
                    """
                    SELECT 
                        name as table_name,
                        0 as row_count
                    FROM sqlite_master 
                    WHERE type='table' 
                      AND name NOT LIKE 'sqlite_%'
                    LIMIT 10
                    """
                )

            result = await self.db_session.execute(query)
            tables = result.fetchall()

            for table_name, row_count in tables:
                if row_count > 100000:  # Flag large tables
                    metrics.append(
                        PerformanceMetric(
                            metric_type=PerformanceMetricType.DATABASE_QUERY_TIME,
                            value=float(row_count),
                            timestamp=datetime.now(),
                            labels={"table": table_name, "issue": "large_table"},
                            source="database_analysis",
                        )
                    )

        except Exception as e:
            logger.error(f"Failed to collect database metrics: {e}")

        return metrics

    async def generate_performance_report(
        self, time_window_minutes: int = 60
    ) -> PerformanceReport:
        """Generate a comprehensive performance report."""
        logger.info(
            f"Generating performance report for last {time_window_minutes} minutes"
        )

        period_end = datetime.now()
        period_start = period_end - timedelta(minutes=time_window_minutes)

        # Collect all metrics
        api_metrics = await self.collect_api_metrics(time_window_minutes)
        cache_metrics = await self.collect_cache_metrics()
        db_metrics = await self.collect_database_metrics(time_window_minutes)

        all_metrics = api_metrics + cache_metrics + db_metrics

        # Generate summary
        summary = self._generate_summary(all_metrics, time_window_minutes)

        # Generate recommendations
        recommendations = self._generate_recommendations(all_metrics, summary)

        report = PerformanceReport(
            period_start=period_start,
            period_end=period_end,
            metrics=all_metrics,
            summary=summary,
            recommendations=recommendations,
        )

        logger.info(f"Performance report generated: {summary}")
        return report

    def _generate_summary(
        self, metrics: list[PerformanceMetric], time_window_minutes: int
    ) -> dict[str, Any]:
        """Generate summary statistics from metrics."""
        summary = {
            "time_window_minutes": time_window_minutes,
            "total_metrics_collected": len(metrics),
            "api_metrics": defaultdict(list),
            "cache_metrics": defaultdict(list),
            "database_metrics": defaultdict(list),
            "performance_issues": [],
            "slow_endpoints": [],
            "low_cache_hit_rates": [],
        }

        # Categorize and analyze metrics
        for metric in metrics:
            if metric.metric_type == PerformanceMetricType.API_RESPONSE_TIME:
                summary["api_metrics"]["response_times"].append(metric.value)

                # Check for slow endpoints (>500ms average)
                if metric.value > 500 and metric.labels.get("statistic") == "average":
                    summary["slow_endpoints"].append(
                        {
                            "path": metric.labels.get("path", "unknown"),
                            "method": metric.labels.get("method", "unknown"),
                            "avg_response_time_ms": metric.value,
                            "statistic": metric.labels.get("statistic"),
                        }
                    )

            elif metric.metric_type == PerformanceMetricType.API_THROUGHPUT:
                summary["api_metrics"]["throughput"].append(metric.value)

            elif metric.metric_type == PerformanceMetricType.CACHE_HIT_RATE:
                summary["cache_metrics"]["hit_rates"].append(metric.value)

                # Check for low cache hit rates (<70%)
                if metric.value < 70:
                    summary["low_cache_hit_rates"].append(
                        {
                            "cache_name": metric.labels.get("cache_name", "unknown"),
                            "hit_rate_percent": metric.value,
                        }
                    )

            elif metric.metric_type == PerformanceMetricType.DATABASE_QUERY_TIME:
                summary["database_metrics"]["query_times"].append(metric.value)

                # Check for large tables
                if (
                    metric.labels.get("issue") == "large_table"
                    and metric.value > 100000
                ):
                    summary["performance_issues"].append(
                        {
                            "type": "large_table",
                            "table": metric.labels.get("table", "unknown"),
                            "row_count": int(metric.value),
                            "recommendation": "Consider archiving old data or adding indexes",
                        }
                    )

        # Calculate statistics
        if summary["api_metrics"]["response_times"]:
            response_times = summary["api_metrics"]["response_times"]
            summary["api_response_time_stats"] = {
                "average_ms": sum(response_times) / len(response_times),
                "max_ms": max(response_times),
                "min_ms": min(response_times),
                "count": len(response_times),
            }

        if summary["cache_metrics"]["hit_rates"]:
            hit_rates = summary["cache_metrics"]["hit_rates"]
            summary["cache_hit_rate_stats"] = {
                "average_percent": sum(hit_rates) / len(hit_rates),
                "max_percent": max(hit_rates),
                "min_percent": min(hit_rates),
                "count": len(hit_rates),
            }

        return summary

    def _generate_recommendations(
        self, metrics: list[PerformanceMetric], summary: dict[str, Any]
    ) -> list[str]:
        """Generate performance improvement recommendations."""
        recommendations = []

        # API performance recommendations
        if "api_response_time_stats" in summary:
            avg_response_time = summary["api_response_time_stats"]["average_ms"]

            if avg_response_time > 500:
                recommendations.append(
                    f"High average API response time ({avg_response_time:.1f}ms). "
                    "Consider optimizing database queries, adding caching, or scaling resources."
                )
            elif avg_response_time > 200:
                recommendations.append(
                    f"Moderate API response time ({avg_response_time:.1f}ms). "
                    "Monitor for degradation and consider optimizations for frequently accessed endpoints."
                )

        # Cache recommendations
        if "cache_hit_rate_stats" in summary:
            avg_hit_rate = summary["cache_hit_rate_stats"]["average_percent"]

            if avg_hit_rate < 70:
                recommendations.append(
                    f"Low cache hit rate ({avg_hit_rate:.1f}%). "
                    "Consider increasing cache TTL, adding more cache layers, or optimizing cache keys."
                )

        # Slow endpoints recommendations
        for endpoint in summary.get("slow_endpoints", []):
            recommendations.append(
                f"Slow endpoint detected: {endpoint['method']} {endpoint['path']} "
                f"(avg {endpoint['avg_response_time_ms']:.1f}ms). "
                "Consider adding database indexes, query optimization, or response caching."
            )

        # Large table recommendations
        for issue in summary.get("performance_issues", []):
            if issue["type"] == "large_table":
                recommendations.append(issue["recommendation"])

        # Add general recommendations if none specific
        if not recommendations:
            recommendations.append(
                "System performance is within acceptable ranges. "
                "Continue monitoring for any degradation."
            )

        return recommendations

    async def record_metric(self, metric: PerformanceMetric) -> None:
        """Record a performance metric (buffered for efficiency)."""
        self._metrics_buffer.append(metric)

        # Flush buffer if it's full or enough time has passed
        if (
            len(self._metrics_buffer) >= self._buffer_size
            or time.time() - self._last_flush_time > 60
        ):  # Flush every minute
            await self._flush_metrics_buffer()

    async def _flush_metrics_buffer(self) -> None:
        """Flush buffered metrics to storage."""
        if not self._metrics_buffer:
            return

        try:
            # In a real implementation, you would store metrics in a time-series database
            # For now, we'll just log them
            logger.info(f"Flushing {len(self._metrics_buffer)} performance metrics")

            # Clear buffer
            self._metrics_buffer.clear()
            self._last_flush_time = time.time()

        except Exception as e:
            logger.error(f"Failed to flush metrics buffer: {e}")

    async def get_performance_trends(
        self, metric_type: PerformanceMetricType, time_window_hours: int = 24
    ) -> dict[str, Any]:
        """Get performance trends for a specific metric type."""
        # This would query time-series data from a metrics database
        # For now, return placeholder data

        return {
            "metric_type": metric_type.value,
            "time_window_hours": time_window_hours,
            "data": {
                "timestamps": [],
                "values": [],
                "trend": "stable",  # stable, improving, degrading
                "change_percentage": 0.0,
            },
            "analysis": "No historical data available. Implement metrics storage for trend analysis.",
        }
