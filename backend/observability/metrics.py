"""Prometheus metrics definitions and helpers."""

from __future__ import annotations

from fastapi import FastAPI
from prometheus_client import Counter, Gauge, Histogram

try:
    from prometheus_fastapi_instrumentator import Instrumentator
except Exception:  # pragma: no cover
    Instrumentator = None

# API metrics
api_requests_total = Counter(
    "soc_api_requests_total",
    "Total API requests",
    ["method", "path", "status", "tenant_id"],
)
api_request_duration_seconds = Histogram(
    "soc_api_request_duration_seconds",
    "API request latency in seconds",
    ["method", "path", "tenant_id"],
    buckets=(0.01, 0.05, 0.1, 0.2, 0.5, 1, 2, 5),
)

# Keep compatibility with performance middleware import
REQUEST_DURATION_HISTOGRAM = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path", "status"],
    buckets=(0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 10.0),
)

# Queue metrics
queue_consume_total = Counter(
    "soc_queue_consume_total",
    "Queue consume attempts",
    ["stream", "consumer_group", "result"],
)
queue_processing_seconds = Histogram(
    "soc_queue_processing_seconds",
    "Queue processing latency",
    ["stream", "consumer_group"],
    buckets=(0.001, 0.01, 0.05, 0.1, 0.5, 1, 2),
)
queue_lag = Gauge("soc_queue_lag", "Queue lag size", ["stream"])
queue_dlq_total = Counter("soc_queue_dlq_total", "Events moved to DLQ", ["stream"])
queue_retry_total = Counter("soc_queue_retry_total", "Events retried", ["stream"])

# Playbook metrics
playbook_runs_total = Counter(
    "soc_playbook_runs_total",
    "Playbook run count",
    ["playbook_name", "status", "mode", "tenant_id"],
)
playbook_run_duration_seconds = Histogram(
    "soc_playbook_run_duration_seconds",
    "Playbook run duration",
    ["playbook_name", "tenant_id"],
    buckets=(1, 5, 10, 30, 60, 120, 300, 600),
)
playbook_errors_total = Counter(
    "soc_playbook_errors_total",
    "Playbook errors",
    ["playbook_name", "error_type", "tenant_id"],
)

# Correlation metrics
correlation_rule_hit_total = Counter(
    "soc_correlation_rule_hit_total",
    "Correlation rule hit count",
    ["rule_id", "tenant_id"],
)

# Error metrics
exceptions_total = Counter(
    "soc_exceptions_total",
    "Unhandled exceptions",
    ["exception_type", "path"],
)


def setup_metrics(app: FastAPI) -> None:
    """Expose Prometheus endpoint and default instrumentator metrics."""
    if Instrumentator is None:
        return
    instrumentator = Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        excluded_handlers=["/metrics", "/health/live", "/health/ready"],
    )
    instrumentator.instrument(app)
    instrumentator.expose(app, endpoint="/metrics/prometheus", include_in_schema=False)


def observe_api_request(method: str, path: str, status: int, tenant_id: str, duration_s: float) -> None:
    api_requests_total.labels(method, path, str(status), tenant_id).inc()
    api_request_duration_seconds.labels(method, path, tenant_id).observe(duration_s)
    REQUEST_DURATION_HISTOGRAM.labels(method, path, str(status)).observe(duration_s)


def observe_queue_consume(stream: str, group: str, result: str, duration_s: float | None = None) -> None:
    queue_consume_total.labels(stream, group, result).inc()
    if duration_s is not None:
        queue_processing_seconds.labels(stream, group).observe(duration_s)


def observe_queue_retry(stream: str) -> None:
    queue_retry_total.labels(stream).inc()


def observe_queue_dlq(stream: str) -> None:
    queue_dlq_total.labels(stream).inc()


def set_queue_lag(stream: str, size: int) -> None:
    queue_lag.labels(stream).set(size)


def observe_playbook_run(playbook_name: str, status: str, mode: str, tenant_id: str, duration_s: float) -> None:
    playbook_runs_total.labels(playbook_name, status, mode, tenant_id).inc()
    playbook_run_duration_seconds.labels(playbook_name, tenant_id).observe(duration_s)


def observe_playbook_error(playbook_name: str, error_type: str, tenant_id: str = "default") -> None:
    playbook_errors_total.labels(playbook_name, error_type, tenant_id).inc()


def observe_correlation_rule_hit(rule_id: str, tenant_id: str = "default") -> None:
    correlation_rule_hit_total.labels(rule_id, tenant_id).inc()


def observe_exception(exception_type: str, path: str) -> None:
    exceptions_total.labels(exception_type, path).inc()
