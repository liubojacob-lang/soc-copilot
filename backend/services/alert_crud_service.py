"""
Alert CRUD Service with Triage State Machine

Provides business-level operations:
- Full CRUD (create, read, update, delete / soft-archive)
- List with search, filtering, pagination, and ordering
- Statistics aggregation
- Triage workflow state machine with transition validation and audit logging
"""

import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from models.asset import AssetDB
from models.audit_log import AuditLogModel
from models.security_alert import SecurityAlert
from repositories.alert_repository import AlertRepository
from schemas.alert_schema import (
    AlertCreate,
    AlertFilter,
    AlertResponse,
    AlertStats,
    AlertTriageRequest,
    AlertUpdate,
    BatchStatusUpdate,
    AlertTriageResponse,
)
from schemas.common import PaginatedData, PaginationParams
from services.base import BaseService

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Auto-triage configuration
# ---------------------------------------------------------------------------

# Severity → base priority score (1-5)
SEVERITY_PRIORITY_MAP: dict[str, int] = {
    "critical": 5,
    "high": 4,
    "medium": 3,
    "low": 2,
    "info": 1,
}

# Asset criticality → priority bonus
ASSET_CRITICALITY_BONUS: dict[str, int] = {
    "critical": 3,
    "high": 2,
    "medium": 1,
    "low": 0,
}

# Known attack patterns → (priority_boost, auto_status)
KNOWN_ATTACK_PATTERNS: list[dict[str, Any]] = [
    # ── Brute Force ──
    {
        "label": "brute_force",
        "patterns": [
            r"brute.?force", r"bruteforce", r"password.?spray", r"password.?guessing",
            r"credential.?stuffing", r"auth.?failure", r"failed.?login",
            r"multiple.?login.?attempt", r"too many.*(?:auth|login)",
            r"SSH.*(?:brute|dictionary)", r"RDP.*(?:brute|login.?attack)",
            r"(?:exceeded|exceed).*login", r"account.*lockout",
        ],
        "priority_boost": 2,
        "suggested_status": "triaged",
    },
    # ── Lateral Movement ──
    {
        "label": "lateral_movement",
        "patterns": [
            r"lateral.?movement", r"pass.?the.?hash", r"pass.?the.?ticket",
            r"PsExec", r"wmi.*exec", r"remote.*(?:execution|exec)",
            r"WinRM", r"SMB.*(?:relay|lateral)", r"remote.*desktop.*(?:anomal|suspicious)",
            r"RDP.*tunneling", r"(?:psexec|wmiexec|smbexec|atexec|dcomexec)",
            r"WMI.*(?:exec|process)", r"schtasks.*(?:remote|create).*\\",
        ],
        "priority_boost": 3,
        "suggested_status": "investigating",
    },
    # ── Data Exfiltration ──
    {
        "label": "data_exfiltration",
        "patterns": [
            r"data.?exfil", r"data.?leak", r"data.?breach",
            r"exfiltrat", r"large.*(?:upload|transfer|outbound)",
            r"DNS.*tunnel", r"icmp.*tunnel", r"covert.*channel",
            r"(?:massive|unusual).*(?:upload|egress|outbound)",
            r"data.*(?:stolen|theft|export)", r"(?:dataloss|data.?loss)",
            r"sensitive.*(?:file|data).*accessed", r"classified.*(?:accessed|retrieved)",
            r"cloud.*storage.*(?:sync|upload).*(?:suspicious|anomal)",
        ],
        "priority_boost": 3,
        "suggested_status": "investigating",
    },
    # ── Malware / C2 ──
    {
        "label": "malware_c2",
        "patterns": [
            r"malware", r"ransomware", r"trojan", r"backdoor",
            r"command.?and.?control", r"c2.*comm", r"botnet",
            r"beacon", r"Cobalt.?Strike", r"meterpreter",
            r"reverse.?shell", r"bind.?shell", r"webshell",
            r"(?:dropper|downloader|loader)", r"payload.*execut",
            r"powershell.*(?:download|encoded|bypass)",
            r"(?:kvC|certutil).*download",
        ],
        "priority_boost": 3,
        "suggested_status": "investigating",
    },
    # ── Privilege Escalation ──
    {
        "label": "privilege_escalation",
        "patterns": [
            r"privilege.?escalat", r"privesc", r"(?:elevat|escalat).*privilege",
            r"SUID", r"sudo.*exploit", r"root.*escalat",
            r"SeImpersonate", r"SeDebugPrivilege", r"token.*(?:impersonat|manipulat)",
            r"UAC.*bypass", r"(?:kernel|driver).*exploit",
            r"DirtyCow", r"(?:dirty.?pipe|polkit)",
        ],
        "priority_boost": 3,
        "suggested_status": "investigating",
    },
    # ── Phishing ──
    {
        "label": "phishing",
        "patterns": [
            r"phish", r"spear.?phish", r"whaling",
            r"malicious.*email", r"suspicious.*attachment", r"spoof.*email",
            r"social.?engineering", r"(?:fake|clone).*login",
            r"credential.*harvest", r"business.*email.*compromis", r"BEC",
        ],
        "priority_boost": 2,
        "suggested_status": "triaged",
    },
    # ── Reconnaissance ──
    {
        "label": "reconnaissance",
        "patterns": [
            r"recon", r"port.?scan", r"vulnerability.?scan",
            r"network.?scan", r"service.?enum", r"nmap", r"masscan",
            r"directory.?(?:traversal|listing)", r"(?:path|file).*disclosure",
            r"information.?disclosure", r"open.*port.*detected",
        ],
        "priority_boost": 1,
        "suggested_status": "triaged",
    },
    # ── Denial of Service ──
    {
        "label": "denial_of_service",
        "patterns": [
            r"(?:denial|DoS|DDoS).*service", r"DDoS", r"(?:flood|amplification).*attack",
            r"SYN.?flood", r"UDP.?flood", r"HTTP.?flood",
            r"resource.?exhaustion", r"slow.?loris", r"slow.?read",
        ],
        "priority_boost": 2,
        "suggested_status": "triaged",
    },
]


def _priority_to_label(score: int) -> str:
    """Convert numeric priority score to human-readable label."""
    if score >= 5:
        return "urgent"
    if score >= 3:
        return "high"
    if score >= 1:
        return "medium"
    return "low"


@dataclass
class AutoTriageResult:
    """Result of auto-triage analysis."""

    alert_id: int
    severity: str
    base_priority: int = 0
    asset_bonus: int = 0
    attack_bonus: int = 0
    total_priority: int = 0
    priority_label: str = "low"
    matched_patterns: list[str] = field(default_factory=list)
    matched_asset: str | None = None
    asset_criticality: str | None = None
    suggested_status: str = "new"
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "severity": self.severity,
            "base_priority": self.base_priority,
            "asset_bonus": self.asset_bonus,
            "attack_bonus": self.attack_bonus,
            "total_priority": self.total_priority,
            "priority_label": self.priority_label,
            "matched_patterns": self.matched_patterns,
            "matched_asset": self.matched_asset,
            "asset_criticality": self.asset_criticality,
            "suggested_status": self.suggested_status,
            "reason": self.reason,
        }


# ---------------------------------------------------------------------------
# Triage state machine
# ---------------------------------------------------------------------------

# Allowed transitions – every key maps to the set of allowed *next* states.
ALERT_TRANSITIONS: dict[str, list[str]] = {
    "new": ["triaged"],
    "triaged": ["investigating", "resolved", "false_positive"],
    "investigating": ["resolved", "false_positive"],
    "resolved": ["reopened"],
    "false_positive": ["reopened"],
    "reopened": ["triaged"],
}

# States that are considered "closed" (no further action unless reopened).
TERMINAL_STATES = {"resolved", "false_positive"}

# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class AlertCRUDService(BaseService):
    """Service for alert CRUD and triage operations.

    Owns transaction boundaries (explicit commit / rollback via BaseService).
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session=session)
        self.repo = AlertRepository(session=session)

    # ==================================================================
    # CREATE
    # ==================================================================

    async def create_alert(
        self, data: AlertCreate, created_by: str | None = None
    ) -> AlertResponse:
        """Create a new alert from user input.

        - Automatically sets tenant_id (default "default")
        - Validates required fields
        - Converts list fields to delimited strings for storage
        - Records audit log
        """
        kwargs = data.model_dump(exclude_unset=False)
        kwargs.pop("rule_groups", None)
        kwargs.pop("rule_mitre", None)
        kwargs.pop("tags", None)
        kwargs.pop("mitre_tactics", None)
        kwargs.pop("mitre_techniques", None)
        kwargs.pop("iocs", None)

        # Convert list fields to comma-separated strings / JSON
        if data.rule_groups:
            kwargs["rule_groups"] = ",".join(data.rule_groups)
        if data.rule_mitre:
            kwargs["rule_mitre"] = ",".join(data.rule_mitre)
        if data.tags is not None:
            kwargs["tags"] = json.dumps(data.tags)
        if data.mitre_tactics is not None:
            kwargs["mitre_tactics"] = json.dumps(data.mitre_tactics)
        if data.mitre_techniques is not None:
            kwargs["mitre_techniques"] = json.dumps(data.mitre_techniques)
        if data.iocs is not None:
            kwargs["iocs"] = json.dumps(data.iocs)

        kwargs["status"] = "new"
        kwargs.setdefault("tenant_id", "default")
        kwargs.setdefault("external_event_id", f"manual-{datetime.now(UTC).timestamp():.0f}")

        alert = await self.repo.create_alert(**kwargs)

        await self._audit(
            action="alert_created",
            target_id=str(alert.id),
            user_id=created_by,
            extra={"title": alert.title, "severity": alert.severity, "source": alert.source},
        )

        logger.info(
            "Alert created  id=%s  title=%s  severity=%s",
            alert.id, alert.title, alert.severity,
        )
        return self._to_response(alert)

    # ==================================================================
    # READ
    # ==================================================================

    async def get_alert(self, alert_id: int) -> AlertResponse | None:
        """Retrieve a single alert by id."""
        alert = await self.repo.get_by_id(alert_id)
        return self._to_response(alert) if alert else None

    async def list_alerts(
        self,
        filters: AlertFilter | None = None,
        pagination: PaginationParams | None = None,
    ) -> PaginatedData[AlertResponse]:
        """
        List alerts with optional filtering, search, and pagination.

        Supported filters:
        - Exact match: status, severity, source, event_type, agent_name, source_ip, assigned_to
        - Full-text search: title, description, source_ip, destination_ip, external_event_id, agent_name
        - Time range: created_from / created_to
        - Tenant isolation (via AlertFilter.tenant_id)
        """
        filter_dict: dict[str, Any] = {}
        search: str | None = None
        created_from: datetime | None = None
        created_to: datetime | None = None

        if filters is not None:
            if filters.status is not None:
                filter_dict["status"] = filters.status
            if filters.severity is not None:
                filter_dict["severity"] = filters.severity.lower()
            if filters.source is not None:
                filter_dict["source"] = filters.source
            if filters.event_type is not None:
                filter_dict["event_type"] = filters.event_type
            if filters.agent_name is not None:
                filter_dict["agent_name"] = filters.agent_name
            if filters.source_ip is not None:
                filter_dict["source_ip"] = filters.source_ip
            if filters.assigned_to is not None:
                filter_dict["assigned_to"] = filters.assigned_to
            if filters.tenant_id is not None:
                filter_dict["tenant_id"] = filters.tenant_id

            search = filters.search
            created_from = filters.created_from
            created_to = filters.created_to

        page = pagination.page if pagination else 1
        page_size = pagination.page_size if pagination else 20

        alerts, total = await self.repo.list_alerts(
            filters=filter_dict or None,
            search=search,
            created_from=created_from,
            created_to=created_to,
            pagination=pagination or PaginationParams(page=page, page_size=page_size),
        )

        return PaginatedData.create(
            items=[self._to_response(a) for a in alerts],
            total=total,
            page=page,
            page_size=page_size,
        )

    # ==================================================================
    # UPDATE
    # ==================================================================

    async def update_alert(
        self, alert_id: int, data: AlertUpdate, updated_by: str | None = None
    ) -> AlertResponse | None:
        """Update alert metadata fields.  Does NOT change the triage status."""
        kwargs = data.model_dump(exclude_unset=True, exclude_none=True)

        # Handle list-to-string conversions for fields stored as CSV / JSON
        list_fields_map = {
            "rule_groups": ("rule_groups", lambda v: ",".join(v) if isinstance(v, list) else v),
            "rule_mitre": ("rule_mitre", lambda v: ",".join(v) if isinstance(v, list) else v),
            "tags": ("tags", lambda v: json.dumps(v) if isinstance(v, list) else v),
            "mitre_tactics": ("mitre_tactics", lambda v: json.dumps(v) if isinstance(v, list) else v),
            "mitre_techniques": ("mitre_techniques", lambda v: json.dumps(v) if isinstance(v, list) else v),
            "iocs": ("iocs", lambda v: json.dumps(v) if isinstance(v, dict) else v),
        }
        for key, (target, transform) in list_fields_map.items():
            if key in kwargs:
                kwargs[target] = transform(kwargs.pop(key))

        alert = await self.repo.update_alert(alert_id, **kwargs)
        if alert is None:
            return None

        await self._audit(
            action="alert_updated",
            target_id=str(alert_id),
            user_id=updated_by,
            extra={"updated_fields": list(kwargs.keys())},
        )

        logger.info("Alert %d updated fields=%s", alert_id, list(kwargs.keys()))
        return self._to_response(alert)

    # ==================================================================
    # DELETE
    # ==================================================================

    async def delete_alert(
        self, alert_id: int, deleted_by: str | None = None
    ) -> bool:
        """
        Delete an alert permanently.

        NOTE: For audit-trail retention, consider soft-archiving instead
        (e.g. set status to a pseudo-state "archived" and keep the record).
        """
        alert = await self.repo.get_by_id(alert_id)
        if alert is None:
            return False

        await self._audit(
            action="alert_deleted",
            target_id=str(alert_id),
            user_id=deleted_by,
            extra={"title": alert.title, "severity": alert.severity},
        )

        deleted = await self.repo.delete_alert(alert_id)
        if deleted:
            logger.info("Alert %d permanently deleted", alert_id)
        return deleted

    # ==================================================================
    # BATCH
    # ==================================================================

    async def batch_update_status(
        self, data: BatchStatusUpdate, changed_by: str | None = None
    ) -> int:
        """Bulk-update status for a set of alerts."""
        now = datetime.now(UTC)
        count = await self.repo.batch_update_status(
            alert_ids=data.alert_ids,
            new_status=data.new_status.value,
            resolved_by=changed_by,
            resolution_note=data.resolution_note,
            updated_at=now,
        )

        await self._audit(
            action="alert_batch_status_change",
            target_id=f"batch:{len(data.alert_ids)}",
            user_id=changed_by,
            extra={
                "count": count,
                "new_status": data.new_status.value,
            },
        )

        logger.info(
            "Batch status update  count=%d  new_status=%s", count, data.new_status.value
        )
        return count

    # ==================================================================
    # STATISTICS
    # ==================================================================

    async def get_alert_stats(
        self, tenant_id: str | None = None
    ) -> AlertStats:
        """Return aggregate alert statistics."""
        raw = await self.repo.get_alert_stats(tenant_id=tenant_id)
        return AlertStats(**raw)

    # ==================================================================
    # TRIAGE STATE MACHINE
    # ==================================================================

    async def change_status(
        self,
        alert_id: int,
        data: AlertTriageRequest,
        user_id: str | None = None,
    ) -> AlertTriageResponse:
        """Transition an alert to a new triage status.

        Validation:
        - Transition must be allowed per ALERT_TRANSITIONS table.
        - Skips are rejected (e.g. "new" → "resolved" is blocked).

        Side effects:
        - resolved_at is automatically set when transitioning to a terminal state.
        - An audit log entry is written for every status change.
        - previous_status is recovered from the database, not from client input.
        """
        alert = await self.repo.get_by_id(alert_id)
        if alert is None:
            raise ValueError(f"Alert {alert_id} not found")

        old_status = alert.status
        new_status = data.new_status.value

        if new_status == old_status:
            raise ValueError(f"Alert {alert_id} is already in status '{old_status}'")

        # --- transition validation ---
        allowed = ALERT_TRANSITIONS.get(old_status, [])
        if new_status not in allowed:
            raise ValueError(
                f"Invalid transition '{old_status}' → '{new_status}'. "
                f"Allowed next states from '{old_status}' are: {allowed}"
            )

        now = datetime.now(UTC)
        update_kwargs: dict[str, Any] = {
            "status": new_status,
            "updated_at": now,
        }

        if data.resolution_note is not None:
            update_kwargs["resolution_note"] = data.resolution_note
        if data.root_cause is not None:
            update_kwargs["root_cause"] = data.root_cause

        # auto-set resolved_at when moving to terminal states
        if new_status in TERMINAL_STATES:
            update_kwargs["resolved_at"] = now
            update_kwargs["resolved_by"] = user_id

        updated = await self.repo.update_alert(alert_id, **update_kwargs)
        if updated is None:
            raise RuntimeError(f"Failed to update alert {alert_id}")

        # --- audit ---
        await self._audit(
            action="alert_status_changed",
            target_id=str(alert_id),
            user_id=user_id,
            extra={
                "old_status": old_status,
                "new_status": new_status,
                "resolution_note": data.resolution_note,
            },
        )

        logger.info(
            "Alert %d status  %s → %s  by=%s",
            alert_id, old_status, new_status, user_id,
        )

        return AlertTriageResponse(
            alert_id=alert_id,
            old_status=old_status,
            new_status=new_status,
            changed_by=user_id or "system",
            changed_at=now,
            resolution_note=data.resolution_note,
        )


    # ==================================================================
    # AUTO TRIAGE
    # ==================================================================

    async def auto_triage(self, alert_id: int) -> AutoTriageResult:
        """Automatically triage an alert based on severity, asset value, and attack patterns.

        Rules in priority order:
        1. Severity → base priority score (critical=5, high=4, medium=3, low=2, info=1)
        2. Asset value → bonus if source_ip matches a known asset with high criticality
        3. Attack pattern matching → bonus if title/description/event_type match known TTPs

        Returns AutoTriageResult with suggested status and priority.
        """
        alert = await self.repo.get_by_id(alert_id)
        if alert is None:
            raise ValueError(f"Alert {alert_id} not found")

        severity = (alert.severity or "info").lower()
        base_priority = SEVERITY_PRIORITY_MAP.get(severity, 1)

        reasons: list[str] = [f"Severity={severity} → base priority {base_priority}"]

        # ── Step 1: Asset correlation ──
        asset_bonus = 0
        matched_asset: str | None = None
        asset_criticality: str | None = None

        if alert.source_ip:
            try:
                asset_result = await self.session.execute(
                    select(AssetDB).where(
                        AssetDB.ip == alert.source_ip,
                        AssetDB.is_active == True,  # noqa: E712
                    )
                )
                asset = asset_result.scalar_one_or_none()
                if asset is not None:
                    matched_asset = asset.hostname
                    asset_criticality = (asset.criticality or "low").lower()
                    asset_bonus = ASSET_CRITICALITY_BONUS.get(asset_criticality, 0)
                    if asset_bonus > 0:
                        reasons.append(
                            f"Source IP {alert.source_ip} matches asset "
                            f"'{matched_asset}' (criticality={asset_criticality}) → +{asset_bonus}"
                        )
            except Exception as exc:
                logger.warning("Asset lookup failed for auto-triage: %s", exc)

        # ── Step 2: Attack pattern matching ──
        # Build searchable text from alert fields
        search_text = " ".join(
            v
            for v in [
                alert.title or "",
                alert.description or "",
                alert.event_type or "",
                alert.rule_groups or "",
                alert.full_log[:2000] if alert.full_log else "",  # limit log size
            ]
            if v
        ).lower()

        attack_bonus = 0
        matched_patterns: list[str] = []
        suggested_status = "new"

        for attack in KNOWN_ATTACK_PATTERNS:
            for pattern in attack["patterns"]:
                if re.search(pattern, search_text, re.IGNORECASE):
                    if attack["label"] not in matched_patterns:
                        matched_patterns.append(attack["label"])
                        attack_bonus += attack["priority_boost"]
                        # Escalate status: investigating > triaged > new
                        if attack["suggested_status"] == "investigating":
                            suggested_status = "investigating"
                        elif (
                            attack["suggested_status"] == "triaged"
                            and suggested_status != "investigating"
                        ):
                            suggested_status = "triaged"
                    break  # one match per category is enough

        if matched_patterns:
            reasons.append(
                f"Attack patterns matched: {', '.join(matched_patterns)} → +{attack_bonus}"
            )

        # ── Step 3: Compute total ──
        total_priority = base_priority + asset_bonus + attack_bonus
        priority_label = _priority_to_label(total_priority)

        # Build final reason
        reason = " | ".join(reasons)
        reason += f" → Total priority: {total_priority} ({priority_label})"

        result = AutoTriageResult(
            alert_id=alert_id,
            severity=severity,
            base_priority=base_priority,
            asset_bonus=asset_bonus,
            attack_bonus=attack_bonus,
            total_priority=total_priority,
            priority_label=priority_label,
            matched_patterns=matched_patterns,
            matched_asset=matched_asset,
            asset_criticality=asset_criticality,
            suggested_status=suggested_status,
            reason=reason,
        )

        logger.info(
            "Auto-triage alert=%d sev=%s priority=%d(%s) status=%s patterns=%s",
            alert_id,
            severity,
            total_priority,
            priority_label,
            suggested_status,
            matched_patterns,
        )

        return result

    # ==================================================================
    # HELPERS
    # ==================================================================

    def _to_response(self, alert: SecurityAlert) -> AlertResponse:
        """Map an ORM SecurityAlert instance to the pydantic AlertResponse."""
        return AlertResponse(
            id=alert.id,
            tenant_id=alert.tenant_id,
            source=alert.source,
            external_event_id=alert.external_event_id,
            event_type=alert.event_type,
            severity=alert.severity,
            title=alert.title,
            description=alert.description,
            source_ip=alert.source_ip,
            destination_ip=alert.destination_ip,
            protocol=alert.protocol,
            agent_name=alert.agent_name,
            agent_id=alert.agent_id,
            agent_ip=alert.agent_ip,
            rule_id=alert.rule_id,
            rule_level=alert.rule_level,
            rule_groups=alert.rule_groups,
            rule_mitre=alert.rule_mitre,
            full_log=alert.full_log,
            location=alert.location,
            geoip=alert.geoip,
            raw_data=alert.raw_data,
            tags=json.loads(alert.tags) if isinstance(alert.tags, str) else alert.tags,
            classification=alert.classification,
            fingerprint=alert.fingerprint,
            aggregated_count=alert.aggregated_count or 1,
            last_seen_at=alert.last_seen_at,
            status=alert.status,
            assigned_to=alert.assigned_to,
            assigned_at=alert.assigned_at,
            resolution_note=alert.resolution_note,
            root_cause=alert.root_cause,
            remediation=alert.remediation,
            resolved_at=alert.resolved_at,
            resolved_by=alert.resolved_by,
            escalated_to=alert.escalated_to,
            escalated_at=alert.escalated_at,
            escalation_reason=alert.escalation_reason,
            threat_score=alert.threat_score,
            enriched_at=alert.enriched_at,
            iocs=alert.iocs,
            mitre_tactics=alert.mitre_tactics,
            mitre_techniques=alert.mitre_techniques,
            created_at=alert.created_at,
            updated_at=alert.updated_at,
            event_timestamp=alert.event_timestamp,
        )

    async def _audit(
        self,
        action: str,
        target_id: str,
        user_id: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        """Write an audit log row.  Non-critical – errors are logged but not raised."""
        import uuid

        try:
            audit = AuditLogModel(
                id=str(uuid.uuid4()),
                user_id=user_id,
                action=action,
                method="SYSTEM",
                path="/api/alerts",
                status_code=200,
                target_type="security_alert",
                target_id=target_id,
                extra_json=extra or {},
            )
            self.session.add(audit)
            await self.session.flush()
        except Exception:
            logger.exception("Failed to write audit log for action=%s target=%s", action, target_id)

    # ==================================================================
    # BATCH UPDATE (comprehensive)  —  v0.9.0
    # ==================================================================

    async def batch_update_alerts(
        self,
        items: list[dict[str, Any]],
        changed_by: str | None = None,
    ) -> dict[str, Any]:
        """Comprehensive batch update: severity, status, assigned_to, resolution_note.

        Args:
            items: List of dicts, each containing alert_id + optional update fields:
                   {alert_id, severity?, status?, assigned_to?, resolution_note?}
            changed_by: User performing the batch operation

        Returns:
            {total, success_count, failed_count, errors: [{alert_id, error}]}
        """
        total = len(items)
        success_count = 0
        failed_count = 0
        errors: list[dict[str, Any]] = []

        for item in items:
            alert_id = item.get("alert_id")
            if not alert_id:
                failed_count += 1
                errors.append({"alert_id": None, "error": "Missing alert_id"})
                continue

            try:
                update_fields: dict[str, Any] = {}
                if "severity" in item and item["severity"] is not None:
                    update_fields["severity"] = item["severity"]
                if "status" in item and item["status"] is not None:
                    update_fields["status"] = item["status"]
                if "assigned_to" in item and item["assigned_to"] is not None:
                    update_fields["assigned_to"] = item["assigned_to"]
                if "resolution_note" in item and item["resolution_note"] is not None:
                    update_fields["resolution_note"] = item["resolution_note"]

                if not update_fields:
                    failed_count += 1
                    errors.append({"alert_id": alert_id, "error": "No fields to update"})
                    continue

                updated = await self.repo.update_alert(alert_id, **update_fields)
                if updated is None:
                    failed_count += 1
                    errors.append({"alert_id": alert_id, "error": "Alert not found"})
                    continue

                await self._audit(
                    action="alert_batch_update",
                    target_id=str(alert_id),
                    user_id=changed_by,
                    extra={"updated_fields": list(update_fields.keys())},
                )
                success_count += 1

            except Exception as e:
                failed_count += 1
                errors.append({"alert_id": alert_id, "error": str(e)})
                logger.warning("Batch update failed for alert %d: %s", alert_id, e)

        logger.info(
            "Batch alert update: total=%d success=%d failed=%d by=%s",
            total, success_count, failed_count, changed_by,
        )
        return {
            "total": total,
            "success_count": success_count,
            "failed_count": failed_count,
            "errors": errors,
        }
