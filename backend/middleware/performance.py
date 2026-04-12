"""Performance monitoring middleware for API endpoints.

v0.8.5: Performance monitoring with slow request detection and Prometheus metrics.
- Tracks request duration for all API calls
- Logs warnings for slow requests (configurable threshold)
- Exports metrics to Prometheus histogram
- Adds X-Response-Time header for debugging
"""

import time
from collections.abc import Callable
from datetime import datetime

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)

# Default slow request threshold in seconds
DEFAULT_SLOW_REQUEST_THRESHOLD = 0.2  # 200ms

# Paths to exclude from performance monitoring (health checks, metrics, etc.)
EXCLUDED_PATHS = {
    "/health",
    "/health/ready",
    "/health/live",
    "/metrics",
    "/openapi.json",
    "/docs",
    "/redoc",
    "/favicon.ico",
}


class PerformanceMiddleware(BaseHTTPMiddleware):
    """Middleware to track API response times and log slow requests.

    Features:
    - Records request duration for all API calls
    - Logs warnings for requests exceeding threshold
    - Adds X-Response-Time header to responses
    - Integrates with Prometheus metrics (if available)
    """

    def __init__(
        self,
        app: ASGIApp,
        slow_request_threshold: float = DEFAULT_SLOW_REQUEST_THRESHOLD,
        exclude_paths: set | None = None,
    ):
        super().__init__(app)
        self.slow_request_threshold = slow_request_threshold
        self.exclude_paths = exclude_paths or EXCLUDED_PATHS
        self._prometheus_available = False

        # Try to import Prometheus for metrics
        try:
            from core.metrics import REQUEST_DURATION_HISTOGRAM

            self._histogram = REQUEST_DURATION_HISTOGRAM
            self._prometheus_available = True
        except ImportError:
            self._histogram = None
            self._prometheus_available = False

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and track performance metrics."""
        # Skip monitoring for excluded paths
        path = request.url.path
        if path in self.exclude_paths or path.startswith("/static/"):
            return await call_next(request)

        # Record start time
        start_time = time.perf_counter()

        # Get request info for logging
        method = request.method
        client_ip = self._get_client_ip(request)
        user_id = getattr(request.state, "user_id", None) or "anonymous"

        # Process request
        try:
            response = await call_next(request)

            # Calculate duration
            duration = time.perf_counter() - start_time
            duration_ms = duration * 1000

            # Add response time header
            response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"

            # Log slow requests
            if duration > self.slow_request_threshold:
                logger.warning(
                    f"Slow request: {method} {path} "
                    f"took {duration_ms:.2f}ms (threshold: {self.slow_request_threshold * 1000:.0f}ms) "
                    f"client={client_ip} user={user_id}"
                )
            else:
                logger.debug(f"Request: {method} {path} completed in {duration_ms:.2f}ms")

            # Record Prometheus metrics
            if self._prometheus_available and self._histogram:
                self._record_prometheus_metrics(
                    method=method,
                    path=self._normalize_path(path),
                    status=response.status_code,
                    duration=duration,
                )

            return response

        except Exception as e:
            # Calculate duration even for failed requests
            duration = time.perf_counter() - start_time
            duration_ms = duration * 1000

            logger.error(
                f"Request failed: {method} {path} "
                f"after {duration_ms:.2f}ms "
                f"error={e!s} "
                f"client={client_ip} user={user_id}"
            )
            raise

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request, handling proxies."""
        # Check X-Forwarded-For header first (for reverse proxies)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        # Fall back to direct client IP
        if request.client:
            return request.client.host
        return "unknown"

    def _normalize_path(self, path: str) -> str:
        """Normalize path for Prometheus labels (replace IDs with placeholders)."""
        import re

        # Replace UUID patterns
        path = re.sub(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            "{uuid}",
            path,
            flags=re.IGNORECASE,
        )

        # Replace numeric IDs
        path = re.sub(r"/\d+(?=/|$)", "/{id}", path)

        return path

    def _record_prometheus_metrics(
        self,
        method: str,
        path: str,
        status: int,
        duration: float,
    ):
        """Record request duration in Prometheus histogram."""
        try:
            self._histogram.labels(
                method=method,
                path=path,
                status=str(status),
            ).observe(duration)
        except Exception as e:
            logger.debug(f"Failed to record Prometheus metrics: {e}")


# Factory function for easy integration
def setup_performance_middleware(app, threshold: float | None = None):
    """Setup performance monitoring middleware on FastAPI app.

    Args:
        app: FastAPI application instance
        threshold: Slow request threshold in seconds (default: from settings or 200ms)
    """
    # Get threshold from settings or use default
    if threshold is None:
        threshold = getattr(settings, "slow_request_threshold", DEFAULT_SLOW_REQUEST_THRESHOLD)

    app.add_middleware(PerformanceMiddleware, slow_request_threshold=threshold)
    logger.info(f"Performance monitoring middleware enabled (threshold: {threshold * 1000:.0f}ms)")


# Re-export canonical histogram from core.metrics to avoid duplicate registration.
try:
    from core.metrics import REQUEST_DURATION_HISTOGRAM
except Exception:  # pragma: no cover
    REQUEST_DURATION_HISTOGRAM = None
