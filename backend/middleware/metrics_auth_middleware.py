"""Access control for the Prometheus scrape endpoints.

``/metrics`` (hand-rolled health metrics) and ``/metrics/prometheus``
(instrumentator) leak environment name, uptime, DB/Redis latency and per-route
request counts. They are not reachable through nginx, but the backend port is
published directly in development and scraped over the container network in
production, so they must not be open by default forever.

Behaviour:
- ``metrics_token`` set -> require ``Authorization: Bearer <token>``.
- unset in production   -> 404, the endpoints do not exist until a token is set.
- unset elsewhere       -> allowed, so local sims and tests keep working.
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from core.config import settings
from core.logger import get_logger

METRICS_PATHS = frozenset({"/metrics", "/metrics/prometheus"})

logger = get_logger(__name__)
_disabled_warned = False


class MetricsAuthMiddleware(BaseHTTPMiddleware):
    """Gate the scrape endpoints behind METRICS_TOKEN."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        global _disabled_warned

        if request.url.path.rstrip("/") not in {p.rstrip("/") for p in METRICS_PATHS}:
            return await call_next(request)

        expected = settings.metrics_token

        if not expected and settings.environment == "production":
            if not _disabled_warned:
                logger.warning(
                    "METRICS_TOKEN is unset in production; /metrics is disabled. "
                    "Set it to enable Prometheus scraping."
                )
                _disabled_warned = True
            return Response(status_code=404)

        if expected:
            header = request.headers.get("authorization", "")
            supplied = header.removeprefix("Bearer ").strip()
            if supplied != expected:
                return Response(
                    status_code=401,
                    headers={"WWW-Authenticate": "Bearer"},
                )

        return await call_next(request)
