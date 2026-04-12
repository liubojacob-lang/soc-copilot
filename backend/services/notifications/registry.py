"""Notification provider registry with dynamic plugin registration."""

from __future__ import annotations

from collections.abc import Iterable

from .base import NotificationProvider


class NotificationRegistry:
    def __init__(self):
        self._providers: dict[str, NotificationProvider] = {}

    def register(self, provider: NotificationProvider) -> None:
        self._providers[provider.name] = provider

    def get(self, name: str) -> NotificationProvider | None:
        return self._providers.get(name)

    def configured(self) -> dict[str, NotificationProvider]:
        return {name: p for name, p in self._providers.items() if p.is_configured()}

    def all_names(self) -> list[str]:
        return list(self._providers.keys())

    def iter_selected(
        self, channels: list[str] | None
    ) -> Iterable[NotificationProvider]:
        providers = self.configured()
        if not channels:
            return providers.values()
        return [providers[c] for c in channels if c in providers]
