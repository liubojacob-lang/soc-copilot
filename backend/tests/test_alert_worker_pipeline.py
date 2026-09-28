"""Tests for AlertWorker pipeline and notification rendering."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.notifications.templates import render_alert_template
from workers.alert_worker import AlertWorker


def test_render_alert_template_standard():
    alert = {
        "id": "alert-123",
        "title": "SQL Injection Detected",
        "source": "waf",
        "severity": "high",
        "event_type": "attack",
        "created_at": "2026-09-21T12:00:00Z",
        "description": "Exploit payload in user-agent header",
    }
    title, body, severity = render_alert_template(alert)

    assert title == "[WAF] SQL Injection Detected"
    assert "Alert ID: alert-123" in body
    assert "Severity: HIGH" in body
    assert "Event: attack" in body
    assert "Description: Exploit payload in user-agent header" in body
    assert severity == "high"


def test_render_alert_template_missing_fields():
    alert = {}
    title, body, severity = render_alert_template(alert)

    assert title == "[SOC] Security Alert"
    assert "Alert ID: N/A" in body
    assert "Severity: MEDIUM" in body
    assert "Event: N/A" in body
    assert severity == "medium"


@pytest.mark.asyncio
async def test_alert_worker_process_message_success():
    with patch("workers.alert_worker.get_message_queue_manager") as mock_get_mq, patch(
        "workers.alert_worker.get_notification_service"
    ) as mock_get_notif:

        mock_mq = MagicMock()
        mock_mq.acknowledge_async = AsyncMock(return_value=True)
        mock_get_mq.return_value = mock_mq

        mock_notif = MagicMock()
        mock_notif.send_alert = AsyncMock(return_value={"slack": True, "feishu": True})
        mock_get_notif.return_value = mock_notif

        worker = AlertWorker(worker_id="test-worker")
        message = {
            "message_id": "msg-001",
            "stream": "events:critical",
            "alert": {"id": "alt-001", "title": "Test Alert", "severity": "critical"},
            "severity": "critical",
        }

        await worker._process_message(message)

        mock_notif.send_alert.assert_awaited_once_with(message["alert"])
        mock_mq.acknowledge_async.assert_awaited_once_with("events:critical", "msg-001")


@pytest.mark.asyncio
async def test_alert_worker_process_message_no_notifications():
    with patch("workers.alert_worker.get_message_queue_manager") as mock_get_mq, patch(
        "workers.alert_worker.get_notification_service"
    ) as mock_get_notif:

        mock_mq = MagicMock()
        mock_mq.acknowledge_async = AsyncMock(return_value=True)
        mock_get_mq.return_value = mock_mq

        mock_notif = MagicMock()
        mock_notif.send_alert = AsyncMock(return_value={})
        mock_get_notif.return_value = mock_notif

        worker = AlertWorker(worker_id="test-worker")
        message = {
            "message_id": "msg-002",
            "stream": "events:medium",
            "alert": {"id": "alt-002"},
            "severity": "medium",
        }

        await worker._process_message(message)

        mock_notif.send_alert.assert_awaited_once_with(message["alert"])
        mock_mq.acknowledge_async.assert_awaited_once_with("events:medium", "msg-002")


@pytest.mark.asyncio
async def test_alert_worker_process_message_exception():
    with patch("workers.alert_worker.get_message_queue_manager") as mock_get_mq, patch(
        "workers.alert_worker.get_notification_service"
    ) as mock_get_notif:

        mock_mq = MagicMock()
        mock_mq.acknowledge_async = AsyncMock(return_value=True)
        mock_get_mq.return_value = mock_mq

        mock_notif = MagicMock()
        mock_notif.send_alert = AsyncMock(
            side_effect=RuntimeError("Channel unreachable")
        )
        mock_get_notif.return_value = mock_notif

        worker = AlertWorker(worker_id="test-worker")
        message = {
            "message_id": "msg-003",
            "stream": "events:high",
            "alert": {"id": "alt-003"},
            "severity": "high",
        }

        # Should not raise uncaught exception
        await worker._process_message(message)

        # Should not acknowledge on failure
        mock_mq.acknowledge_async.assert_not_awaited()


def test_alert_worker_signal_handler():
    with patch("workers.alert_worker.get_message_queue_manager"), patch(
        "workers.alert_worker.get_notification_service"
    ):
        worker = AlertWorker(worker_id="test-worker")
        assert not worker.shutdown_requested
        worker._signal_handler(15, None)
        assert worker.shutdown_requested
