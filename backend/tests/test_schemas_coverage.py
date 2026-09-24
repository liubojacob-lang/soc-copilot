"""Tests for Pydantic schemas in alert_analysis, playbook_dag, and alert_schema."""

from datetime import UTC, datetime

from schemas.alert_analysis import (
    AffectedAsset,
    AlertAnalysisResult,
    AssetCriticality,
    AttackPhase,
    ConfidenceLevel,
    EventCategory,
    EventSubCategory,
    EvidencePoint,
    EvidenceSource,
    ImpactAssessment,
    IOCs,
    RemediationAction,
    ResponsePriority,
    RootCauseAnalysis,
    SeverityLevel,
    Verdict,
    get_matching_triggers,
)
from schemas.alert_analysis import (
    AlertSource as AnalysisAlertSource,
)
from schemas.alert_schema import (
    AlertCreate,
    AlertFilter,
    AlertSeverity,
    AlertSource,
    AlertStats,
    AlertStatus,
    AlertUpdate,
    BatchStatusUpdate,
)
from schemas.playbook_dag import (
    DAGSchema,
    EdgeSchema,
    NodeRunStatus,
    NodeSchema,
    PlaybookDefinitionCreate,
    PlaybookDefinitionUpdate,
)

# ── Alert Analysis Schemas ──────────────────────────────────────────────


def test_alert_analysis_enums():
    assert EventCategory.MALWARE == "malware"
    assert EventSubCategory.RANSOMWARE == "ransomware"
    assert SeverityLevel.CRITICAL == "critical"
    assert ConfidenceLevel.HIGH == "high"
    assert Verdict.TRUE_POSITIVE == "true_positive"
    assert AssetCriticality.HIGH == "high"
    assert ResponsePriority.P1 == "P1"
    assert AttackPhase.RECONNAISSANCE == "reconnaissance"


def test_alert_analysis_result_model():
    res = AlertAnalysisResult(
        alert_id="alt-001",
        alert_name="Ransomware Detected",
        alert_source=AnalysisAlertSource.SIEM,
        event_category=EventCategory.MALWARE,
        event_subcategory=EventSubCategory.RANSOMWARE,
        severity=SeverityLevel.CRITICAL,
        confidence=ConfidenceLevel.HIGH,
        confidence_score=0.95,
        verdict=Verdict.TRUE_POSITIVE,
        summary="Ransomware execution detected on web server",
        reasoning="Suspicious process encrypted multiple files in rapid succession",
        attack_technique_ids=["T1486"],
        attack_tactic_ids=["TA0040"],
        iocs=IOCs(
            file_hashes=[
                "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
            ],
            ip_addresses=["192.168.1.50"],
        ),
        impact=ImpactAssessment(
            affected_assets=[
                AffectedAsset(
                    hostname="web-prod-01",
                    criticality=AssetCriticality.HIGH,
                    is_compromised=True,
                )
            ],
            business_impact_level=SeverityLevel.CRITICAL,
            contains_pii=True,
        ),
        remediation_actions=[
            RemediationAction(
                action_id="isolate-host",
                title="Isolate host from network",
                priority=ResponsePriority.P1,
            )
        ],
        evidence=[
            EvidencePoint(
                description="Sysmon Event ID 1: Process create",
                source=EvidenceSource.LOG,
                confidence=ConfidenceLevel.HIGH,
            )
        ],
        root_cause_analysis=RootCauseAnalysis(
            primary_cause="Phishing email attachment executed",
            attack_vector="email",
            attack_phase=AttackPhase.DELIVERY,
        ),
    )

    assert res.alert_id == "alt-001"
    assert res.confidence_score == 0.95
    assert len(res.attack_technique_ids) == 1
    assert res.impact.contains_pii is True

    # Test get_matching_triggers
    triggers = get_matching_triggers(res)
    assert "critical_auto_contain" in triggers
    assert "malware_response" in triggers
    assert "pii_exposure" in triggers
    assert "high_confidence_positive" in triggers


def test_get_matching_triggers_branches():
    # Test phishing
    res = AlertAnalysisResult(
        alert_id="alt-002",
        event_category=EventCategory.PHISHING,
        severity=SeverityLevel.MEDIUM,
        confidence=ConfidenceLevel.HIGH,
        confidence_score=0.8,
        verdict=Verdict.NEEDS_INVESTIGATION,
        summary="Phishing attempt",
        reasoning="Suspicious link",
    )
    triggers = get_matching_triggers(res)
    assert "phishing_investigation" in triggers
    assert "critical_auto_contain" not in triggers

    # Test C2
    res_c2 = AlertAnalysisResult(
        alert_id="alt-003",
        event_category=EventCategory.COMMAND_AND_CONTROL,
        severity=SeverityLevel.HIGH,
        confidence=ConfidenceLevel.HIGH,
        confidence_score=0.85,
        verdict=Verdict.TRUE_POSITIVE,
        summary="C2 beaconing",
    )
    triggers_c2 = get_matching_triggers(res_c2)
    assert "c2_traffic" in triggers_c2
    assert "critical_auto_contain" in triggers_c2
    assert "high_confidence_positive" in triggers_c2


# ── Playbook DAG Schemas ────────────────────────────────────────────────


def test_playbook_dag_node_and_edge():
    node = NodeSchema(
        id="node-1",
        name="Extract IOCs",
        type="extract_iocs",
        config={"threshold": 3},
        inputs={"raw": "payload"},
        inputs_template={"target_ip": "{{context.ip}}"},
    )
    assert node.id == "node-1"
    assert node.resolved_inputs == {"target_ip": "{{context.ip}}"}

    edge = EdgeSchema(
        source="node-1",
        target="node-2",
        condition="$.output.score > 50",
    )
    assert edge.source == "node-1"
    assert edge.condition == "$.output.score > 50"

    dag = DAGSchema(nodes=[node], edges=[edge])
    assert len(dag.nodes) == 1
    assert len(dag.edges) == 1


def test_playbook_definition_schemas():
    create_req = PlaybookDefinitionCreate(
        name="Automated Incident Response",
        description="Quarantine infected host and notify oncall",
        dag=DAGSchema(
            nodes=[
                NodeSchema(id="n1", name="Check IOC", type="ti_lookup"),
                NodeSchema(id="n2", name="Isolate", type="containment"),
            ],
            edges=[EdgeSchema(source="n1", target="n2")],
        ),
    )
    assert create_req.name == "Automated Incident Response"
    assert len(create_req.dag.nodes) == 2

    update_req = PlaybookDefinitionUpdate(
        name="Renamed Response Playbook",
        is_active=False,
    )
    assert update_req.name == "Renamed Response Playbook"
    assert update_req.is_active is False


def test_playbook_run_step_schema():
    step = NodeRunStatus(
        node_id="n1",
        node_name="Check IOC",
        node_type="ti_lookup",
        status="success",
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
        attempt_count=1,
        last_error=None,
        output_json={"reputation": "malicious"},
    )
    assert step.node_id == "n1"
    assert step.status == "success"
    assert step.output["reputation"] == "malicious"


# ── Alert Schemas ───────────────────────────────────────────────────────


def test_alert_crud_schemas():
    alert_create = AlertCreate(
        source=AlertSource.SURICATA.value,
        title="ET EXPLOIT Suspicious User Agent",
        severity=AlertSeverity.HIGH.value,
        description="Known scanner user-agent detected",
        event_type="network_ids",
        raw_log="GET / HTTP/1.1 200",
    )
    assert alert_create.source == "suricata"
    assert alert_create.severity == "high"

    alert_update = AlertUpdate(
        severity=AlertSeverity.CRITICAL.value,
        description="Escalated to critical",
    )
    assert alert_update.severity == "critical"

    batch_update = BatchStatusUpdate(
        alert_ids=[101, 102, 103],
        new_status=AlertStatus.RESOLVED,
        resolution_note="Bulk resolved false positives",
    )
    assert len(batch_update.alert_ids) == 3

    filter_schema = AlertFilter(
        severity=AlertSeverity.CRITICAL.value,
        status=AlertStatus.NEW.value,
        source="wazuh",
        agent_name="srv-db-01",
    )
    assert filter_schema.severity == "critical"
    assert filter_schema.source == "wazuh"

    stats = AlertStats(
        total=100,
        by_severity={"critical": 10, "high": 30, "medium": 40, "low": 20},
        by_status={"new": 50, "triaged": 20, "resolved": 30},
        last_24h=15,
    )
    assert stats.total == 100
    assert stats.last_24h == 15
