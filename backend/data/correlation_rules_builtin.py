"""Built-in correlation rules for SOC Copilot.

These rules are automatically seeded during database migration/initialization.
"""

from core.logger import get_logger

logger = get_logger(__name__)

BUILTIN_CORRELATION_RULES = [
    {
        "name": "Brute Force Attack - Multiple Failed Logins",
        "description": "Correlates multiple failed login attempts from the same source IP or username within 5 minutes",
        "time_window_seconds": 300,
        "entity_types": {"ip_address": True, "username": True, "hostname": False},
        "min_similarity": 0.5,
        "conditions": {
            "min_event_count": 3,
            "category": ["authentication", "brute_force"],
        },
        "action": "aggregate",
        "priority": 90,
        "group_by_field": "source_ip",
    },
    {
        "name": "Port Scanning - Multiple Port Access",
        "description": "Correlates multiple port access attempts from the same source IP within 2 minutes",
        "time_window_seconds": 120,
        "entity_types": {"ip_address": True, "username": False, "hostname": False},
        "min_similarity": 0.6,
        "conditions": {"min_event_count": 5, "category": ["network", "port_scan"]},
        "action": "aggregate",
        "priority": 85,
        "group_by_field": "source_ip",
    },
    {
        "name": "Malware Outbreak - Same IOCs Across Assets",
        "description": "Correlates malware detections with same file hash/domain across different assets within 1 hour",
        "time_window_seconds": 3600,
        "entity_types": {
            "ip_address": False,
            "username": False,
            "hostname": True,
            "domains": True,
        },
        "min_similarity": 0.7,
        "conditions": {"min_event_count": 2, "category": ["malware", "endpoint"]},
        "action": "escalate",
        "action_params": {"escalation severity": "critical"},
        "priority": 95,
        "group_by_field": "ioc_hash",
    },
    {
        "name": "Lateral Movement - Unusual Asset Hopping",
        "description": "Correlates authentication/access events across multiple assets for the same user within 10 minutes",
        "time_window_seconds": 600,
        "entity_types": {"ip_address": False, "username": True, "hostname": True},
        "min_similarity": 0.6,
        "conditions": {
            "min_event_count": 3,
            "category": ["authentication", "lateral_movement"],
        },
        "action": "aggregate",
        "priority": 90,
        "group_by_field": "username",
    },
    {
        "name": "Data Exfiltration - Large Data Transfer",
        "description": "Correlates large data transfer events from the same user/IP within 5 minutes",
        "time_window_seconds": 300,
        "entity_types": {"ip_address": True, "username": True, "hostname": True},
        "min_similarity": 0.7,
        "conditions": {
            "min_event_count": 2,
            "min_severity": "medium",
            "category": ["data_exfiltration", "network"],
        },
        "action": "escalate",
        "action_params": {"escalation severity": "high"},
        "priority": 92,
        "group_by_field": None,
    },
    {
        "name": "Phishing Campaign - Same URL/Domain",
        "description": "Correlates phishing alerts with same URL or domain across multiple users within 24 hours",
        "time_window_seconds": 86400,
        "entity_types": {
            "ip_address": False,
            "username": False,
            "hostname": False,
            "domains": True,
        },
        "min_similarity": 0.8,
        "conditions": {"min_event_count": 2, "category": ["phishing", "email"]},
        "action": "aggregate",
        "priority": 88,
        "group_by_field": "phishing_url",
    },
    {
        "name": "DDoS Attack - High Volume from Same Source",
        "description": "Correlates high-frequency requests from same source IP within 1 minute",
        "time_window_seconds": 60,
        "entity_types": {"ip_address": True, "username": False, "hostname": False},
        "min_similarity": 0.5,
        "conditions": {"min_event_count": 50, "category": ["network", "ddos"]},
        "action": "escalate",
        "action_params": {"escalation severity": "critical"},
        "priority": 97,
        "group_by_field": "source_ip",
    },
    {
        "name": "Insider Threat - After-Hours Access",
        "description": "Correlates after-hours access events for the same user across multiple days",
        "time_window_seconds": 604800,  # 7 days
        "entity_types": {"ip_address": False, "username": True, "hostname": True},
        "min_similarity": 0.6,
        "conditions": {
            "min_event_count": 3,
            "category": ["authentication", "insider_threat"],
        },
        "action": "aggregate",
        "priority": 80,
        "group_by_field": "username",
    },
    {
        "name": "Web Application Attack - Same Attack Pattern",
        "description": "Correlates web attacks (SQLi, XSS, etc.) with same pattern against same target within 30 minutes",
        "time_window_seconds": 1800,
        "entity_types": {"ip_address": True, "username": False, "hostname": True},
        "min_similarity": 0.7,
        "conditions": {
            "min_event_count": 3,
            "category": ["web_attack", "sql_injection", "xss"],
        },
        "action": "aggregate",
        "priority": 87,
        "group_by_field": "target_hostname",
    },
    {
        "name": "Ransomware - Multiple Encrypted Files",
        "description": "Correlates ransomware-related file encryption events across same asset within 5 minutes",
        "time_window_seconds": 300,
        "entity_types": {"ip_address": False, "username": False, "hostname": True},
        "min_similarity": 0.8,
        "conditions": {
            "min_event_count": 5,
            "category": ["ransomware", "malware", "endpoint"],
        },
        "action": "escalate",
        "action_params": {
            "escalation severity": "critical",
            "auto_playbook": "ransomware_response",
        },
        "priority": 99,
        "group_by_field": "hostname",
    },
]


async def seed_builtin_rules(db_session) -> int:
    """
    Seed built-in correlation rules to database.

    Returns:
        Number of rules created
    """
    from models.correlation_rule import CorrelationRule
    from sqlalchemy import select

    created_count = 0

    for rule_data in BUILTIN_CORRELATION_RULES:
        # Check if rule already exists
        query = select(CorrelationRule).where(CorrelationRule.name == rule_data["name"])
        result = await db_session.execute(query)
        existing = result.scalar_one_or_none()

        if existing:
            logger.info(f"Built-in rule already exists: {rule_data['name']}")
            continue

        # Create new rule
        rule = CorrelationRule(
            **rule_data, is_builtin=True, enabled=True, created_by="system"
        )

        db_session.add(rule)
        created_count += 1
        logger.info(f"Created built-in rule: {rule_data['name']}")

    await db_session.commit()

    return created_count
