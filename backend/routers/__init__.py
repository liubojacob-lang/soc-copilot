"""API routers module."""

from . import (
    admin_settings,
    ai,
    ai_models,
    ai_tasks,
    alert,
    alert_enrichment,  # v0.9.0: Threat intelligence enrichment
    api_keys,
    assets,
    audit,
    auth,
    cloud_native,
    correlation,  # v0.8.0: Event correlation
    history,
    ioc_hits,
    marketplace,
    monitor,
    playbook,
    playbook_definitions,
    report,
    root_cause,
    secrets,
    security_alerts,  # v0.9.0: External security alert ingestion
    threat_hunting,
    threat_intel,
    timeline,
    triggers,
    ueba,
    users,
    webhooks,
)

__all__ = [
    "admin_settings",
    "ai",
    "ai_models",
    "ai_tasks",
    "alert",
    "alert_enrichment",  # v0.9.0: Threat intelligence enrichment
    "api_keys",
    "assets",
    "audit",
    "auth",
    "cloud_native",
    "correlation",  # v0.8.0: Event correlation
    "history",
    "ioc_hits",
    "marketplace",
    "monitor",
    "playbook",
    "playbook_definitions",
    "report",
    "root_cause",
    "secrets",
    "security_alerts",  # v0.9.0: External security alert ingestion
    "threat_hunting",
    "threat_intel",
    "timeline",
    "triggers",
    "ueba",
    "users",
    "webhooks",
]
