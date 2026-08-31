"""Alerting package — analysis, streaming, and queue integration."""

from .alert_ingest_queue import ingest_alert, ingest_playbook_result

# Lazy imports avoid pulling the full dependency chain (models/__init__.py is
# currently broken upstream — these are safe submodule imports below).
__all__ = [
    "ingest_alert",
    "ingest_playbook_result",
]
