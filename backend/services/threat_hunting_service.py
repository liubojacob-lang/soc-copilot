"""
Threat Hunting Service - Proactive Threat Discovery
Enables hypothesis-driven hunting and automated threat detection.

Hunt execution queries the ingested security alerts (security_alerts table)
with parameterized SQLAlchemy filters; findings are derived from real alert
data — no simulated results are produced in apply paths.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

from core.logger import get_logger
from db.session import AsyncSession
from models.security_alert import SecurityAlert

logger = get_logger(__name__)


class HuntType(Enum):
    """Types of threat hunting."""

    IOC_HUNT = "ioc_hunt"  # Hunt for known IOCs
    HYPOTHESIS = "hypothesis"  # Hypothesis-driven
    BEHAVIORAL = "behavioral"  # Behavioral anomaly
    ML_BASED = "ml_based"  # ML anomaly detection


class HuntStatus(Enum):
    """Status of hunt."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class HuntHypothesis:
    """Threat hunting hypothesis."""

    id: str
    name: str
    description: str
    mitre_techniques: list[str]
    data_sources: list[str]
    query_logic: str
    severity: str
    created_by: str
    created_at: datetime


@dataclass
class HuntFinding:
    """Finding from threat hunt."""

    id: str
    hunt_id: str
    entity_type: str
    entity_id: str
    description: str
    confidence: float
    severity: str
    evidence: dict[str, Any]
    recommended_actions: list[str]
    found_at: datetime


@dataclass
class HuntResult:
    """Complete hunt result."""

    hunt_id: str
    hunt_name: str
    status: HuntStatus
    started_at: datetime
    completed_at: datetime | None
    total_entities_scanned: int
    findings: list[HuntFinding]
    statistics: dict[str, Any]


class ThreatHuntingEngine:
    """Threat hunting engine."""

    def __init__(self):
        self.active_hunts: dict[str, HuntResult] = {}
        self.hunt_library: dict[str, HuntHypothesis] = {}
        self._initialize_default_hypotheses()

    def _initialize_default_hypotheses(self):
        """Initialize default hunting hypotheses based on MITRE ATT&CK."""
        default_hypotheses = [
            HuntHypothesis(
                id="hunt_001",
                name="Lateral Movement via SMB",
                description="Detect potential lateral movement through unusual SMB connections",
                mitre_techniques=["T1021.002"],
                data_sources=["network_traffic", "windows_events"],
                query_logic="""
                    SELECT src_ip, dst_ip, count(*) as connection_count
                    FROM network_events
                    WHERE protocol = 'SMB' 
                    AND dst_port = 445
                    AND timestamp > now() - interval '24 hours'
                    GROUP BY src_ip, dst_ip
                    HAVING count(*) > 100
                """,
                severity="high",
                created_by="system",
                created_at=datetime.now(),
            ),
            HuntHypothesis(
                id="hunt_002",
                name="PowerShell Obfuscation",
                description="Detect obfuscated PowerShell commands",
                mitre_techniques=["T1059.001", "T1027"],
                data_sources=["process_creation", "command_line"],
                query_logic="""
                    SELECT process_id, command_line, user
                    FROM process_events
                    WHERE process_name ILIKE '%powershell%'
                    AND (
                        command_line ILIKE '%[Convert]::FromBase64%'
                        OR command_line ILIKE '%-enc%'
                        OR command_line ILIKE '%-encodedcommand%'
                        OR LENGTH(command_line) > 1000
                    )
                """,
                severity="critical",
                created_by="system",
                created_at=datetime.now(),
            ),
            HuntHypothesis(
                id="hunt_003",
                name="Persistence via Scheduled Tasks",
                description="Detect suspicious scheduled task creation",
                mitre_techniques=["T1053.005"],
                data_sources=["windows_events", "file_events"],
                query_logic="""
                    SELECT task_name, author, command
                    FROM scheduled_tasks
                    WHERE created_time > now() - interval '7 days'
                    AND (
                        command ILIKE '%powershell%'
                        OR command ILIKE '%cmd%'
                        OR command ILIKE '%wscript%'
                        OR command ILIKE '%cscript%'
                    )
                """,
                severity="high",
                created_by="system",
                created_at=datetime.now(),
            ),
            HuntHypothesis(
                id="hunt_004",
                name="Data Exfiltration via DNS",
                description="Detect potential data exfiltration over DNS",
                mitre_techniques=["T1071.004"],
                data_sources=["dns_logs", "network_traffic"],
                query_logic="""
                    SELECT src_ip, dns_query, count(*) as query_count
                    FROM dns_events
                    WHERE timestamp > now() - interval '1 hour'
                    AND LENGTH(dns_query) > 50
                    GROUP BY src_ip, dns_query
                    HAVING count(*) > 100
                """,
                severity="medium",
                created_by="system",
                created_at=datetime.now(),
            ),
            HuntHypothesis(
                id="hunt_005",
                name="Kerberoasting Activity",
                description="Detect potential Kerberoasting attacks",
                mitre_techniques=["T1558.003"],
                data_sources=["windows_events", "authentication_logs"],
                query_logic="""
                    SELECT user, service_name, count(*) as ticket_count
                    FROM kerberos_events
                    WHERE event_type = 'TGS-REQ'
                    AND timestamp > now() - interval '24 hours'
                    GROUP BY user, service_name
                    HAVING count(*) > 5
                """,
                severity="critical",
                created_by="system",
                created_at=datetime.now(),
            ),
        ]

        for hypothesis in default_hypotheses:
            self.hunt_library[hypothesis.id] = hypothesis

        logger.info(f"Initialized {len(default_hypotheses)} default hunt hypotheses")

    async def create_custom_hypothesis(
        self,
        name: str,
        description: str,
        mitre_techniques: list[str],
        data_sources: list[str],
        query_logic: str,
        severity: str,
        created_by: str,
    ) -> HuntHypothesis:
        """
        Create custom hunting hypothesis.

        Args:
            name: Hypothesis name
            description: Detailed description
            mitre_techniques: List of MITRE ATT&CK technique IDs
            data_sources: Required data sources
            query_logic: SQL or query logic
            severity: Severity level
            created_by: User creating the hypothesis

        Returns:
            Created hypothesis
        """
        hypothesis_id = f"hunt_{len(self.hunt_library) + 1:03d}"

        hypothesis = HuntHypothesis(
            id=hypothesis_id,
            name=name,
            description=description,
            mitre_techniques=mitre_techniques,
            data_sources=data_sources,
            query_logic=query_logic,
            severity=severity,
            created_by=created_by,
            created_at=datetime.now(),
        )

        self.hunt_library[hypothesis_id] = hypothesis
        logger.info(f"Created custom hypothesis: {hypothesis_id}")

        return hypothesis

    async def execute_hunt(
        self, hypothesis_id: str, time_range_hours: int = 24, db: AsyncSession = None
    ) -> HuntResult:
        """
        Execute threat hunt based on hypothesis.

        Args:
            hypothesis_id: Hypothesis to hunt for
            time_range_hours: Time range to hunt in
            db: Database session

        Returns:
            Hunt results
        """
        hypothesis = self.hunt_library.get(hypothesis_id)
        if not hypothesis:
            raise ValueError(f"Hypothesis {hypothesis_id} not found")

        hunt_id = f"hunt_exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        result = HuntResult(
            hunt_id=hunt_id,
            hunt_name=hypothesis.name,
            status=HuntStatus.RUNNING,
            started_at=datetime.now(),
            completed_at=None,
            total_entities_scanned=0,
            findings=[],
            statistics={},
        )

        self.active_hunts[hunt_id] = result
        started_at = datetime.now()

        try:
            logger.info(f"Starting hunt {hunt_id}: {hypothesis.name}")

            # Real execution: search ingested alerts matching the hypothesis
            findings, entities_scanned = await self._execute_hunt_query(
                hypothesis=hypothesis, time_range_hours=time_range_hours, db=db
            )

            result.findings = findings
            result.total_entities_scanned = entities_scanned
            result.status = HuntStatus.COMPLETED
            result.completed_at = datetime.now()
            elapsed = max((datetime.now() - started_at).total_seconds(), 0.001)
            result.statistics = {
                "entities_scanned": result.total_entities_scanned,
                "findings_count": len(findings),
                "high_severity": len([f for f in findings if f.severity == "high"]),
                "execution_time_seconds": round(elapsed, 3),
                "time_range_hours": time_range_hours,
            }

            logger.info(f"Completed hunt {hunt_id} with {len(findings)} findings")

        except Exception as e:
            logger.exception(f"Hunt {hunt_id} failed")
            result.status = HuntStatus.FAILED
            result.completed_at = datetime.now()
            result.statistics = {"error": str(e)}

        return result

    # Keyword sets per built-in hypothesis. All matching goes through
    # AlertRepository.list_alerts (bound-parameter search); the keywords are
    # compile-time constants and never user-controlled text.
    _HUNT_PATTERNS: dict[str, dict[str, list[str]]] = {
        "hunt_001": {  # Lateral movement (SMB / psexec / remote execution)
            "text": ["lateral", "smb", "psexec", "winrm", "wmic"],
        },
        "hunt_002": {  # Obfuscated PowerShell
            "text": ["powershell", "encodedcommand", "frombase64"],
        },
        "hunt_003": {  # Persistence via scheduled tasks
            "text": ["scheduled task", "schtasks", "persistence"],
        },
        "hunt_004": {  # DNS exfiltration
            "text": ["dns"],
        },
        "hunt_005": {  # Kerberoasting
            "text": ["kerberoasting", "kerberos"],
        },
    }

    async def _execute_hunt_query(
        self, hypothesis: HuntHypothesis, time_range_hours: int, db: AsyncSession
    ) -> tuple[list[HuntFinding], int]:
        """Search ingested security alerts matching the hypothesis keywords.

        Delegates to AlertRepository.list_alerts (parameterized search across
        title/description/IP/agent fields with a time window and real count).
        Returns (findings, entities_scanned) where entities_scanned is the
        largest real total reported across the keyword searches.
        """
        from repositories.alert_repository import AlertRepository
        from schemas.common import PaginationParams

        since = datetime.now(UTC).replace(tzinfo=None) - timedelta(
            hours=time_range_hours
        )
        keyword_groups = self._HUNT_PATTERNS.get(hypothesis.id, {})
        keywords = [k for group in keyword_groups.values() for k in group]

        if not keywords:
            logger.warning(
                "No search keywords for hypothesis %s; returning no findings",
                hypothesis.id,
            )
            return [], 0

        repo = AlertRepository(db)
        merged: dict[Any, SecurityAlert] = {}
        entities_scanned = 0

        for keyword in keywords:
            alerts, total = await repo.list_alerts(
                search=keyword,
                created_from=since,
                pagination=PaginationParams(
                    page=1, page_size=50, sort_by="created_at", sort_order="desc"
                ),
            )
            entities_scanned = max(entities_scanned, total)
            for alert in alerts:
                merged[alert.id] = alert

        rows = sorted(
            merged.values(),
            key=lambda a: a.created_at or datetime.now(UTC).replace(tzinfo=None),
            reverse=True,
        )[:100]

        findings = []
        for idx, alert in enumerate(rows, start=1):
            findings.append(
                HuntFinding(
                    id="finding_" + str(idx),
                    hunt_id=hypothesis.id,
                    entity_type="alert",
                    entity_id=str(alert.id),
                    description=alert.title,
                    confidence=0.9,
                    severity=alert.severity or hypothesis.severity,
                    evidence={
                        "alert_id": str(alert.id),
                        "source": alert.source,
                        "event_type": alert.event_type,
                        "source_ip": alert.source_ip,
                        "destination_ip": alert.destination_ip,
                        "agent_name": alert.agent_name,
                        "rule_id": alert.rule_id,
                        "rule_mitre": alert.rule_mitre,
                        "event_timestamp": (
                            alert.event_timestamp.isoformat()
                            if alert.event_timestamp
                            else None
                        ),
                    },
                    recommended_actions=[
                        "Review the alert details",
                        "Correlate with related alerts",
                        "Escalate to incident response if confirmed",
                    ],
                    found_at=datetime.now(),
                )
            )

        return findings, entities_scanned

    async def ioc_hunt(
        self,
        iocs: list[dict[str, str]],
        time_range_days: int = 30,
        db: AsyncSession = None,
    ) -> list[HuntFinding]:
        """
        Hunt for Indicators of Compromise (IOCs).

        Searches the ingested security alerts via AlertRepository: exact
        matches on the source/destination IP columns plus the repository's
        parameterized full-text search over title/description/IP/agent/log
        fields. Only real matches produce findings; unmatched IOCs return
        nothing.
        """
        if db is None:
            raise ValueError("A database session is required for IOC hunting")

        from repositories.alert_repository import AlertRepository
        from schemas.common import PaginationParams

        since = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=time_range_days)
        findings: list[HuntFinding] = []
        repo = AlertRepository(db)
        page = PaginationParams(
            page=1, page_size=50, sort_by="created_at", sort_order="desc"
        )

        for ioc in iocs:
            ioc_type = ioc.get("type")
            ioc_value = (ioc.get("value") or "").strip()
            if not ioc_value:
                continue

            logger.info("Hunting for IOC: %s=%s", ioc_type, ioc_value)

            merged: dict[Any, SecurityAlert] = {}
            for field in ("source_ip", "destination_ip"):
                exact, _total = await repo.list_alerts(
                    filters={field: ioc_value}, created_from=since, pagination=page
                )
                for alert in exact:
                    merged[alert.id] = alert

            text_hits, _total = await repo.list_alerts(
                search=ioc_value, created_from=since, pagination=page
            )
            for alert in text_hits:
                merged[alert.id] = alert

            if not merged:
                # No evidence of this IOC in ingested data — report nothing
                continue

            rows = sorted(
                merged.values(),
                key=lambda a: a.created_at or datetime.now(UTC).replace(tzinfo=None),
                reverse=True,
            )[:50]
            timestamps = [a.created_at for a in rows if a.created_at is not None]
            findings.append(
                HuntFinding(
                    id="ioc_finding_" + str(len(findings) + 1),
                    hunt_id="ioc_hunt",
                    entity_type=ioc_type or "ioc",
                    entity_id=ioc_value,
                    description="IOC observed in "
                    + str(len(rows))
                    + " ingested alert(s)",
                    confidence=0.95,
                    severity="high",
                    evidence={
                        "match_count": len(rows),
                        "first_seen": (
                            min(timestamps).isoformat() if timestamps else None
                        ),
                        "last_seen": (
                            max(timestamps).isoformat() if timestamps else None
                        ),
                        "sample_alert_ids": [str(a.id) for a in rows[:5]],
                        "sample_agents": list(
                            {a.agent_name for a in rows if a.agent_name}
                        )[:5],
                    },
                    recommended_actions=[
                        "Block IP",
                        "Check affected hosts",
                        "Review firewall rules",
                    ],
                    found_at=datetime.now(),
                )
            )

        return findings

    async def get_hunt_library(self) -> list[HuntHypothesis]:
        """Get all available hunt hypotheses."""
        return list(self.hunt_library.values())

    async def get_hunt_results(
        self, hunt_id: str | None = None, limit: int = 50
    ) -> list[HuntResult]:
        """Get hunt execution results."""
        if hunt_id:
            result = self.active_hunts.get(hunt_id)
            return [result] if result else []

        # Return recent hunts
        sorted_hunts = sorted(
            self.active_hunts.values(), key=lambda x: x.started_at, reverse=True
        )
        return sorted_hunts[:limit]


# Global threat hunting engine
_threat_hunting_engine: ThreatHuntingEngine | None = None


def get_threat_hunting_engine() -> ThreatHuntingEngine:
    """Get or create global threat hunting engine."""
    global _threat_hunting_engine
    if _threat_hunting_engine is None:
        _threat_hunting_engine = ThreatHuntingEngine()
    return _threat_hunting_engine


async def initialize_threat_hunting():
    """Initialize threat hunting on application startup."""
    global _threat_hunting_engine
    _threat_hunting_engine = ThreatHuntingEngine()
    logger.info("Threat hunting engine initialized")


async def close_threat_hunting():
    """Cleanup threat hunting on application shutdown."""
    global _threat_hunting_engine
    if _threat_hunting_engine:
        logger.info("Threat hunting engine closed")
        _threat_hunting_engine = None
