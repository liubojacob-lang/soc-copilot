"""LLM call tracing with Langfuse integration.

Provides optional tracing for LLM calls using Langfuse.
If Langfuse is not configured or installed, a NoopTracer is used
that has zero performance impact.
"""

import asyncio
import functools
import time
from collections.abc import Callable
from typing import Any

from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Langfuse availability detection
# ---------------------------------------------------------------------------
_LANGFUSE_AVAILABLE = False
_langfuse: Any = None


def _try_import_langfuse() -> bool:
    """Try to import langfuse; return True on success."""
    global _langfuse
    try:
        from langfuse.decorators import observe  # noqa: F401 (availability probe)
        from langfuse.langfuse import Langfuse

        _langfuse = Langfuse(
            public_key=getattr(settings, "langfuse_public_key", None) or "",
            secret_key=getattr(settings, "langfuse_secret_key", None) or "",
            host=getattr(settings, "langfuse_host", "https://cloud.langfuse.com"),
            flush_interval=5,
        )
        logger.info("Langfuse tracing initialized")
        return True
    except ImportError:
        logger.debug("Langfuse not installed; using NoopTracer")
        return False
    except Exception as e:
        logger.warning(f"Langfuse initialization failed: {e}; using NoopTracer")
        return False


# ---------------------------------------------------------------------------
# Tracer (real or noop)
# ---------------------------------------------------------------------------
class NoopTracer:
    """No-op tracer with zero overhead when Langfuse is disabled."""

    def trace(self, name: str, **kwargs):
        """Return a no-op context manager."""

        class _NoopCtx:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        return _NoopCtx()

    def generation(self, **kwargs):
        """Return a no-op context manager."""

        class _NoopGen:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        return _NoopGen()

    def span(self, **kwargs):
        """Return a no-op context manager."""

        class _NoopSpan:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        return _NoopSpan()

    def score(self, **kwargs):
        """No-op score."""
        pass

    def event(self, **kwargs):
        """No-op event."""
        pass


def get_tracer() -> Any:
    """Get the global tracer instance (Langfuse or Noop)."""
    global _LANGFUSE_AVAILABLE
    if not _LANGFUSE_AVAILABLE:
        # Check if configured
        pk = getattr(settings, "langfuse_public_key", None)
        sk = getattr(settings, "langfuse_secret_key", None)
        if pk and sk:
            _LANGFUSE_AVAILABLE = _try_import_langfuse()
        else:
            logger.debug(
                "Langfuse not configured (LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY)"
            )
    if _LANGFUSE_AVAILABLE:
        return _langfuse
    return NoopTracer()


# ---------------------------------------------------------------------------
# Manual tracing helpers
# ---------------------------------------------------------------------------
def trace_llm_call(func: Callable) -> Callable:
    """Decorator to trace an LLM call function.

    Records:
    - start/end time  (latency)
    - prompt / response text (truncated for safety)
    - token usage (if available)
    - model name (if available)
    """

    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        tracer = get_tracer()
        start = time.perf_counter()

        # Extract prompt / model from kwargs if available
        prompt_text = _extract_prompt(kwargs)
        model_name = kwargs.get("model") or kwargs.get("model_name", "unknown")

        try:
            result = await func(*args, **kwargs)
            latency = time.perf_counter() - start
            _record_generation(
                tracer,
                name=func.__name__,
                prompt=prompt_text,
                response=_extract_response(result),
                model=model_name,
                latency=latency,
                usage=_extract_usage(result),
                level="DEFAULT",
            )
            return result
        except Exception as e:
            latency = time.perf_counter() - start
            _record_generation(
                tracer,
                name=func.__name__,
                prompt=prompt_text,
                response=str(e),
                model=model_name,
                latency=latency,
                level="ERROR",
            )
            raise

    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        tracer = get_tracer()
        start = time.perf_counter()

        prompt_text = _extract_prompt(kwargs)
        model_name = kwargs.get("model") or kwargs.get("model_name", "unknown")

        try:
            result = func(*args, **kwargs)
            latency = time.perf_counter() - start
            _record_generation(
                tracer,
                name=func.__name__,
                prompt=prompt_text,
                response=_extract_response(result),
                model=model_name,
                latency=latency,
                usage=_extract_usage(result),
                level="DEFAULT",
            )
            return result
        except Exception as e:
            latency = time.perf_counter() - start
            _record_generation(
                tracer,
                name=func.__name__,
                prompt=prompt_text,
                response=str(e),
                model=model_name,
                latency=latency,
                level="ERROR",
            )
            raise

    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper


def _extract_prompt(kwargs: dict[str, Any]) -> str | None:
    """Extract prompt text from kwargs."""
    for key in ("prompt", "messages", "system_prompt", "user_prompt"):
        if key in kwargs:
            val = kwargs[key]
            if isinstance(val, str):
                return val[:4000]
            if isinstance(val, list):
                # messages list
                return str(val)[:4000]
    return None


def _extract_response(result: Any) -> str | None:
    """Extract response text from result."""
    if isinstance(result, str):
        return result[:4000]
    if isinstance(result, dict):
        content = result.get("content") or result.get("text") or result.get("response")
        if isinstance(content, str):
            return content[:4000]
    return str(result)[:4000]


def _extract_usage(result: Any) -> dict[str, int] | None:
    """Extract token usage from result."""
    if isinstance(result, dict) and "usage" in result:
        usage = result["usage"]
        if isinstance(usage, dict):
            out = {}
            for k in ("prompt_tokens", "completion_tokens", "total_tokens"):
                if k in usage:
                    out[k] = usage[k]
            return out if out else None
    return None


def _record_generation(
    tracer: Any,
    name: str,
    prompt: str | None,
    response: str | None,
    model: str,
    latency: float,
    usage: dict[str, int] | None = None,
    level: str = "DEFAULT",
) -> None:
    """Record a generation event to Langfuse if available."""
    if isinstance(tracer, NoopTracer):
        return

    try:
        from langfuse.api.resources.commons.types.usage import Usage

        _usage = None
        if usage:
            try:
                _usage = Usage(**usage)
            except Exception:
                pass

        tracer.generation(
            name=name,
            input=prompt,
            output=response,
            model=model,
            usage=_usage,
            metadata={"latency_ms": round(latency * 1000, 2)},
        )
    except Exception:
        # Fail silently - tracing should never break application logic
        pass


# ---------------------------------------------------------------------------
# High-level observe decorator for FastAPI endpoints
# ---------------------------------------------------------------------------
def observe_endpoint(name: str | None = None):
    """Decorator to observe a FastAPI endpoint.

    Usage:
        @router.post("/analyze-alert")
        @observe_endpoint("analyze_alert")
        async def analyze_alert(...):
            ...
    """

    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            tracer = get_tracer()
            _name = name or func.__name__
            start = time.perf_counter()

            with tracer.trace(name=_name) as trace:
                try:
                    result = await func(*args, **kwargs)
                    latency = time.perf_counter() - start
                    if not isinstance(tracer, NoopTracer):
                        try:
                            trace.update(
                                metadata={"latency_ms": round(latency * 1000, 2)}
                            )
                        except Exception:
                            pass
                    return result
                except Exception as e:
                    latency = time.perf_counter() - start
                    if not isinstance(tracer, NoopTracer):
                        try:
                            trace.update(
                                metadata={
                                    "latency_ms": round(latency * 1000, 2),
                                    "error": str(e),
                                }
                            )
                        except Exception:
                            pass
                    raise

        return wrapper

    return decorator
