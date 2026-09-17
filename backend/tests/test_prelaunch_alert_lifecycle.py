"""Pre-launch regression tests for the alert lifecycle state machine.

Covers ``backend/services/alerting/alert_lifecycle.py`` — a high-risk module
changed in the v0.9.4 release batch (``_parse_alert_id`` hardening + new
``related_cases`` aggregation) that previously had ~27% coverage and no
dedicated test file.

These tests are *characterisation + contract* tests: they assert the behaviour
the API contract promises (invalid ids must not raise, status transitions must
persist, related cases must be surfaced).
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from schemas.alert_lifecycle import (
    AlertAssignment,
    AlertEscalationCreate,
    AlertResolution,
    AlertSeverity,
    AlertStatus,
)
from services.alerting.alert_lifecycle import AlertLifecycleService

# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _make_result(scalar=None, rows=None):
    """Build a stand-in for ``sqlalchemy.engine.Result``.

    ``AsyncMock(spec=AsyncSession)`` cannot model this correctly (its children
    are AsyncMocks, so ``result.scalars()`` returns a coroutine), so we build
    the result object explicitly.
    """
    result = MagicMock()
    result.scalar_one_or_none.return_value = scalar
    result.scalars.return_value = MagicMock(**{"all.return_value": rows or []})
    return result


def _make_session(*results):
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=list(results))
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


def _make_alert(
    alert_id=42,
    status="new",
    severity="high",
    assigned_to=None,
    escalated_to=None,
    escalation_reason=None,
):
    now = datetime.now(UTC)
    alert = MagicMock()
    alert.id = alert_id
    alert.status = status
    alert.severity = severity
    alert.source = "wazuh"
    alert.event_type = "bruteforce"
    alert.title = "SSH brute force"
    alert.description = "Repeated failed logins"
    alert.source_ip = "10.0.0.1"
    alert.destination_ip = "10.0.0.2"
    alert.assigned_to = assigned_to
    alert.assigned_at = None
    alert.escalated_to = escalated_to
    alert.escalated_at = now if escalated_to else None
    alert.escalation_reason = escalation_reason
    alert.resolution_note = None
    alert.root_cause = None
    alert.remediation = None
    alert.resolved_at = None
    alert.resolved_by = None
    alert.created_at = now
    alert.updated_at = now
    alert.enriched_at = None
    alert.analyzed_at = None
    return alert


def _lifecycle_results(alert, notes=None, cases=None):
    """Three execute() calls: alert lookup, notes lookup, cases lookup."""
    return (
        _make_result(scalar=alert),
        _make_result(rows=notes or []),
        _make_result(rows=cases or []),
    )


# --------------------------------------------------------------------------- #
# _parse_alert_id — new defensive helper
# --------------------------------------------------------------------------- #


class TestParseAlertId:
    """The new ``_parse_alert_id`` helper guards every lifecycle entrypoint."""

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("42", 42),
            (42, 42),
            (" 7 ", 7),  # whitespace tolerated by int()
            ("0", 0),
        ],
    )
    def test_numeric_ids_are_accepted(self, raw, expected):
        assert AlertLifecycleService._parse_alert_id(raw) == expected

    @pytest.mark.parametrize("raw", ["abc", "", None, "12.5", "0x10", [], {}])
    def test_non_numeric_ids_reject(self, raw):
        assert AlertLifecycleService._parse_alert_id(raw) is None


# --------------------------------------------------------------------------- #
# _normalize_status — legacy status mapping
# --------------------------------------------------------------------------- #


class TestNormalizeStatus:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("open", AlertStatus.NEW),
            ("new", AlertStatus.NEW),
            ("closed", AlertStatus.RESOLVED),
            ("resolved", AlertStatus.RESOLVED),
            ("false_positive", AlertStatus.FALSE_POSITIVE),
            ("investigating", AlertStatus.INVESTIGATING),
            ("escalated", AlertStatus.ESCALATED),
            ("NEW", AlertStatus.NEW),  # case-insensitive
        ],
    )
    def test_known_statuses(self, raw, expected):
        assert AlertLifecycleService._normalize_status(raw) is expected

    @pytest.mark.parametrize("raw", [None, "", "garbage", "in_progress"])
    def test_unknown_status_falls_back_to_new(self, raw):
        assert AlertLifecycleService._normalize_status(raw) is AlertStatus.NEW


# --------------------------------------------------------------------------- #
# get_alert_lifecycle
# --------------------------------------------------------------------------- #


class TestGetAlertLifecycle:
    async def test_non_numeric_id_returns_none_without_db_access(self):
        """A malformed path parameter must short-circuit, never hit the DB."""
        session = _make_session()
        service = AlertLifecycleService(session)

        assert await service.get_alert_lifecycle("not-an-id") is None
        session.execute.assert_not_called()

    async def test_missing_alert_returns_none(self):
        session = _make_session(_make_result(scalar=None))
        service = AlertLifecycleService(session)

        assert await service.get_alert_lifecycle("999") is None

    async def test_returns_lifecycle_with_related_cases(self):
        """v0.9.4: related non-deleted cases must be exposed on the response."""
        alert = _make_alert()
        case = MagicMock()
        case.id = "case-1"
        case.title = "Ransomware investigation"
        case.severity = "critical"
        case.status = "open"
        case.created_at = datetime.now(UTC)

        session = _make_session(*_lifecycle_results(alert, cases=[case]))
        service = AlertLifecycleService(session)

        resp = await service.get_alert_lifecycle("42")

        assert resp is not None
        assert resp.alert_id == "42"
        assert resp.severity == AlertSeverity.HIGH
        assert len(resp.related_cases) == 1
        assert resp.related_cases[0]["id"] == "case-1"
        assert resp.related_cases[0]["title"] == "Ransomware investigation"
        # Three queries: alert, notes, related cases
        assert session.execute.await_count == 3

    async def test_related_cases_defaults_to_empty_list(self):
        alert = _make_alert()
        session = _make_session(*_lifecycle_results(alert))
        service = AlertLifecycleService(session)

        resp = await service.get_alert_lifecycle("42")
        assert resp.related_cases == []


# --------------------------------------------------------------------------- #
# Status transitions
# --------------------------------------------------------------------------- #


class TestStatusTransitions:
    async def test_update_status_persists_and_refreshes(self):
        alert = _make_alert(status="new")
        session = _make_session(
            _make_result(scalar=alert),  # update_status lookup
            *_lifecycle_results(alert),  # follow-up get_alert_lifecycle
        )
        service = AlertLifecycleService(session)

        resp = await service.update_status("42", AlertStatus.INVESTIGATING, "u1")

        assert alert.status == "investigating"
        session.commit.assert_awaited_once()
        session.refresh.assert_awaited_once()
        assert resp.status == AlertStatus.INVESTIGATING

    async def test_update_status_invalid_id_is_noop(self):
        session = _make_session()
        service = AlertLifecycleService(session)

        assert await service.update_status("abc", AlertStatus.RESOLVED, "u1") is None
        session.execute.assert_not_called()
        session.commit.assert_not_called()

    async def test_assign_alert_sets_assignee(self):
        alert = _make_alert()
        session = _make_session(
            _make_result(scalar=alert),
            *_lifecycle_results(alert),
        )
        service = AlertLifecycleService(session)

        resp = await service.assign_alert("42", AlertAssignment(assigned_to="analyst-7"), "u1")

        assert alert.assigned_to == "analyst-7"
        assert alert.assigned_at is not None
        assert resp.assigned_to is not None
        assert resp.assigned_to.user_id == "analyst-7"

    async def test_resolve_alert_sets_resolution_fields(self):
        alert = _make_alert(status="investigating")
        session = _make_session(
            _make_result(scalar=alert),
            *_lifecycle_results(alert),
        )
        service = AlertLifecycleService(session)

        resolution = AlertResolution(
            resolution_type=AlertStatus.RESOLVED,
            resolution_note="Blocked at firewall",
            root_cause="Leaked credential",
            remediation="Rotate key",
        )
        resp = await service.resolve_alert("42", resolution, "u1")

        assert alert.status == "resolved"
        assert alert.resolved_by == "u1"
        assert alert.resolved_at is not None
        assert resp.status == AlertStatus.RESOLVED

    async def test_escalate_alert_sets_escalation_fields(self):
        alert = _make_alert(status="investigating")
        session = _make_session(
            _make_result(scalar=alert),
            *_lifecycle_results(alert),
        )
        service = AlertLifecycleService(session)

        resp = await service.escalate_alert(
            "42", AlertEscalationCreate(escalated_to="tier2", reason="Needs IR"), "u1"
        )

        assert alert.status == AlertStatus.ESCALATED.value
        assert alert.escalated_to == "tier2"
        assert alert.escalation_reason == "Needs IR"
        assert resp.escalated is not None
        assert resp.escalated.escalated_to == "tier2"

    async def test_escalate_invalid_id_is_noop(self):
        session = _make_session()
        service = AlertLifecycleService(session)
        assert (
            await service.escalate_alert(
                "nope", AlertEscalationCreate(escalated_to="tier2", reason="x"), "u1"
            )
            is None
        )


# --------------------------------------------------------------------------- #
# add_note error contract
# --------------------------------------------------------------------------- #


class TestAddNoteContract:
    async def test_add_note_raises_value_error_for_invalid_id(self):
        """Documented behaviour: add_note raises (unlike siblings returning None).

        The router guards this with a preceding ``get_alert_lifecycle`` 404, so
        it is not reachable over HTTP, but the inconsistency is intentional-to-
        document rather than accidental.
        """
        session = _make_session()
        service = AlertLifecycleService(session)

        with pytest.raises(ValueError, match="not found"):
            await service.add_note("abc", MagicMock(content="hi"), "u1", "analyst")
