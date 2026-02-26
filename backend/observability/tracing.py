"""OpenTelemetry tracing bootstrap (optional dependency)."""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def setup_tracing(app=None, service_name: str = "soc-backend") -> bool:
    """Initialize OpenTelemetry exporters/instrumentation when deps are installed."""
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.redis import RedisInstrumentor
        from opentelemetry.instrumentation.logging import LoggingInstrumentor
    except Exception as exc:  # pragma: no cover
        logger.warning("OpenTelemetry disabled (missing packages): %s", exc)
        return False

    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        logger.info("OpenTelemetry not configured (OTEL_EXPORTER_OTLP_ENDPOINT missing)")
        return False

    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    span_processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, insecure=True))
    provider.add_span_processor(span_processor)
    trace.set_tracer_provider(provider)

    if app is not None:
        FastAPIInstrumentor.instrument_app(app)

    RedisInstrumentor().instrument()
    LoggingInstrumentor().instrument(set_logging_format=False)
    logger.info("OpenTelemetry tracing enabled")
    return True
