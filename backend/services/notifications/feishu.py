"""Feishu notification provider."""

from __future__ import annotations

import os

import aiohttp
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .base import NotificationMessage, NotificationProvider


class FeishuProvider(NotificationProvider):
    name = "feishu"

    def __init__(self, webhook_url: str | None = None):
        self.webhook_url = webhook_url or os.getenv("FEISHU_WEBHOOK_URL")

    def is_configured(self) -> bool:
        return bool(self.webhook_url)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        retry=retry_if_exception_type((aiohttp.ClientError, TimeoutError)),
        reraise=True,
    )
    async def send(self, message: NotificationMessage) -> bool:
        if not self.webhook_url:
            return False
        payload = {
            "msg_type": "text",
            "content": {"text": f"{message.title}\n{message.body}"},
        }
        timeout = aiohttp.ClientTimeout(total=8)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(self.webhook_url, json=payload) as resp:
                return 200 <= resp.status < 300
