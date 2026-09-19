"""Root cause analysis service (T2.4 minimal closed loop).

Wires the previously orphaned ``root_cause_analyses`` table and the CoT
prompt in ``prompts/root_cause_analysis.md`` into a working flow:

    alert → context assembly → LLM CoT analysis → persist → list/feedback

Design notes:

- Uses the shared ``LLMRetryService`` structured path (schema injection +
  retries + circuit breaker).
- When the LLM is unavailable the service REFUSES to fabricate an analysis
  (the T1.1 principle): a degraded RCA is worse than no RCA, so the caller
  gets a 503 instead of persisted fiction.
"""

import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from models.root_cause_analysis import RootCauseAnalysis
from models.security_alert import SecurityAlert
from schemas.root_cause import RootCauseFeedbackRequest, RootCauseLLMResult
from services.llm_retry import get_llm_retry_service

logger = get_logger(__name__)

_PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "root_cause_analysis.md"
_PROMPT_VERSION = "cot-v1"
_VALID_PRIORITIES = {"critical", "high", "medium", "low"}
_MAX_SIMILAR_ALERTS = 5


class RootCauseAlertNotFoundError(Exception):
    """The requested alert does not exist (or is soft-deleted)."""


class RootCauseAnalysisNotFoundError(Exception):
    """The requested analysis record does not exist."""


class AIServiceUnavailableError(Exception):
    """LLM degraded — refusing to fabricate a root cause analysis."""


class RootCauseAnalysisService:
    """Orchestrates AI root cause analyses for security alerts."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ------------------------------------------------------------------ #
    # Analysis
    # ------------------------------------------------------------------ #

    async def analyze(self, alert_id: int) -> RootCauseAnalysis:
        alert = await self._get_alert(alert_id)
        context = await self._build_context(alert)

        prompt = self._load_prompt_template()
        for placeholder, value in context.items():
            prompt = prompt.replace("{" + placeholder + "}", value)

        started = time.perf_counter()
        llm = get_llm_retry_service()
        result, model_used, degraded = await llm.generate_structured(
            prompt=prompt, response_class=RootCauseLLMResult
        )
        duration_ms = (time.perf_counter() - started) * 1000

        if degraded:
            # T1.1 principle: never persist fabricated forensic conclusions.
            logger.warning(
                f"RCA for alert {alert_id} refused: LLM degraded "
                f"({getattr(result, 'error_reason', 'unknown')})"
            )
            raise AIServiceUnavailableError(
                "AI provider unavailable; root cause analysis was not performed"
            )

        priority = (
            result.remediation_priority
            if result.remediation_priority in _VALID_PRIORITIES
            else "medium"
        )

        row = RootCauseAnalysis(
            alert_id=str(alert.id),
            root_cause_category=result.root_cause_category[:50],
            root_cause_subcategory=(
                result.root_cause_subcategory[:100]
                if result.root_cause_subcategory
                else None
            ),
            confidence=float(result.confidence),
            reasoning_steps={"steps": result.reasoning_steps},
            evidence_chain={"evidence": result.evidence_chain},
            verification_steps=result.verification_steps,
            suggested_remediation=result.suggested_remediation,
            remediation_priority=priority,
            ai_model=model_used,
            ai_prompt_version=_PROMPT_VERSION,
            analysis_duration_ms=round(duration_ms, 1),
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)

        logger.info(
            f"RCA completed for alert {alert_id}: category={row.root_cause_category}, "
            f"confidence={row.confidence}, model={model_used}, {duration_ms:.0f}ms"
        )
        return row

    # ------------------------------------------------------------------ #
    # Query / feedback
    # ------------------------------------------------------------------ #

    async def list_for_alert(
        self, alert_id: int, limit: int = 20
    ) -> list[RootCauseAnalysis]:
        stmt = (
            select(RootCauseAnalysis)
            .where(RootCauseAnalysis.alert_id == str(alert_id))
            .order_by(RootCauseAnalysis.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def submit_feedback(
        self, rca_id: str, payload: RootCauseFeedbackRequest
    ) -> RootCauseAnalysis:
        row = await self.session.get(RootCauseAnalysis, rca_id)
        if row is None:
            raise RootCauseAnalysisNotFoundError(rca_id)

        row.human_verified = True
        row.feedback_category = payload.verdict
        row.human_feedback = payload.comment
        row.updated_at = datetime.now(UTC).isoformat()
        await self.session.commit()
        await self.session.refresh(row)
        return row

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #

    async def _get_alert(self, alert_id: int) -> SecurityAlert:
        alert = await self.session.get(SecurityAlert, int(alert_id))
        if alert is None or alert.deleted_at is not None:
            raise RootCauseAlertNotFoundError(str(alert_id))
        return alert

    async def _build_context(self, alert: SecurityAlert) -> dict[str, str]:
        similar = await self._find_similar_alerts(alert)
        similar_lines = "\n".join(
            f"- [{s.created_at}] severity={s.severity} source={s.source} "
            f"title={s.title!r} status={s.status}"
            for s in similar
        ) or "(no similar alerts found)"

        alert_context = (
            f"Alert #{alert.id}: {alert.title}\n"
            f"Severity: {alert.severity} | Type: {alert.event_type} | "
            f"Source: {alert.source}\n"
            f"Description: {alert.description or '(none)'}\n"
            f"Source IP: {alert.source_ip or '-'} | "
            f"Destination IP: {alert.destination_ip or '-'}\n"
            f"Agent: {alert.agent_name or '-'} | Rule: {alert.rule_id or '-'} "
            f"(level {alert.rule_level or '-'})\n"
            f"MITRE: {alert.rule_mitre or '-'}\n"
            f"Full log: {alert.full_log or '(not captured)'}"
        )

        related_events = (
            f"{len(similar)} related alerts sharing rule_id/source_ip:\n{similar_lines}"
        )
        system_state = (
            f"Status: {alert.status} | Assigned to: {alert.assigned_to or 'unassigned'}\n"
            f"Detected at: {alert.created_at}\n"
            f"Resolution note: {alert.resolution_note or '(none)'}"
        )

        return {
            "alert_context": alert_context,
            "related_events": related_events,
            "system_state": system_state,
            "similar_historical_cases": similar_lines,
        }

    async def _find_similar_alerts(
        self, alert: SecurityAlert
    ) -> list[SecurityAlert]:
        conditions = [SecurityAlert.id != alert.id, SecurityAlert.deleted_at.is_(None)]
        if alert.rule_id:
            conditions.append(SecurityAlert.rule_id == alert.rule_id)
        elif alert.source_ip:
            conditions.append(SecurityAlert.source_ip == alert.source_ip)
        else:
            return []

        stmt = (
            select(SecurityAlert)
            .where(*conditions)
            .order_by(SecurityAlert.created_at.desc())
            .limit(_MAX_SIMILAR_ALERTS)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    def _load_prompt_template(self) -> str:
        # The template contains a JSON example with literal braces, so it is
        # filled via targeted replace() rather than str.format().
        return _PROMPT_PATH.read_text(encoding="utf-8")


def _to_response_dict(row: RootCauseAnalysis) -> dict[str, Any]:
    """Serialize a row for the API response model."""
    reasoning = row.reasoning_steps or {}
    evidence = row.evidence_chain or {}
    return {
        "id": row.id,
        "alert_id": row.alert_id,
        "root_cause_category": row.root_cause_category,
        "root_cause_subcategory": row.root_cause_subcategory,
        "confidence": row.confidence,
        "reasoning_steps": reasoning.get("steps", []) if isinstance(reasoning, dict) else reasoning,
        "evidence_chain": evidence.get("evidence", []) if isinstance(evidence, dict) else evidence,
        "verification_steps": row.verification_steps or [],
        "suggested_remediation": row.suggested_remediation,
        "remediation_priority": row.remediation_priority,
        "ai_model": row.ai_model,
        "analysis_duration_ms": row.analysis_duration_ms,
        "human_verified": bool(row.human_verified),
        "human_feedback": row.human_feedback,
        "feedback_category": row.feedback_category,
        "created_at": row.created_at,
    }
