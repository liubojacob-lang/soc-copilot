"""
告警分析器标准输出 Schema v1.0
SOC Copilot - Security Operations Center Intelligent Analysis Platform
"""

from datetime import datetime
from typing import List, Optional, Dict
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum

try:
    from playbook_engine.triggers.alert_triggers import AlertTriggerConfig
except ImportError:
    AlertTriggerConfig = None


class EventCategory(str, Enum):
    INITIAL_ACCESS = "initial_access"
    EXECUTION = "execution"
    PERSISTENCE = "persistence"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DEFENSE_EVASION = "defense_evasion"
    CREDENTIAL_ACCESS = "credential_access"
    DISCOVERY = "discovery"
    LATERAL_MOVEMENT = "lateral_movement"
    COLLECTION = "collection"
    COMMAND_AND_CONTROL = "command_and_control"
    EXFILTRATION = "exfiltration"
    IMPACT = "impact"
    RECONNAISSANCE = "reconnaissance"
    MALWARE = "malware"
    PHISHING = "phishing"
    DATA_BREACH = "data_breach"
    UNKNOWN = "unknown"


class EventSubCategory(str, Enum):
    PHISHING_CAMPAIGN = "phishing_campaign"
    PHISHING_SPEARPHISHING = "phishing_spearphishing"
    PHISHING_ATTACHMENT = "phishing_attachment"
    BRUTE_FORCE = "brute_force"
    CREDENTIAL_DUMPING = "credential_dumping"
    MALICIOUS_FILE = "malicious_file"
    DNS_TUNNELING = "dns_tunneling"
    RANSOMWARE = "ransomware"
    LATERAL_MOVEMENT = "lateral_movement"
    DATA_EXFILTRATION = "data_exfiltration"
    UNKNOWN = "unknown"


class SeverityLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ConfidenceLevel(str, Enum):
    CERTAIN = "certain"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    SPECULATIVE = "speculative"


class AssetCriticality(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ResponsePriority(str, Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"
    P5 = "P5"


class ActionStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


class Verdict(str, Enum):
    TRUE_POSITIVE = "true_positive"
    FALSE_POSITIVE = "false_positive"
    BENIGN = "benign"
    NEEDS_INVESTIGATION = "needs_investigation"


class AttackPhase(str, Enum):
    RECONNAISSANCE = "reconnaissance"
    WEAPONIZATION = "weaponization"
    DELIVERY = "delivery"
    EXPLOITATION = "exploitation"
    INSTALLATION = "installation"
    COMMAND_AND_CONTROL = "command_and_control"
    ACTIONS_ON_OBJECTIVES = "actions_on_objectives"


class AlertSource(str, Enum):
    SIEM = "siem"
    EDR = "edr"
    NTA = "nta"
    WAF = "waf"
    FIREWALL = "firewall"
    OTHER = "other"


class EvidenceSource(str, Enum):
    LOG = "log"
    ALERT = "alert"
    FLOW = "flow"
    OTHER = "other"


class IOCs(BaseModel):
    ips: List[str] = Field(default_factory=list)
    domains: List[str] = Field(default_factory=list)
    urls: List[str] = Field(default_factory=list)
    hashes: List[str] = Field(default_factory=list)
    emails: List[str] = Field(default_factory=list)
    file_paths: List[str] = Field(default_factory=list)


class IOCStatistics(BaseModel):
    total_count: int = 0
    ip_count: int = 0
    domain_count: int = 0
    url_count: int = 0
    hash_count: int = 0
    unique_countries: List[str] = Field(default_factory=list)
    is_research_related: bool = False


class Entity(BaseModel):
    value: str = ""
    type: str = ""
    count: int = 1


class Entities(BaseModel):
    users: List[Entity] = Field(default_factory=list)
    hosts: List[Entity] = Field(default_factory=list)
    accounts: List[Entity] = Field(default_factory=list)
    processes: List[Entity] = Field(default_factory=list)


class EvidencePoint(BaseModel):
    id: str = ""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source: EvidenceSource = EvidenceSource.LOG
    description: str = ""
    raw_content: str = ""
    key_fields: Dict = Field(default_factory=dict)


class TimelineEvent(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event_type: str = ""
    source_ip: Optional[str] = None
    target_ip: Optional[str] = None
    description: str = ""
    severity: SeverityLevel = SeverityLevel.LOW


class AffectedAsset(BaseModel):
    asset_id: str = ""
    hostname: Optional[str] = None
    ip_addresses: List[str] = Field(default_factory=list)
    criticality: AssetCriticality = AssetCriticality.MEDIUM
    is_compromised: bool = False


class ImpactAssessment(BaseModel):
    affected_assets: List[AffectedAsset] = Field(default_factory=list)
    business_impact_level: SeverityLevel = SeverityLevel.LOW
    data_at_risk: Optional[str] = None
    estimated_recovery_time: Optional[str] = None
    contains_pii: bool = False
    contains_phi: bool = False


class RemediationAction(BaseModel):
    action_id: str = ""
    category: str = ""
    priority: ResponsePriority = ResponsePriority.P3
    title: str = ""
    description: str = ""
    commands: List[str] = Field(default_factory=list)
    verification_steps: List[str] = Field(default_factory=list)
    rollback_steps: List[str] = Field(default_factory=list)


class ThreatIntelResult(BaseModel):
    ioc_type: str = ""
    ioc_value: str = ""
    verdict: str = ""
    confidence: float = 0.0
    provider: str = ""
    tags: List[str] = Field(default_factory=list)


class RootCauseAnalysis(BaseModel):
    primary_cause: str = ""
    contributing_factors: List[str] = Field(default_factory=list)
    attack_vector: str = ""
    initial_compromise_method: str = ""
    attack_phase: AttackPhase = AttackPhase.RECONNAISSANCE
    privilege_escalation_path: List[str] = Field(default_factory=list)
    lateral_movement_path: List[str] = Field(default_factory=list)
    data_accessed: List[str] = Field(default_factory=list)
    data_exfiltrated: List[str] = Field(default_factory=list)


class AlertAnalysisResult(BaseModel):
    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}, protected_namespaces=()
    )

    analysis_version: str = "1.0"
    analysis_timestamp: datetime = Field(default_factory=datetime.utcnow)
    model_used: str = ""
    analysis_duration_ms: int = 0

    alert_id: Optional[str] = None
    alert_name: str = ""
    alert_source: AlertSource = AlertSource.OTHER
    original_raw_log: str = ""

    event_category: EventCategory = EventCategory.UNKNOWN
    event_subcategory: EventSubCategory = EventSubCategory.UNKNOWN
    attack_technique_ids: List[str] = Field(default_factory=list)
    attack_tactic_ids: List[str] = Field(default_factory=list)

    verdict: Verdict = Verdict.NEEDS_INVESTIGATION
    severity: SeverityLevel = SeverityLevel.LOW
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    confidence_score: float = 0.5

    iocs: IOCs = Field(default_factory=IOCs)
    ioc_statistics: IOCStatistics = Field(default_factory=IOCStatistics)
    enriched_iocs: List[ThreatIntelResult] = Field(default_factory=list)

    entities: Entities = Field(default_factory=Entities)
    evidence_points: List[EvidencePoint] = Field(default_factory=list)
    timeline: List[TimelineEvent] = Field(default_factory=list)

    impact: ImpactAssessment = Field(default_factory=ImpactAssessment)
    root_cause: Optional[RootCauseAnalysis] = None

    recommended_actions: List[RemediationAction] = Field(default_factory=list)
    suggested_playbooks: List[str] = Field(default_factory=list)
    escalation_required: bool = False
    escalation_level: Optional[str] = None

    summary: str = ""
    full_narrative: str = ""
    key_findings: List[str] = Field(default_factory=list)
    next_investigation_steps: List[str] = Field(default_factory=list)
    references: List[str] = Field(default_factory=list)

    request_id: str = ""
    degraded_mode: bool = False
    error_message: Optional[str] = None

    def get_severity_icon(self) -> str:
        icons = {
            "critical": "🔴",
            "high": "🟠",
            "medium": "🟡",
            "low": "🟢",
            "info": "🔵",
        }
        return icons.get(self.severity.value, "⚪")

    def is_critical(self) -> bool:
        return self.severity in [SeverityLevel.CRITICAL, SeverityLevel.HIGH]


class AlertAnalysisRequest(BaseModel):
    raw_log: str = Field(..., min_length=10)
    alert_id: Optional[str] = None
    alert_name: Optional[str] = None
    alert_source: Optional[AlertSource] = None


# Playbook 联动常量
ALERT_TO_PLAYBOOK_CONTEXT = {
    "alert.id": "alert.id",
    "alert.severity": "alert.severity",
    "alert.verdict": "alert.verdict",
    "alert.event_category": "alert.event_category",
    "alert.iocs.ips": "context.ioc.ips",
    "alert.iocs.domains": "context.ioc.domains",
    "alert.entities.hosts": "context.entity.hosts",
    "alert.impact.risk_score": "context.impact.risk_score",
    "alert.escalation_required": "response.escalation_required",
}

TRIGGER_CONDITION_TEMPLATES = {
    "critical_alert": {
        "field": "alert.severity",
        "operator": "in",
        "value": ["critical", "high"],
    },
    "true_positive": {
        "field": "alert.verdict",
        "operator": "eq",
        "value": "true_positive",
    },
    "malware": {"field": "alert.event_category", "operator": "eq", "value": "malware"},
    "phishing": {
        "field": "alert.event_category",
        "operator": "eq",
        "value": "phishing",
    },
    "data_exfiltration": {
        "field": "alert.event_category",
        "operator": "eq",
        "value": "exfiltration",
    },
    "c2": {
        "field": "alert.event_category",
        "operator": "eq",
        "value": "command_and_control",
    },
    "pii_exposure": {
        "field": "alert.impact.contains_pii",
        "operator": "eq",
        "value": True,
    },
}


def get_matching_triggers(analysis_result: AlertAnalysisResult) -> List[str]:
    """
    根据告警分析结果返回匹配的触发器ID列表

    Args:
        analysis_result: 告警分析结果

    Returns:
        匹配的触发器ID列表
    """
    matching_triggers = []

    severity = (
        analysis_result.severity.value
        if hasattr(analysis_result.severity, "value")
        else str(analysis_result.severity)
    )
    verdict = (
        analysis_result.verdict.value
        if hasattr(analysis_result.verdict, "value")
        else str(analysis_result.verdict)
    )
    event_category = (
        analysis_result.event_category.value
        if hasattr(analysis_result.event_category, "value")
        else str(analysis_result.event_category)
    )

    if severity in ["critical", "high"]:
        matching_triggers.append("critical_auto_contain")

    if event_category == "malware":
        matching_triggers.append("malware_response")

    if event_category == "phishing":
        matching_triggers.append("phishing_investigation")

    if event_category == "command_and_control":
        matching_triggers.append("c2_traffic")

    if event_category == "exfiltration" or "exfiltration" in event_category:
        matching_triggers.append("data_exfiltration")

    if analysis_result.impact.contains_pii:
        matching_triggers.append("pii_exposure")

    if verdict == "true_positive" and analysis_result.confidence_score >= 0.7:
        matching_triggers.append("high_confidence_positive")

    return matching_triggers
