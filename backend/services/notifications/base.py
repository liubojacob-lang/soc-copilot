"""Notification provider abstractions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class NotificationMessage:
    title: str
    body: str
    severity: str
    payload: dict[str, Any]


class NotificationProvider(ABC):
    """Plugin contract for all notification channels."""

    name: str

    @abstractmethod
    def is_configured(self) -> bool:
        """Whether provider has required credentials/config."""

    @abstractmethod
    async def send(self, message: NotificationMessage) -> bool:
        """Send notification."""
