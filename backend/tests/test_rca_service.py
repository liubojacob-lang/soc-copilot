"""Tests for the root cause analysis service (T2.4 minimal closed loop).

Covers the three contract points that matter:

1. A successful LLM analysis is persisted with the model metadata.
2. A degraded LLM result is REFUSED — nothing is persisted (T1.1 principle:
   fabricated forensic conclusions are worse than no conclusion).
3. Analyst feedback closes the human-verification loop.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from schemas.root_cause import RootCauseFeedbackRequest, RootCauseLLMResult
from services.rca_service import (
    AIServiceUnavailableError,
    RootCauseAlertNotFoundError,
    RootCauseAnalysisNotFoundError,
    RootCauseAnalysisService,
)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _make_alert(alert_id=42, **overrides):
    alert = MagicMock()
    alert.id = alert_id
    alert.deleted_at = None
    alert.title = "SSH brute force from 203.0.113.7"
    alert.severity = "high"
    alert.event_type = "bruteforce"
    alert.source = "wazuh"
    alert.description = "Multiple failed logins"
    alert.source_ip = "203.0.113.7"
    alert.destination_ip = "10.0.0.5"
    alert.agent_name = "web-01"
    alert.rule_id = "5710"
    alert.rule_level = 8
    alert.rule_mitre = "T1110"
    alert.full_log = "sshd: Failed password for root"
    alert.status = "new"
    alert.assigned_to = None
    alert.created_at = "2026-09-19T00:00:00Z"
    alert.resolution_note = None
    for key, value in overrides.items():
        setattr(alert, key, value)
    return alert


def _make_llm_result(**overrides):
    defaults = dict(
        root_cause_category="attack",
        root_cause_subcategory="ssh brute force",
        confidence=0.87,
        reasoning_steps=[{"step": 1, "description": "Gather facts", "findings": ["8 failed logins"]}],
        evidence_chain=[{"evidence": "auth.log shows failures", "supports": "attack", "strength": "strong"}],
        verification_steps=["grep 'Failed password' /var/log/auth.log"],
        suggested_remediation="Block 203.0.113.7 at the firewall and enforce key auth",
        remediation_priority="high",
    )
    defaults.update(overrides)
    return RootCauseLLMResult(**defaults)


def _make_session(alert="default", rca_row=None):
    session = AsyncMock()
    if alert == "default":
        alert = _make_alert()

    async def _get(model, key):
        if model.__name__ == "SecurityAlert":
            if alert is None:
                return None
            return alert if key == alert.id else None
        if model.__name__ == "RootCauseAnalysis":
            return rca_row
        return None

    session.get = AsyncMock(side_effect=_get)
    session.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))))
    session.add = MagicMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture
def llm_ok(monkeypatch):
    stub = MagicMock()
    stub.generate_structured = AsyncMock(return_value=(_make_llm_result(), "glm-4-test", False))
    monkeypatch.setattr("services.rca_service.get_llm_retry_service", lambda: stub)
    return stub


@pytest.fixture
def llm_degraded(monkeypatch):
    degraded_result = MagicMock()
    degraded_result.error_reason = "provider down"
    stub = MagicMock()
    stub.generate_structured = AsyncMock(return_value=(degraded_result, "zhipu", True))
    monkeypatch.setattr("services.rca_service.get_llm_retry_service", lambda: stub)
    return stub


# --------------------------------------------------------------------------- #
# Analysis
# --------------------------------------------------------------------------- #


class TestAnalyze:
    async def test_persists_successful_analysis(self, llm_ok):
        alert = _make_alert()
        session = _make_session(alert=alert)

        row = await RootCauseAnalysisService(session).analyze(alert.id)

        assert row.alert_id == "42"
        assert row.root_cause_category == "attack"
        assert row.confidence == 0.87
        assert row.ai_model == "glm-4-test"
        assert row.remediation_priority == "high"
        assert row.analysis_duration_ms is not None
        session.add.assert_called_once()
        session.commit.assert_awaited_once()
        # The prompt sent to the LLM was built from the CoT template with
        # real alert context, not an empty skeleton.
        prompt = llm_ok.generate_structured.call_args.kwargs["prompt"]
        assert "SSH brute force" in prompt
        assert "203.0.113.7" in prompt
        assert "{alert_context}" not in prompt

    async def test_degraded_llm_is_refused_and_nothing_persisted(self, llm_degraded):
        session = _make_session(alert=_make_alert())

        with pytest.raises(AIServiceUnavailableError):
            await RootCauseAnalysisService(session).analyze(42)

        session.add.assert_not_called()
        assert session.commit.await_count == 0

    async def test_unknown_alert_raises(self, llm_ok):
        session = _make_session(alert=None)

        with pytest.raises(RootCauseAlertNotFoundError):
            await RootCauseAnalysisService(session).analyze(999)

    async def test_soft_deleted_alert_raises(self, llm_ok):
        alert = _make_alert(deleted_at="2026-09-01T00:00:00Z")
        session = _make_session(alert=alert)

        with pytest.raises(RootCauseAlertNotFoundError):
            await RootCauseAnalysisService(session).analyze(alert.id)

    async def test_invalid_priority_falls_back_to_medium(self, monkeypatch):
        stub = MagicMock()
        stub.generate_structured = AsyncMock(
            return_value=(_make_llm_result(remediation_priority="urgent!!"), "glm", False)
        )
        monkeypatch.setattr("services.rca_service.get_llm_retry_service", lambda: stub)
        session = _make_session(alert=_make_alert())

        row = await RootCauseAnalysisService(session).analyze(42)
        assert row.remediation_priority == "medium"


# --------------------------------------------------------------------------- #
# Feedback loop
# --------------------------------------------------------------------------- #


class TestFeedback:
    async def test_feedback_updates_record(self):
        rca = MagicMock(spec=["id", "human_verified", "feedback_category", "human_feedback", "updated_at"])
        session = _make_session(rca_row=rca)

        row = await RootCauseAnalysisService(session).submit_feedback(
            "rca-1",
            RootCauseFeedbackRequest(verdict="accurate", comment="matched auth.log"),
        )

        assert row.human_verified is True
        assert row.feedback_category == "accurate"
        assert row.human_feedback == "matched auth.log"
        assert row.updated_at is not None
        session.commit.assert_awaited_once()

    async def test_feedback_on_missing_record_raises(self):
        session = _make_session(rca_row=None)

        with pytest.raises(RootCauseAnalysisNotFoundError):
            await RootCauseAnalysisService(session).submit_feedback(
                "missing", RootCauseFeedbackRequest(verdict="inaccurate")
            )
