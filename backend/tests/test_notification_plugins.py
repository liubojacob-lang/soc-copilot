"""Unit tests for notification plugin architecture."""

from __future__ import annotations

import pytest

from services.notification_service import NotificationService
from services.notifications.base import NotificationMessage, NotificationProvider


class DummyProvider(NotificationProvider):
    name = "dummy"

    def __init__(self):
        self.calls = 0

    def is_configured(self) -> bool:
        return True

    async def send(self, message: NotificationMessage) -> bool:
        self.calls += 1
        return True


@pytest.mark.asyncio
async def test_dynamic_provider_registration() -> None:
    svc = NotificationService()
    dummy = DummyProvider()
    svc.register_provider(dummy)

    results = await svc.send_alert(
        {"id": "1", "source": "test", "title": "x", "severity": "low"},
        channels=["dummy"],
    )

    assert results["dummy"] is True
    assert dummy.calls == 1
