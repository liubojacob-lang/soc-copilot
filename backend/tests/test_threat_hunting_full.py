"""
Comprehensive tests for Threat Hunting Engine, Sigma detection rule engine,
and Threat Hunting API router endpoints.
"""

from __future__ import annotations

import unittest.mock as mock
from datetime import datetime

import pytest
from httpx import AsyncClient

from services.threat_hunting.sigma_engine import (
    SigmaEngine,
    SigmaRule,
    get_sigma_engine,
)
from services.threat_hunting_service import (
    HuntHypothesis,
    HuntResult,
    HuntStatus,
    ThreatHuntingEngine,
    close_threat_hunting,
    get_threat_hunting_engine,
    initialize_threat_hunting,
)


# ─────────────────────────────────────────────────────────────
# 1. ThreatHuntingEngine Unit Tests
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_threat_hunting_engine_initialization():
    engine = ThreatHuntingEngine()
    hypotheses = await engine.get_hunt_library()
    assert len(hypotheses) >= 2
    rule_ids = [h.id for h in hypotheses]
    assert "hunt_001" in rule_ids


@pytest.mark.asyncio
async def test_threat_hunting_engine_create_custom_hypothesis():
    engine = ThreatHuntingEngine()
    custom = await engine.create_custom_hypothesis(
        name="DNS Tunneling Activity",
        description="Detect unusually high volume of subdomains queried via TXT records",
        mitre_techniques=["T1071.004"],
        data_sources=["dns_logs", "zeek_dns"],
        query_logic="SELECT domain, count(distinct subdomain) FROM dns_queries GROUP BY domain HAVING count(*) > 500",
        severity="high",
        created_by="lead_hunter",
    )

    assert custom.id.startswith("hunt_")
    assert custom.name == "DNS Tunneling Activity"
    assert custom.severity == "high"
    assert custom.created_by == "lead_hunter"

    library = await engine.get_hunt_library()
    assert any(h.id == custom.id for h in library)


@pytest.mark.asyncio
async def test_threat_hunting_engine_execute_hunt_success():
    engine = ThreatHuntingEngine()
    result = await engine.execute_hunt("hunt_001", time_range_hours=12)

    assert result.hunt_id.startswith("hunt_exec_")
    assert result.status == HuntStatus.COMPLETED
    assert result.completed_at is not None
    assert result.total_entities_scanned > 0
    assert len(result.findings) >= 1
    assert result.statistics["findings_count"] == len(result.findings)


@pytest.mark.asyncio
async def test_threat_hunting_engine_execute_hunt_not_found():
    engine = ThreatHuntingEngine()
    with pytest.raises(ValueError, match="Hypothesis nonexistent_hunt not found"):
        await engine.execute_hunt("nonexistent_hunt")


@pytest.mark.asyncio
async def test_threat_hunting_engine_ioc_hunt():
    engine = ThreatHuntingEngine()
    iocs = [
        {"type": "ip", "value": "185.220.101.5", "description": "Tor exit node"},
        {"type": "domain", "value": "malware-c2-domain.com", "description": "Known Cobalt Strike C2"},
    ]

    findings = await engine.ioc_hunt(iocs, time_range_days=7)
    assert len(findings) >= 1
    ip_finding = next((f for f in findings if f.entity_id == "185.220.101.5"), None)
    assert ip_finding is not None
    assert ip_finding.confidence >= 0.8
    assert "Block IP" in ip_finding.recommended_actions


@pytest.mark.asyncio
async def test_threat_hunting_lifecycle_and_results_retrieval():
    await initialize_threat_hunting()
    engine = get_threat_hunting_engine()
    assert engine is not None

    # Execute hunt
    res1 = await engine.execute_hunt("hunt_001", time_range_hours=6)
    # Ensure second hunt has a unique id in active_hunts
    res2_id = f"{res1.hunt_id}_sub"
    engine.active_hunts[res2_id] = HuntResult(
        hunt_id=res2_id,
        hunt_name="Secondary Hunt",
        status=HuntStatus.COMPLETED,
        started_at=datetime.now(),
        completed_at=datetime.now(),
        total_entities_scanned=500,
        findings=[],
        statistics={"findings_count": 0},
    )

    all_results = await engine.get_hunt_results(limit=10)
    assert len(all_results) >= 2

    # Query single hunt by id
    single_res = await engine.get_hunt_results(hunt_id=res2_id)
    assert len(single_res) == 1
    assert single_res[0].hunt_id == res2_id

    await close_threat_hunting()


# ─────────────────────────────────────────────────────────────
# 2. Sigma Rule Engine Unit Tests
# ─────────────────────────────────────────────────────────────

def test_sigma_engine_rules_loading():
    engine = get_sigma_engine()
    rules = engine.get_all_rules()
    assert len(rules) > 0

    categories = engine.get_categories()
    assert len(categories) > 0

    first_rule = rules[0]
    rule_detail = engine.get_rule(first_rule.id)
    assert rule_detail is not None
    assert rule_detail.id == first_rule.id
    assert rule_detail.title == first_rule.title

    # Filter by category
    cat_rules = engine.get_rules_by_category(first_rule.category)
    assert len(cat_rules) >= 1
    assert all(r.category == first_rule.category for r in cat_rules)


# ─────────────────────────────────────────────────────────────
# 3. Threat Hunting API Router Endpoints Tests
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_hunt_hypotheses_api(auth_client: AsyncClient):
    response = await auth_client.get("/api/v1/threat-hunting/hypotheses")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert "mitre_techniques" in data[0]


@pytest.mark.asyncio
async def test_create_hunt_hypothesis_api(auth_client: AsyncClient):
    payload = {
        "name": "Suspicious Shadow Copy Deletion",
        "description": "Adversaries may delete Volume Shadow Copies to hinder data recovery after ransomware encryption.",
        "mitre_techniques": ["T1490"],
        "data_sources": ["windows_events", "process_creation"],
        "query_logic": "process_name = 'vssadmin.exe' AND command_line LIKE '%delete shadows%'",
        "severity": "critical",
    }
    response = await auth_client.post("/api/v1/threat-hunting/hypotheses", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == payload["name"]
    assert data["severity"] == "critical"
    assert data["id"].startswith("hunt_")


@pytest.mark.asyncio
async def test_execute_hunt_api(auth_client: AsyncClient):
    payload = {
        "hypothesis_id": "hunt_001",
        "time_range_hours": 24,
    }
    response = await auth_client.post("/api/v1/threat-hunting/execute", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["hunt_id"].startswith("hunt_exec_")
    assert data["status"] in ("completed", "running")
    assert "findings" in data
    assert "statistics" in data


@pytest.mark.asyncio
async def test_ioc_hunt_api(auth_client: AsyncClient):
    payload = {
        "iocs": [
            {"type": "ip", "value": "198.51.100.23", "description": "Suspicious Scanner"},
        ],
        "time_range_days": 14,
    }
    response = await auth_client.post("/api/v1/threat-hunting/ioc-hunt", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "hunt_id" in data
    assert data["total_iocs"] == 1
    assert "findings" in data
    assert "statistics" in data


@pytest.mark.asyncio
async def test_get_hunt_results_api(auth_client: AsyncClient):
    # Ensure at least one execution
    await auth_client.post(
        "/api/v1/threat-hunting/execute",
        json={"hypothesis_id": "hunt_001", "time_range_hours": 1},
    )

    response = await auth_client.get("/api/v1/threat-hunting/results?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert "hunt_id" in data[0]


@pytest.mark.asyncio
async def test_get_hunting_dashboard_api(auth_client: AsyncClient):
    response = await auth_client.get("/api/v1/threat-hunting/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert "top_mitre_techniques" in data
    assert "hunt_effectiveness" in data


@pytest.mark.asyncio
async def test_sigma_rules_api_endpoints(auth_client: AsyncClient):
    # 1. List rules
    response = await auth_client.get("/api/v1/threat-hunting/sigma/rules")
    assert response.status_code == 200
    rules = response.json()
    assert isinstance(rules, list)
    assert len(rules) > 0

    first_rule_id = rules[0]["id"]

    # 2. Get categories
    cat_resp = await auth_client.get("/api/v1/threat-hunting/sigma/rules/categories")
    assert cat_resp.status_code == 200
    cat_data = cat_resp.json()
    assert "categories" in cat_data

    # 3. Rule detail
    detail_resp = await auth_client.get(f"/api/v1/threat-hunting/sigma/rules/{first_rule_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["id"] == first_rule_id
    assert "title" in detail

    # 4. 404 for invalid rule
    not_found_resp = await auth_client.get("/api/v1/threat-hunting/sigma/rules/invalid_rule_999")
    assert not_found_resp.status_code == 404
