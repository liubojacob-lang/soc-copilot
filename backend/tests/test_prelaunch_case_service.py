"""Pre-launch regression tests for case creation / alert linking.

``backend/services/case_service.py`` is at ~14% coverage and gained a new
"link initial alerts on case creation" feature in the v0.9.4 batch, plus
``str | int`` coercion on ``CaseCreate.alert_ids`` and ``CaseAlertLink.alert_ids``.
This file pins down the coercion semantics so a later refactor cannot silently
drop or corrupt alert associations.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from schemas.case import CaseAlertLink, CaseCreate, CaseSeverity, CaseStatus
from services.case_service import CaseService

# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _make_service():
    session = AsyncMock()
    session.commit = AsyncMock()
    service = CaseService(session)
    service.repo = MagicMock()
    service.repo.create = AsyncMock(return_value=_make_case())
    service.repo.add_timeline_entry = AsyncMock()
    service.repo.link_alerts = AsyncMock(return_value=2)
    service.repo.get_by_id = AsyncMock(return_value=_make_case())
    service._to_detail = AsyncMock(return_value="detail")
    return service


def _make_case(case_id="case-1"):
    case = MagicMock()
    case.id = case_id
    case.title = "T"
    case.description = None
    case.severity = "high"
    case.status = "new"
    case.assigned_to = None
    case.sla_due_at = None
    case.resolution = None
    case.resolved_at = None
    case.closed_at = None
    case.tenant_id = None
    case.created_at = datetime.now(UTC)
    case.updated_at = datetime.now(UTC)
    case.alerts = []
    case.timeline_entries = []
    case.comments = []
    return case


def _result(rows):
    res = MagicMock()
    res.scalars.return_value = MagicMock(**{"all.return_value": rows})
    return res


def _create_payload(alert_ids):
    return CaseCreate(
        title="Ransomware triage",
        severity=CaseSeverity.high,
        status=CaseStatus.new,
        alert_ids=alert_ids,
    )


# --------------------------------------------------------------------------- #
# Schema-level coercion acceptance
# --------------------------------------------------------------------------- #


class TestAlertIdSchemas:
    def test_case_create_accepts_mixed_str_and_int(self):
        payload = CaseCreate(title="t", alert_ids=["7", 8, "abc"])
        assert payload.alert_ids == ["7", 8, "abc"]

    def test_case_alert_link_accepts_strings(self):
        link = CaseAlertLink(alert_ids=["1", 2])
        assert link.alert_ids == ["1", 2]

    def test_case_alert_link_still_requires_at_least_one(self):
        with pytest.raises(Exception):
            CaseAlertLink(alert_ids=[])


# --------------------------------------------------------------------------- #
# create() — initial alert linking
# --------------------------------------------------------------------------- #


class TestCreateLinksInitialAlerts:
    async def test_valid_string_ids_are_coerced_and_linked(self):
        service = _make_service()
        service.session.execute = AsyncMock(return_value=_result([7, 8]))

        await service.create(_create_payload(["7", 8]), user_id="u1")

        service.repo.link_alerts.assert_awaited_once()
        kwargs = service.repo.link_alerts.await_args.kwargs
        assert kwargs["alert_ids"] == [7, 8]
        assert kwargs["case_id"] == "case-1"
        assert kwargs["added_by"] == "u1"

    async def test_non_numeric_ids_are_silently_dropped(self):
        """DEFECT QA-006 (documented): invalid ids vanish without any signal."""
        service = _make_service()
        service.session.execute = AsyncMock(return_value=_result([7]))

        await service.create(_create_payload(["7", "not-an-id", "??"]), user_id="u1")

        service.repo.link_alerts.assert_awaited_once()
        assert service.repo.link_alerts.await_args.kwargs["alert_ids"] == [7]

    async def test_all_invalid_ids_skip_linking_entirely(self):
        service = _make_service()
        service.session.execute = AsyncMock(return_value=_result([]))

        await service.create(_create_payload(["nope", "??"]), user_id="u1")

        service.repo.link_alerts.assert_not_called()

    async def test_ids_missing_from_db_are_filtered_out(self):
        service = _make_service()
        # DB only knows about id 7, the caller also asked for 999
        service.session.execute = AsyncMock(return_value=_result([7]))

        await service.create(_create_payload([7, 999]), user_id="u1")

        assert service.repo.link_alerts.await_args.kwargs["alert_ids"] == [7]

    async def test_no_alert_ids_does_not_query_alerts(self):
        service = _make_service()
        service.session.execute = AsyncMock(return_value=_result([]))

        await service.create(_create_payload(None), user_id="u1")

        service.session.execute.assert_not_called()
        service.repo.link_alerts.assert_not_called()
        service.session.commit.assert_awaited_once()

    async def test_timeline_entry_records_linked_alerts(self):
        service = _make_service()
        service.session.execute = AsyncMock(return_value=_result([7, 8]))

        await service.create(_create_payload(["7", "8"]), user_id="u1")

        summaries = [
            c.kwargs["summary"] for c in service.repo.add_timeline_entry.await_args_list
        ]
        assert any("Linked 2 alert(s) on case creation" in s for s in summaries)


# --------------------------------------------------------------------------- #
# link_alerts() — post-creation linking
# --------------------------------------------------------------------------- #


class TestLinkAlerts:
    def _service(self):
        service = _make_service()
        service.repo.get_by_id_simple = AsyncMock(return_value=_make_case())
        return service

    async def test_string_ids_coerced_to_int(self):
        service = self._service()
        service.repo.link_alerts = AsyncMock(return_value=2)

        await service.link_alerts("case-1", CaseAlertLink(alert_ids=["11", 12]), user_id="u1")

        assert service.repo.link_alerts.await_args.kwargs["alert_ids"] == [11, 12]

    async def test_all_invalid_ids_call_repo_with_empty_list(self):
        """DEFECT QA-006: empty list reaches the repository instead of a 400."""
        service = self._service()
        service.repo.link_alerts = AsyncMock(return_value=0)

        await service.link_alerts("case-1", CaseAlertLink(alert_ids=["x"]), user_id="u1")

        assert service.repo.link_alerts.await_args.kwargs["alert_ids"] == []

    async def test_missing_case_raises(self):
        service = self._service()
        service.repo.get_by_id_simple = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="Case not found"):
            await service.link_alerts(
                "missing", CaseAlertLink(alert_ids=[1]), user_id="u1"
            )
