"""HTTP callback notification service for playbook events."""

from datetime import UTC, datetime
from typing import Any

import httpx

from core.logger import get_logger

logger = get_logger(__name__)


class HttpCallbackService:
    """Service for sending HTTP callback notifications for playbook events."""

    def __init__(
        self,
        default_callback_url: str | None = None,
        timeout: int = 10,
        max_retries: int = 3,
    ):
        """Initialize the HTTP callback service.

        Args:
            default_callback_url: Default callback URL (can be overridden per notification)
            timeout: HTTP request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.default_callback_url = default_callback_url
        self.timeout = timeout
        self.max_retries = max_retries

    async def send_playbook_event(
        self,
        event_type: str,
        run_id: str,
        playbook_name: str,
        status: str,
        data: dict[str, Any] | None = None,
        callback_url: str | None = None,
    ) -> bool:
        """Send a playbook event notification via HTTP callback.

        Args:
            event_type: Type of event (started, completed, failed, approval_required)
            run_id: Playbook run ID
            playbook_name: Name of the playbook
            status: Current status
            data: Optional additional event data
            callback_url: Optional override callback URL

        Returns:
            True if notification sent successfully, False otherwise
        """
        url = callback_url or self.default_callback_url
        if not url:
            logger.warning("No HTTP callback URL configured")
            return False

        payload = {
            "event_type": event_type,
            "run_id": run_id,
            "playbook_name": playbook_name,
            "status": status,
            "timestamp": datetime.now(UTC).isoformat(),
            "data": data or {},
        }

        return await self._send_with_retry(url, payload)

    async def send_node_event(
        self,
        event_type: str,
        run_id: str,
        node_id: str,
        node_name: str,
        status: str,
        output: Any | None = None,
        error: str | None = None,
        callback_url: str | None = None,
    ) -> bool:
        """Send a node event notification via HTTP callback.

        Args:
            event_type: Type of event (node_started, node_completed, node_failed)
            run_id: Playbook run ID
            node_id: Node ID
            node_name: Node name
            status: Node status
            output: Optional node output
            error: Optional error message
            callback_url: Optional override callback URL

        Returns:
            True if notification sent successfully, False otherwise
        """
        url = callback_url or self.default_callback_url
        if not url:
            return False

        payload = {
            "event_type": event_type,
            "run_id": run_id,
            "node_id": node_id,
            "node_name": node_name,
            "status": status,
            "timestamp": datetime.now(UTC).isoformat(),
            "output": output,
            "error": error,
        }

        return await self._send_with_retry(url, payload)

    async def _send_with_retry(
        self,
        url: str,
        payload: dict[str, Any],
    ) -> bool:
        """Send HTTP callback with retry logic.

        Args:
            url: Callback URL
            payload: Payload to send

        Returns:
            True if sent successfully, False otherwise
        """
        import asyncio

        for attempt in range(1, self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        url,
                        json=payload,
                        headers={"Content-Type": "application/json"},
                    )

                    if response.status_code in [200, 201, 202, 204]:
                        logger.info(f"HTTP callback sent successfully to {url}")
                        return True
                    else:
                        logger.warning(
                            f"HTTP callback attempt {attempt} failed with status "
                            f"{response.status_code}: {response.text}"
                        )

            except httpx.TimeoutException:
                logger.warning(f"HTTP callback attempt {attempt} timed out")
            except Exception as e:
                logger.error(f"HTTP callback attempt {attempt} failed: {e}")

            # Don't retry on the last attempt
            if attempt < self.max_retries:
                # Exponential backoff
                backoff = 2 ** (attempt - 1)
                await asyncio.sleep(backoff)

        logger.error(f"HTTP callback failed after {self.max_retries} attempts")
        return False
