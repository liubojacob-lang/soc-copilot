"""Observability exporter configuration placeholders."""

from __future__ import annotations

import os


def exporter_config() -> dict[str, str | None]:
    return {
        "otel_endpoint": os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"),
        "prometheus_path": "/metrics/prometheus",
    }
