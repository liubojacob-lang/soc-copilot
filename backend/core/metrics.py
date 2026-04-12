"""Backward-compatible metrics facade.

This module keeps existing imports stable while delegating implementation to
`observability.metrics`.
"""

from __future__ import annotations

from observability.metrics import (
    REQUEST_DURATION_HISTOGRAM,
    observe_api_request,
    observe_correlation_rule_hit,
    observe_exception,
    observe_playbook_error,
    observe_playbook_run,
    observe_queue_consume,
    observe_queue_dlq,
    observe_queue_retry,
    set_queue_lag,
    setup_metrics,
)


def record_playbook_run(
    playbook_name: str,
    status: str,
    mode: str,
    duration: float,
    tenant_id: str = "default",
):
    observe_playbook_run(playbook_name, status, mode, tenant_id, duration)


def record_playbook_error(
    playbook_name: str, error_type: str, tenant_id: str = "default"
):
    observe_playbook_error(playbook_name, error_type, tenant_id)


def record_ai_request(
    model: str,
    provider: str,
    status: str,
    duration: float,
    tokens_input: int = 0,
    tokens_output: int = 0,
):
    # Kept for compatibility; AI metrics moved to dedicated provider metrics in stage 3.
    _ = (model, provider, status, duration, tokens_input, tokens_output)
    return None


__all__ = [
    "REQUEST_DURATION_HISTOGRAM",
    "observe_api_request",
    "observe_correlation_rule_hit",
    "observe_exception",
    "observe_playbook_error",
    "observe_playbook_run",
    "observe_queue_consume",
    "observe_queue_dlq",
    "observe_queue_retry",
    "record_ai_request",
    "record_playbook_error",
    "record_playbook_run",
    "set_queue_lag",
    "setup_metrics",
]
