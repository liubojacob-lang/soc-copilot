"""API routers module."""

from . import (
    alert,
    report,
    ai_models,
    timeline,
    history,
    assets,
    ioc_hits,
    threat_intel,
    playbook,
    playbook_definitions,
    auth,
    users,
    api_keys,
    audit,
    webhooks,
    triggers,
    secrets,
    admin_settings,
    dify,
    ai,
    ai_tasks,
    marketplace,
    ueba,
    threat_hunting,
    cloud_native,
    monitor,
    correlation,  # v0.8.0: Event correlation
    security_alerts,  # v0.9.0: External security alert ingestion
    alert_enrichment,  # v0.9.0: Threat intelligence enrichment
    wazuh_event_receiver,  # v1.1.0: Event-driven Wazuh webhook receiver
)

__all__ = [
    "alert",
    "report",
    "ai_models",
    "timeline",
    "history",
    "assets",
    "ioc_hits",
    "threat_intel",
    "playbook",
    "playbook_definitions",
    "auth",
    "users",
    "api_keys",
    "audit",
    "webhooks",
    "triggers",
    "secrets",
    "admin_settings",
    "dify",
    "ai",
    "ai_tasks",
    "marketplace",
    "ueba",
    "threat_hunting",
    "cloud_native",
    "monitor",
    "correlation",  # v0.8.0: Event correlation
    "security_alerts",  # v0.9.0: External security alert ingestion
    "alert_enrichment",  # v0.9.0: Threat intelligence enrichment
    "wazuh_event_receiver",  # v1.1.0: Event-driven Wazuh webhook receiver
]
