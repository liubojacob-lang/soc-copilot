"""Tests for architectural risks and debt fixes.

Verifies:
1. Nmap scan input validation (prevents injection and bad targets/ports)
2. Production security checks (weak password / secret pattern rejection)
3. Database migration auto-run configuration
4. Alert lifecycle escalation data mapping
5. Alert enrichment AbuseIPDB handling
6. System queue statistics and DLQ replay routing
"""

import pytest
from datetime import datetime, UTC
from pydantic import ValidationError

from core.config import Settings
from services.asset_discovery_service import _validate_scan_target, _validate_scan_ports
from schemas.alert_lifecycle import AlertLifecycleResponse, AlertSeverity, AlertStatus, AlertEscalation
from services.alerting.alert_enrichment import ThreatIntelEnricher
from services.message_broker import get_message_broker


# 1. Nmap Scan Target Validation Tests
def test_nmap_valid_targets():
    assert _validate_scan_target("192.168.1.1") == "192.168.1.1"
    assert _validate_scan_target("10.0.0.0/24") == "10.0.0.0/24"
    assert _validate_scan_target("172.16.0.0/16") == "172.16.0.0/16"
    assert _validate_scan_target("localhost") == "localhost"
    assert _validate_scan_target("gateway.internal") == "gateway.internal"


def test_nmap_injection_targets_rejected():
    dangerous_inputs = [
        "-sS",
        "--script=vuln",
        "-p 80",
        "192.168.1.1; whoami",
        "192.168.1.1 && ls",
        "192.168.1.1 | rm -rf /",
        "`id`",
        "",
        "   ",
        "--stylesheet",
    ]
    for bad in dangerous_inputs:
        with pytest.raises(ValueError):
            _validate_scan_target(bad)


# 2. Nmap Scan Port Validation Tests
def test_nmap_valid_ports():
    assert _validate_scan_ports("80") == "80"
    assert _validate_scan_ports("80,443") == "80,443"
    assert _validate_scan_ports("1-1024") == "1-1024"
    assert _validate_scan_ports("22,80-90,443,8080") == "22,80-90,443,8080"
    assert _validate_scan_ports(None) is None


def test_nmap_invalid_ports_rejected():
    invalid_ports = [
        "-p 80",
        "80; echo bad",
        "0",
        "70000",
        "100-50",
        "http,https",
        "80,99999",
        "-1",
    ]
    for bad in invalid_ports:
        with pytest.raises(ValueError):
            _validate_scan_ports(bad)


# 3. Production Configuration Security Tests
def test_config_production_rejects_weak_jwt():
    with pytest.raises(ValidationError):
        Settings(
            environment="production",
            jwt_secret="short",
            bootstrap_admin_password="SuperSecurePassword123!@",
            secret_encryption_key="x" * 44,
        )

    with pytest.raises(ValidationError):
        Settings(
            environment="production",
            jwt_secret="changeme-secret-default-jwt-token-12345",
            bootstrap_admin_password="SuperSecurePassword123!@",
            secret_encryption_key="x" * 44,
        )


def test_config_production_rejects_weak_admin_password():
    with pytest.raises(ValidationError):
        Settings(
            environment="production",
            jwt_secret="a" * 32,
            bootstrap_admin_password="admin12345678",
            secret_encryption_key="x" * 44,
        )


def test_config_auto_run_migrations_setting():
    s = Settings(auto_run_migrations=False)
    assert s.auto_run_migrations is False
    s_default = Settings()
    assert s_default.auto_run_migrations is True


# 4. Alert Lifecycle Escalation Mapping Tests
def test_alert_lifecycle_escalated_response():
    now = datetime.now(UTC)
    escalation = AlertEscalation(
        escalated_to="tier2_analyst",
        escalated_by="tier1_analyst",
        reason="Detected lateral movement requiring Tier 2 deep dive",
        escalated_at=now,
    )
    resp = AlertLifecycleResponse(
        alert_id="101",
        status=AlertStatus.ESCALATED,
        severity=AlertSeverity.HIGH,
        escalated=escalation,
        notes=[],
        created_at=now,
        updated_at=now,
        first_seen=now,
        last_seen=now,
        timeline=[],
    )
    assert resp.escalated is not None
    assert resp.escalated.escalated_to == "tier2_analyst"
    assert "lateral movement" in resp.escalated.reason


# 5. Alert Enrichment ThreatIntelEnricher Initialization Tests
def test_threat_intel_enricher_init(monkeypatch):
    monkeypatch.delenv("ABUSEIPDB_API_KEY", raising=False)
    monkeypatch.delenv("VIRUSTOTAL_API_KEY", raising=False)
    enricher = ThreatIntelEnricher()
    assert enricher.sources["otx"] is True
    assert enricher.sources["abuseipdb"] is False

    monkeypatch.setenv("ABUSEIPDB_API_KEY", "dummy_key")
    enricher2 = ThreatIntelEnricher()
    assert enricher2.sources["abuseipdb"] is True


# 6. Queue Broker & Stats Tests
def test_queue_broker_stats():
    broker = get_message_broker()
    stats = broker.get_queue_stats()
    assert isinstance(stats, dict)
    assert "dlq" in stats
