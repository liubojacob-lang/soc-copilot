"""Tests for AlertCRUDService, auto-triage scoring, and triage state machine."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from models.security_alert import SecurityAlert
from schemas.alert_schema import (
    AlertCreate,
    AlertStatus,
    AlertTriageRequest,
    AlertUpdate,
)
from services.alert_crud_service import (
    ALERT_TRANSITIONS,
    AlertCRUDService,
    AutoTriageResult,
    _priority_to_label,
)


def test_priority_to_label():
    assert _priority_to_label(6) == "urgent"
    assert _priority_to_label(5) == "urgent"
    assert _priority_to_label(4) == "high"
    assert _priority_to_label(3) == "high"
    assert _priority_to_label(2) == "medium"
    assert _priority_to_label(1) == "medium"
    assert _priority_to_label(0) == "low"


def test_auto_triage_result_to_dict():
    res = AutoTriageResult(
        alert_id=10,
        severity="high",
        base_priority=4,
        asset_bonus=2,
        attack_bonus=3,
        total_priority=9,
        priority_label="urgent",
        matched_patterns=["brute_force"],
        matched_asset="srv-db-01",
        asset_criticality="high",
        suggested_status="investigating",
        reason="Matched brute force pattern on high-criticality database asset",
    )
    d = res.to_dict()
    assert d["alert_id"] == 10
    assert d["total_priority"] == 9
    assert d["priority_label"] == "urgent"
    assert "brute_force" in d["matched_patterns"]


def test_alert_transitions_map():
    assert "triaged" in ALERT_TRANSITIONS["new"]
    assert "investigating" in ALERT_TRANSITIONS["triaged"]
    assert "reopened" in ALERT_TRANSITIONS["resolved"]
    assert "triaged" in ALERT_TRANSITIONS["reopened"]


def _make_security_alert(
    alert_id=101, status="new", severity="high", title="Failed SSH Login Spike"
):
    return SecurityAlert(
        id=alert_id,
        tenant_id="default",
        external_event_id=f"ev-{alert_id}",
        source="wazuh",
        title=title,
        severity=severity,
        status=status,
        description="Multiple failed authentication attempts detected",
        event_type="auth_failure",
        tags='["ssh", "auth"]',
        iocs={"ip": ["192.168.1.50"]},
        mitre_tactics=["TA0001"],
        mitre_techniques=["T1110"],
        rule_groups="sshd,syslog",
        rule_mitre="T1110",
        source_ip="192.168.1.50",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def alert_crud_service():
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    service = AlertCRUDService(session)
    service.repo = MagicMock()
    return service


@pytest.mark.asyncio
async def test_create_alert(alert_crud_service):
    alert_obj = _make_security_alert(101)
    alert_crud_service.repo.create_alert = AsyncMock(return_value=alert_obj)

    data = AlertCreate(
        source="wazuh",
        event_type="auth_failure",
        title="Failed SSH Login Spike",
        severity="high",
        tags=["ssh", "auth"],
        iocs={"ip": ["192.168.1.50"]},
        mitre_tactics=["TA0001"],
        mitre_techniques=["T1110"],
        rule_groups=["sshd", "syslog"],
    )

    res = await alert_crud_service.create_alert(data, created_by="user-1")
    assert res.id == 101
    assert res.title == "Failed SSH Login Spike"
    alert_crud_service.repo.create_alert.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_alert(alert_crud_service):
    alert_obj = _make_security_alert(alert_id=202)
    alert_crud_service.repo.get_by_id = AsyncMock(return_value=alert_obj)

    res = await alert_crud_service.get_alert(202)
    assert res is not None
    assert res.id == 202

    alert_crud_service.repo.get_by_id = AsyncMock(return_value=None)
    res_none = await alert_crud_service.get_alert(999)
    assert res_none is None


@pytest.mark.asyncio
async def test_update_alert(alert_crud_service):
    alert_obj = _make_security_alert(alert_id=303)
    alert_crud_service.repo.get_by_id = AsyncMock(return_value=alert_obj)
    alert_crud_service.repo.update_alert = AsyncMock(return_value=alert_obj)

    update_req = AlertUpdate(title="Updated Alert Title", severity="critical")
    res = await alert_crud_service.update_alert(303, update_req, updated_by="admin-1")

    assert res.id == 303
    alert_crud_service.repo.update_alert.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_alert(alert_crud_service):
    alert_obj = _make_security_alert(alert_id=404)
    alert_crud_service.repo.get_by_id = AsyncMock(return_value=alert_obj)
    alert_crud_service.repo.delete_alert = AsyncMock(return_value=True)

    success = await alert_crud_service.delete_alert(404, deleted_by="admin-1")
    assert success is True
    alert_crud_service.repo.delete_alert.assert_awaited_once_with(404)

    # Not found case
    alert_crud_service.repo.get_by_id = AsyncMock(return_value=None)
    assert await alert_crud_service.delete_alert(999) is False


@pytest.mark.asyncio
async def test_change_status_valid_transition(alert_crud_service):
    alert_obj = _make_security_alert(alert_id=505, status="new")
    alert_crud_service.repo.get_by_id = AsyncMock(return_value=alert_obj)
    alert_crud_service.repo.update_alert = AsyncMock(return_value=alert_obj)

    req = AlertTriageRequest(
        new_status=AlertStatus.TRIAGED,
        resolution_note="Initial analyst triage complete",
    )
    res = await alert_crud_service.change_status(505, req, user_id="analyst-1")
    assert res.alert_id == 505
    assert res.old_status == "new"
    assert res.new_status == "triaged"
    assert res.changed_by == "analyst-1"
    alert_crud_service.repo.update_alert.assert_awaited()


@pytest.mark.asyncio
async def test_change_status_invalid_transition(alert_crud_service):
    alert_obj = _make_security_alert(alert_id=606, status="new")
    alert_crud_service.repo.get_by_id = AsyncMock(return_value=alert_obj)

    # new -> resolved is not allowed directly
    req = AlertTriageRequest(
        new_status=AlertStatus.RESOLVED,
        resolution_note="Jump directly to resolved",
    )
    with pytest.raises(ValueError) as exc:
        await alert_crud_service.change_status(606, req, user_id="analyst-1")
    assert "Invalid transition" in str(exc.value)

    # Same status is not allowed
    same_req = AlertTriageRequest(new_status=AlertStatus.NEW)
    with pytest.raises(ValueError) as exc:
        await alert_crud_service.change_status(606, same_req, user_id="analyst-1")
    assert "already in status" in str(exc.value)


@pytest.mark.asyncio
async def test_auto_triage_flow(alert_crud_service):
    alert_obj = _make_security_alert(
        alert_id=707,
        severity="critical",
        title="Multiple brute force attempts on root account",
    )
    alert_crud_service.repo.get_by_id = AsyncMock(return_value=alert_obj)

    # Mock DB query for asset correlation returning None
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    alert_crud_service.session.execute = AsyncMock(return_value=mock_res)

    result = await alert_crud_service.auto_triage(707)
    assert result.alert_id == 707
    assert result.severity == "critical"
    assert result.base_priority == 5
    assert result.total_priority >= 5
    assert result.priority_label == "urgent"
