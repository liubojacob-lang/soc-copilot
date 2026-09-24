"""State machine and business logic tests for CaseService."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from schemas.case import (
    CaseAssign,
    CaseSeverity,
    CaseStatus,
    CaseStatusUpdate,
    CaseUpdate,
    CommentCreate,
)
from services.case_service import CaseService


def _make_case_mock(case_id="case-100", status="new", severity="high"):
    case = MagicMock()
    case.id = case_id
    case.title = "Incident Alpha"
    case.description = "Initial description"
    case.severity = severity
    case.status = status
    case.assigned_to = None
    case.sla_due_at = None
    case.resolution = None
    case.resolved_at = None
    case.closed_at = None
    case.tenant_id = "default"
    case.created_at = datetime.now(UTC)
    case.updated_at = datetime.now(UTC)
    case.alerts = []
    case.timeline_entries = []
    case.comments = []
    case.assignee = None
    return case


@pytest.fixture
def case_service():
    session = AsyncMock()
    session.commit = AsyncMock()
    service = CaseService(session)
    service.repo = MagicMock()
    service.repo.get_case_alerts = AsyncMock(return_value=[])
    service.repo.count_alerts = AsyncMock(return_value=0)
    service.repo.count_comments = AsyncMock(return_value=0)
    service.repo.add_timeline_entry = AsyncMock()
    service.repo.update = AsyncMock()
    return service


@pytest.mark.asyncio
async def test_update_status_allowed_transitions(case_service):
    # 1. new -> investigating
    case = _make_case_mock(status="new")
    case_service.repo.get_by_id_simple = AsyncMock(return_value=case)
    case_service.repo.update = AsyncMock(return_value=case)
    case_service.repo.get_by_id = AsyncMock(return_value=case)

    res = await case_service.update_status(
        "case-100",
        CaseStatusUpdate(status=CaseStatus.investigating),
        user_id="user-1",
    )
    assert res is not None
    case_service.repo.update.assert_awaited()
    case_service.repo.add_timeline_entry.assert_awaited()

    # 2. investigating -> resolved
    case.status = "investigating"
    res = await case_service.update_status(
        "case-100",
        CaseStatusUpdate(
            status=CaseStatus.resolved, resolution="Root cause eliminated"
        ),
        user_id="user-1",
    )
    assert res is not None

    # 3. resolved -> closed
    case.status = "resolved"
    res = await case_service.update_status(
        "case-100",
        CaseStatusUpdate(status=CaseStatus.closed),
        user_id="user-1",
    )
    assert res is not None


@pytest.mark.asyncio
async def test_update_status_disallowed_transitions(case_service):
    # closed -> investigating is disallowed
    case = _make_case_mock(status="closed")
    case_service.repo.get_by_id_simple = AsyncMock(return_value=case)

    with pytest.raises(ValueError) as exc:
        await case_service.update_status(
            "case-100",
            CaseStatusUpdate(status=CaseStatus.investigating),
        )
    assert "Invalid status transition" in str(exc.value)

    # new -> pending_review is disallowed (must be investigating first)
    case.status = "new"
    with pytest.raises(ValueError) as exc:
        await case_service.update_status(
            "case-100",
            CaseStatusUpdate(status=CaseStatus.pending_review),
        )
    assert "Invalid status transition" in str(exc.value)


@pytest.mark.asyncio
async def test_update_status_case_not_found(case_service):
    case_service.repo.get_by_id_simple = AsyncMock(return_value=None)
    with pytest.raises(ValueError) as exc:
        await case_service.update_status(
            "nonexistent",
            CaseStatusUpdate(status=CaseStatus.investigating),
        )
    assert "Case not found" in str(exc.value)


@pytest.mark.asyncio
async def test_assign_case(case_service):
    case = _make_case_mock(case_id="case-200")
    case_service.repo.get_by_id_simple = AsyncMock(return_value=case)
    case_service.repo.update = AsyncMock(return_value=case)
    case_service.repo.get_by_id = AsyncMock(return_value=case)

    res = await case_service.assign(
        "case-200",
        CaseAssign(assigned_to="analyst-bob"),
        user_id="lead-alice",
    )
    assert res is not None
    case_service.repo.update.assert_awaited_with(
        case_service.session, case, assigned_to="analyst-bob"
    )
    case_service.repo.add_timeline_entry.assert_awaited()


@pytest.mark.asyncio
async def test_update_case_fields_and_timeline(case_service):
    case = _make_case_mock(case_id="case-300", severity="low")
    case_service.repo.get_by_id_simple = AsyncMock(return_value=case)
    case_service.repo.update = AsyncMock(return_value=case)
    case_service.repo.get_by_id = AsyncMock(return_value=case)

    update_data = CaseUpdate(title="Updated Title", severity=CaseSeverity.critical)
    res = await case_service.update("case-300", update_data, user_id="admin-1")

    assert res is not None
    case_service.repo.update.assert_awaited()
    case_service.repo.add_timeline_entry.assert_awaited()


@pytest.mark.asyncio
async def test_delete_case(case_service):
    case = _make_case_mock(case_id="case-400")
    case_service.repo.get_by_id_simple = AsyncMock(return_value=case)
    case_service.repo.delete = AsyncMock()

    await case_service.delete("case-400")
    case_service.repo.delete.assert_awaited_once_with(case_service.session, case)
    case_service.session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_comments_flow(case_service):
    case = _make_case_mock(case_id="case-500")
    case_service.repo.get_by_id_simple = AsyncMock(return_value=case)

    mock_comment = MagicMock()
    mock_comment.id = "cmt-1"
    mock_comment.case_id = "case-500"
    mock_comment.user_id = "u-1"
    mock_comment.username = "alice"
    mock_comment.content = "Forensic analysis completed."
    mock_comment.created_at = datetime.now(UTC)
    mock_comment.updated_at = datetime.now(UTC)

    case_service.repo.add_comment = AsyncMock(return_value=mock_comment)
    case_service.repo.get_comments = AsyncMock(return_value=[mock_comment])

    comment_res = await case_service.add_comment(
        "case-500",
        CommentCreate(content="Forensic analysis completed."),
        user_id="u-1",
        username="alice",
    )
    assert comment_res.id == "cmt-1"
    assert comment_res.content == "Forensic analysis completed."
    case_service.repo.add_timeline_entry.assert_awaited()

    comments_list = await case_service.repo.get_comments(
        case_service.session, "case-500"
    )
    assert len(comments_list) == 1
    assert comments_list[0].id == "cmt-1"


@pytest.mark.asyncio
async def test_unlink_alert(case_service):
    case = _make_case_mock(case_id="case-600")
    case_service.repo.get_by_id_simple = AsyncMock(return_value=case)
    case_service.repo.unlink_alert = AsyncMock(return_value=True)
    case_service.repo.get_by_id = AsyncMock(return_value=case)

    unlinked = await case_service.unlink_alert("case-600", 12345, user_id="analyst-1")
    assert unlinked is not None
    case_service.repo.add_timeline_entry.assert_awaited()


@pytest.mark.asyncio
async def test_get_stats(case_service):
    mock_stats = {
        "total": 42,
        "by_status": {"open": 10, "investigating": 12, "resolved": 15, "closed": 5},
        "by_severity": {"critical": 2, "high": 10, "medium": 20, "low": 10},
        "open_cases": 22,
        "overdue_cases": 1,
        "resolved_today": 3,
        "avg_resolution_hours": 4.5,
    }
    case_service.repo.get_stats = AsyncMock(return_value=mock_stats)

    stats = await case_service.get_stats()
    assert stats.total == 42
    assert stats.by_status["open"] == 10
    assert stats.open_cases == 22
    assert stats.overdue_cases == 1
