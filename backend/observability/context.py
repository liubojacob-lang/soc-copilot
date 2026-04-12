"""Request-scoped observability context."""

from __future__ import annotations

from contextvars import ContextVar

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")
trace_id_ctx: ContextVar[str] = ContextVar("trace_id", default="")
tenant_id_ctx: ContextVar[str] = ContextVar("tenant_id", default="default")


def set_context(
    *, request_id: str = "", trace_id: str = "", tenant_id: str = "default"
) -> None:
    request_id_ctx.set(request_id or "")
    trace_id_ctx.set(trace_id or "")
    tenant_id_ctx.set(tenant_id or "default")


def clear_context() -> None:
    request_id_ctx.set("")
    trace_id_ctx.set("")
    tenant_id_ctx.set("default")


def get_request_id() -> str:
    return request_id_ctx.get()


def get_trace_id() -> str:
    return trace_id_ctx.get()


def get_tenant_id() -> str:
    return tenant_id_ctx.get()
