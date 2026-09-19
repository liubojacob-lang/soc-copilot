"""Alert pipeline lifecycle service.

Wires the automatic alert processing chain that otherwise never runs:

    ingest -> threat-intel enrichment -> correlation -> AI pre-triage

The ingest endpoint only persists alerts and publishes them to the message
queue (consumed by separately deployed workers, if any). This service runs
inside the API process and drives the analysis stages for each new alert:

1. Enrichment: OTX reputation / MITRE tactic context written to
   ``raw_data["threat_intel"]`` (external lookups honour
   ``allow_external_ti``).
2. Correlation: new alerts are batched through the correlation engine,
   which groups related alerts into ``correlated_events`` incidents and
   publishes ``correlation.incident.created`` on the event bus.
3. AI pre-triage: alerts at or above ``alert_pipeline_ai_min_severity``
   get an ``alert_analysis`` task enqueued in the AI task queue (processed
   by the AI task processor); the task id is recorded on the alert.

Each alert is processed exactly once: stage progress is recorded in
``raw_data["pipeline"]``. This matters because the correlation engine has
no built-in incident dedup — re-running the same events would duplicate
incidents — and because OTX lookups should not be repeated per cycle.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select

from core.lifecycle import LifecycleService, ServicePriority
from core.logger import get_logger
from services.prompt_resolution import resolve_prompt

logger = get_logger(__name__)

_SEVERITY_LEVELS = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}

_TRIAGE_PROMPT_TEMPLATE = """You are a SOC triage analyst. Analyze the security alert below and respond with ONLY a JSON object, no other text:
{{"verdict": "true_positive" | "false_positive" | "needs_investigation", "confidence": <0.0-1.0>, "summary": "<one paragraph>", "recommended_actions": ["<action>", ...], "mitre_tactics": ["<TA####>", ...]}}

Constraints:
- Never recommend destructive or defensive-evasion actions (clearing logs, disabling security controls, deleting data).
- Base the verdict only on the provided alert data; do not invent indicators.
- Use "needs_investigation" when the data is ambiguous.

Alert:
{alert_block}"""


class AlertPipelineService(LifecycleService):
    """Background pipeline: enrich -> correlate -> AI triage for new alerts.

    Priority: NORMAL
    Dependencies: database
    """

    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        # Alerts created after this timestamp are candidates. Overlapping the
        # watermark by a few seconds plus the per-alert processed marker makes
        # the pipeline restart-safe without missing in-flight inserts.
        self._watermark: datetime | None = None

    @property
    def name(self) -> str:
        return "alert_pipeline"

    @property
    def priority(self) -> ServicePriority:
        return ServicePriority.NORMAL

    @property
    def dependencies(self) -> list[str]:
        return ["database"]

    async def start(self) -> None:
        from core.config import settings

        if not settings.alert_pipeline_enabled:
            logger.info("Alert pipeline disabled (ALERT_PIPELINE_ENABLED=false)")
            return

        self._watermark = datetime.now(UTC) - timedelta(hours=1)
        self._task = asyncio.create_task(self._run_loop(), name="alert-pipeline-loop")
        logger.info(
            "Alert pipeline started (interval=%ss, batch=%s, ai_min_severity=%s)",
            settings.alert_pipeline_interval_seconds,
            settings.alert_pipeline_batch_size,
            settings.alert_pipeline_ai_min_severity,
        )

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None
        logger.info("Alert pipeline stopped")

    # ── Main loop ──────────────────────────────────────────────────────

    async def _run_loop(self) -> None:
        from core.config import settings

        while True:
            try:
                await self._process_cycle()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Alert pipeline cycle failed: {e}")
            await asyncio.sleep(settings.alert_pipeline_interval_seconds)

    async def _process_cycle(self) -> None:

        assert self._watermark is not None
        await self._enrich_and_triage()
        await self._correlate()
        # Keep the watermark in the past so alerts committed moments before
        # the max-seen timestamp (clock ordering) are still picked up; the
        # processed marker makes the overlap a no-op.
        ceiling = datetime.now(UTC) - timedelta(seconds=5)
        self._watermark = min(self._watermark, ceiling)

    # ── Stage 1+3: enrichment and AI triage ────────────────────────────

    async def _enrich_and_triage(self) -> None:
        from core.config import settings
        from db.session import AsyncSessionLocal
        from models.security_alert import SecurityAlert
        from services.alerting.alert_enrichment import ThreatIntelEnricher

        assert self._watermark is not None
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(SecurityAlert)
                .where(
                    SecurityAlert.deleted_at.is_(None),
                    SecurityAlert.created_at >= self._watermark,
                )
                .order_by(SecurityAlert.created_at.asc())
                .limit(settings.alert_pipeline_batch_size)
            )
            alerts = list(result.scalars().all())
            if not alerts:
                return

            min_level = _SEVERITY_LEVELS.get(
                settings.alert_pipeline_ai_min_severity.lower(), 3
            )

            processed = 0
            async with ThreatIntelEnricher() as enricher:
                enricher.sources["otx"] = settings.allow_external_ti
                for alert in alerts:
                    try:
                        await self._process_one(alert, enricher, min_level, session)
                        processed += 1
                    except Exception as e:
                        logger.warning(f"Pipeline failed for alert {alert.id}: {e}")
                        await session.rollback()
            if processed:
                logger.info(f"Alert pipeline processed {processed} alerts")

            max_created = max(a.created_at for a in alerts if a.created_at)
            if max_created is not None:
                self._watermark = max_created - timedelta(seconds=5)

    async def _process_one(self, alert, enricher, min_level: int, session) -> None:
        from core.prompt_sanitizer import sanitize_prompt_input
        from models.ai_task import AITaskType
        from services.ai_task_service import get_ai_task_service

        raw = dict(alert.raw_data) if alert.raw_data else {}
        pipeline_state = raw.get("pipeline") or {}
        if pipeline_state.get("processed_at"):
            return

        # Stage 1: threat-intel enrichment (skip if already enriched <24h).
        if not raw.get("enriched_at"):
            enrichment = await enricher.enrich_alert(alert)
            raw["threat_intel"] = enrichment

        # Stage 3: AI pre-triage for severe alerts.
        severity_level = _SEVERITY_LEVELS.get((alert.severity or "low").lower(), 1)
        if severity_level >= min_level and not pipeline_state.get("ai_task_id"):
            alert_block = (
                f"severity={alert.severity}\n"
                f"source={alert.source}\n"
                f"rule={alert.rule_id or '-'} (level {alert.rule_level or '-'})\n"
                f"agent={alert.agent_name or '-'}\n"
                f"source_ip={alert.source_ip or '-'}\n"
                f"destination_ip={alert.destination_ip or '-'}\n"
                f"title={sanitize_prompt_input(alert.title or '', max_length=300)}\n"
                f"description={sanitize_prompt_input(alert.description or '', max_length=2000)}"
            )
            # T3.2: triage template overridable via an active "alert_triage"
            # row in the prompt registry.
            triage_template = await resolve_prompt(
                "alert_triage", _TRIAGE_PROMPT_TEMPLATE
            )
            task_id = await get_ai_task_service().submit_task(
                task_type=AITaskType.ALERT_ANALYSIS,
                prompt=triage_template.format(alert_block=alert_block),
                input_data={
                    "alert_id": str(alert.id),
                    "source": alert.source,
                    "severity": alert.severity,
                },
                priority=severity_level * 3,
                timeout_seconds=180,
            )
            pipeline_state["ai_task_id"] = task_id

        pipeline_state["processed_at"] = datetime.now(UTC).isoformat()
        raw["pipeline"] = pipeline_state
        alert.raw_data = raw
        # Commit per alert so partial progress survives a mid-batch failure.
        await session.commit()

    # ── Stage 2: correlation ───────────────────────────────────────────

    async def _correlate(self) -> None:
        from core.config import settings
        from db.session import AsyncSessionLocal
        from models.security_alert import SecurityAlert

        window_start = datetime.now(UTC) - timedelta(
            minutes=settings.alert_pipeline_correlation_window_minutes
        )
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(SecurityAlert)
                .where(
                    SecurityAlert.deleted_at.is_(None),
                    SecurityAlert.created_at >= window_start,
                )
                .order_by(SecurityAlert.created_at.desc())
                .limit(settings.alert_pipeline_correlation_max_events)
            )
            alerts = list(result.scalars().all())

            pending = [a for a in alerts if not self._is_correlated(a)]
            if len(pending) < 2:
                return

            from services.event_correlation_service import EventCorrelationService

            events = [self._to_correlation_event(a) for a in pending]
            incidents = await EventCorrelationService(session).correlate_events(events)

            now_iso = datetime.now(UTC).isoformat()
            for alert in pending:
                raw = dict(alert.raw_data) if alert.raw_data else {}
                state = raw.get("pipeline") or {}
                state["correlated_at"] = now_iso
                raw["pipeline"] = state
                alert.raw_data = raw
            await session.commit()

            if incidents:
                logger.info(
                    f"Alert pipeline correlated {len(pending)} alerts into "
                    f"{len(incidents)} incidents"
                )
                await self._publish_incident_events(incidents)

    @staticmethod
    def _is_correlated(alert) -> bool:
        raw = alert.raw_data or {}
        state = raw.get("pipeline") or {}
        return bool(state.get("correlated_at"))

    @staticmethod
    def _to_correlation_event(alert) -> dict[str, Any]:
        timestamp = alert.event_timestamp or alert.created_at
        return {
            "id": str(alert.id),
            "timestamp": timestamp.isoformat() if timestamp else None,
            "severity": alert.severity,
            "message": f"{alert.title or ''} {alert.description or ''}".strip(),
            "source_ip": alert.source_ip,
            "dest_ip": alert.destination_ip,
            "hostname": alert.agent_name,
            "attack_type": (alert.rule_mitre or "").split(",")[0] or None,
        }

    @staticmethod
    async def _publish_incident_events(incidents) -> None:
        from services.event_bus import get_event_bus

        event_bus = get_event_bus()
        for incident in incidents:
            try:
                await event_bus.publish(
                    event_type="correlation.incident.created",
                    source="alert-pipeline",
                    payload={
                        "incident_id": incident.id,
                        "rule_id": incident.rule_id,
                        "severity": incident.severity,
                        "raw_event_count": incident.raw_event_count,
                    },
                    event_id=str(incident.id),
                    priority=str(incident.severity).lower(),
                )
            except Exception as e:
                logger.warning(f"Failed to publish incident event: {e}")
