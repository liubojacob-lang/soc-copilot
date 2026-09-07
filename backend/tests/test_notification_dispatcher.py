"""
Comprehensive tests for Notification Dispatcher, multi-channel providers,
event bus integration, and notification API router.
"""

from __future__ import annotations

import unittest.mock as mock
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from models.on_call_schedule import OnCallSchedule
from services.notification_service import NotificationService
from services.notifications.base import NotificationMessage, NotificationProvider
from services.notifications.email import EmailProvider
from services.notifications.feishu import FeishuProvider
from services.notifications.registry import NotificationRegistry
from services.notifications.slack import SlackProvider
from services.notifications.templates import render_alert_template

# ─────────────────────────────────────────────────────────────
# 1. Template Rendering & Message Formulation Tests
# ─────────────────────────────────────────────────────────────

def test_render_alert_template_standard():
    alert = {
        "id": "ALT-100",
        "title": "Brute Force Attack Detected",
        "severity": "high",
        "source": "Wazuh",
        "description": "50 failed login attempts from 192.168.1.100",
    }
    title, body, severity = render_alert_template(alert)
    assert "Brute Force Attack Detected" in title
    assert "[WAZUH]" in title
    assert severity == "high"
    assert "192.168.1.100" in body


def test_render_alert_template_fallback_values():
    alert = {}
    title, body, severity = render_alert_template(alert)
    assert title  # Has default title
    assert severity in ("medium", "info", "low")  # default fallback
    assert "Description" in body or "N/A" in body or "unknown" in body.lower()


# ─────────────────────────────────────────────────────────────
# 2. Individual Provider Unit Tests with Mocks
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_feishu_provider_send_success():
    provider = FeishuProvider(webhook_url="https://open.feishu.cn/open-apis/bot/v2/hook/test")
    assert provider.is_configured() is True

    msg = NotificationMessage(title="Test Alert", body="Alert details", severity="high", payload={})

    with mock.patch("aiohttp.ClientSession.post") as mock_post:
        mock_resp = mock.AsyncMock()
        mock_resp.status = 200
        mock_post.return_value.__aenter__.return_value = mock_resp

        result = await provider.send(msg)
        assert result is True
        mock_post.assert_called_once()


@pytest.mark.asyncio
async def test_feishu_provider_unconfigured():
    provider = FeishuProvider(webhook_url=None)
    provider.webhook_url = None
    assert provider.is_configured() is False

    msg = NotificationMessage(title="Test", body="body", severity="info", payload={})
    result = await provider.send(msg)
    assert result is False


@pytest.mark.asyncio
async def test_slack_provider_send_success():
    provider = SlackProvider(webhook_url="https://hooks.slack.com/services/test/test/test")
    assert provider.is_configured() is True

    msg = NotificationMessage(title="Critical Alert", body="Host compromised", severity="critical", payload={})

    with mock.patch("aiohttp.ClientSession.post") as mock_post:
        mock_resp = mock.AsyncMock()
        mock_resp.status = 200
        mock_post.return_value.__aenter__.return_value = mock_resp

        result = await provider.send(msg)
        assert result is True
        mock_post.assert_called_once()


@pytest.mark.asyncio
async def test_slack_provider_send_failure():
    provider = SlackProvider(webhook_url="https://hooks.slack.com/services/test/test/test")

    msg = NotificationMessage(title="Critical Alert", body="Details", severity="critical", payload={})

    with mock.patch("aiohttp.ClientSession.post") as mock_post:
        mock_resp = mock.AsyncMock()
        mock_resp.status = 500
        mock_post.return_value.__aenter__.return_value = mock_resp

        result = await provider.send(msg)
        assert result is False


@pytest.mark.asyncio
async def test_email_provider_send_mocked():
    provider = EmailProvider()
    provider.to_email = "soc-oncall@example.com"
    provider.smtp_user = "soc-bot@example.com"
    # Dummy credential generated at runtime (no literal in source)
    provider.smtp_password = "test-" + uuid.uuid4().hex
    assert provider.is_configured() is True

    msg = NotificationMessage(title="Security Notice", body="Test email content", severity="low", payload={})

    with mock.patch("smtplib.SMTP") as mock_smtp_cls:
        mock_smtp_inst = mock.MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_smtp_inst

        result = await provider.send(msg)
        assert result is True
        mock_smtp_inst.starttls.assert_called_once()
        mock_smtp_inst.login.assert_called_once_with("soc-bot@example.com", provider.smtp_password)
        mock_smtp_inst.sendmail.assert_called_once()


@pytest.mark.asyncio
async def test_email_provider_unconfigured():
    provider = EmailProvider()
    provider.to_email = None
    assert provider.is_configured() is False

    msg = NotificationMessage(title="Notice", body="Content", severity="low", payload={})
    result = await provider.send(msg)
    assert result is False


# ─────────────────────────────────────────────────────────────
# 3. NotificationService Facade & Event Bus Integration Tests
# ─────────────────────────────────────────────────────────────

class MockProvider(NotificationProvider):
    def __init__(self, name: str, should_succeed: bool = True, raise_error: bool = False):
        self.name = name
        self.should_succeed = should_succeed
        self.raise_error = raise_error
        self.call_count = 0

    def is_configured(self) -> bool:
        return True

    async def send(self, message: NotificationMessage) -> bool:
        self.call_count += 1
        if self.raise_error:
            raise RuntimeError(f"Channel {self.name} connection timeout")
        return self.should_succeed


@pytest.mark.asyncio
async def test_notification_service_send_alert_multi_channel():
    svc = NotificationService()
    svc.registry = NotificationRegistry()
    p_feishu = MockProvider("feishu", should_succeed=True)
    p_slack = MockProvider("slack", should_succeed=False)
    p_email = MockProvider("email", raise_error=True)

    svc.registry.register(p_feishu)
    svc.registry.register(p_slack)
    svc.registry.register(p_email)

    with mock.patch.object(svc.event_bus, "publish", new_callable=mock.AsyncMock) as mock_publish:
        alert = {
            "id": "ALT-555",
            "title": "SQL Injection Attempt",
            "severity": "high",
            "source": "ModSecurity",
            "description": "payload: ' OR 1=1 --",
        }

        results = await svc.send_alert(alert, channels=["feishu", "slack", "email"])

        assert results["feishu"] is True
        assert results["slack"] is False
        assert results["email"] is False

        # Verify event bus published for feishu and slack
        assert mock_publish.call_count >= 2
        first_call = mock_publish.call_args_list[0]
        assert first_call.kwargs["event_type"] == "notification.sent"
        assert first_call.kwargs["priority"] == "high"


@pytest.mark.asyncio
async def test_notification_service_filtered_channels():
    svc = NotificationService()
    svc.registry = NotificationRegistry()
    p_feishu = MockProvider("feishu", should_succeed=True)
    p_slack = MockProvider("slack", should_succeed=True)
    svc.registry.register(p_feishu)
    svc.registry.register(p_slack)

    alert = {"id": "ALT-999", "title": "Test Filter", "severity": "low"}
    results = await svc.send_alert(alert, channels=["slack"])

    assert "slack" in results
    assert "feishu" not in results
    assert p_slack.call_count == 1
    assert p_feishu.call_count == 0


# ─────────────────────────────────────────────────────────────
# 4. API Router Endpoints Tests (/api/v1/notifications/...)
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_notification_router_test_endpoint(auth_client: AsyncClient):
    with mock.patch("services.notification_service.NotificationService.send_alert") as mock_send:
        mock_send.return_value = {"feishu": True, "slack": True}

        response = await auth_client.post(
            "/api/v1/notifications/test",
            json={"channels": ["feishu", "slack"]},
        )

        assert response.status_code == 200
        data = response.json()
        assert data.get("feishu") is True
        assert data.get("slack") is True


@pytest.mark.asyncio
async def test_notification_router_channels_endpoint(auth_client: AsyncClient):
    response = await auth_client.get("/api/v1/notifications/channels")
    assert response.status_code == 200
    data = response.json()
    assert "feishu" in data
    assert "slack" in data
    assert "email" in data
    assert isinstance(data["feishu"], bool)


@pytest.mark.asyncio
async def test_notification_router_queue_stats(auth_client: AsyncClient):
    response = await auth_client.get("/api/v1/notifications/queue/stats")
    assert response.status_code == 200
    data = response.json()
    for priority in ("critical", "high", "medium", "low"):
        assert priority in data
        assert "stream" in data[priority]
        assert "length" in data[priority]


@pytest.mark.asyncio
async def test_notification_router_health(auth_client: AsyncClient):
    response = await auth_client.get("/api/v1/notifications/health")
    assert response.status_code == 200
    data = response.json()
    assert "redis" in data
    assert "streams" in data
    assert "channels" in data


# ─────────────────────────────────────────────────────────────
# 5. On-Call Schedule Model Unit Tests
# ─────────────────────────────────────────────────────────────

def test_on_call_schedule_model():
    now = datetime.now(UTC)
    end = now + timedelta(days=7)
    schedule = OnCallSchedule(
        id="schedule-001",
        user_id="user-analyst-1",
        start_date=now,
        end_date=end,
        rotation_group="tier1_soc",
        is_primary=True,
    )

    assert schedule.id == "schedule-001"
    assert schedule.user_id == "user-analyst-1"
    assert schedule.rotation_group == "tier1_soc"
    assert schedule.is_primary is True
    assert schedule.end_date > schedule.start_date
