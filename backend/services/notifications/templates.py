"""Notification templates."""

from __future__ import annotations

from typing import Any


def render_alert_template(alert: dict[str, Any]) -> tuple[str, str, str]:
    severity = str(alert.get("severity", "medium")).lower()
    title = f"[{alert.get('source', 'SOC').upper()}] {alert.get('title', 'Security Alert')}"
    body = (
        f"Alert ID: {alert.get('id', 'N/A')}\n"
        f"Severity: {severity.upper()}\n"
        f"Event: {alert.get('event_type', 'N/A')}\n"
        f"Time: {alert.get('created_at', alert.get('event_timestamp', 'N/A'))}\n"
        f"Description: {alert.get('description', 'N/A')}"
    )
    return title, body, severity
