"""Slack notification service for playbook events."""

from datetime import UTC, datetime
from typing import Any

import httpx

from core.logger import get_logger

logger = get_logger(__name__)


class SlackNotificationService:
    """Service for sending playbook notifications to Slack."""

    def __init__(
        self,
        webhook_url: str | None = None,
        timeout: int = 10,
    ):
        """Initialize the Slack notification service.

        Args:
            webhook_url: Default Slack webhook URL (can be overridden per notification)
            timeout: HTTP request timeout in seconds
        """
        self.webhook_url = webhook_url
        self.timeout = timeout

    async def notify_playbook_started(
        self,
        run_id: str,
        playbook_name: str,
        mode: str,
        webhook_url: str | None = None,
    ) -> bool:
        """Send notification when a playbook starts.

        Args:
            run_id: Playbook run ID
            playbook_name: Name of the playbook
            mode: Execution mode (dry_run or apply)
            webhook_url: Optional override webhook URL

        Returns:
            True if notification sent successfully, False otherwise
        """
        url = webhook_url or self.webhook_url
        if not url:
            logger.warning("No Slack webhook URL configured")
            return False

        message = {
            "text": f":rocket: Playbook Started: *{playbook_name}*",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f":rocket: Playbook Started: {playbook_name}",
                    },
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Run ID:*\n`{run_id}`",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Mode:*\n{mode}",
                        },
                        {
                            "type": "mrkdwn",
                            "text": "*Status:*\n:hourglass: Running",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Time:*\n{datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}",
                        },
                    ],
                },
            ],
        }

        return await self._send_message(url, message)

    async def notify_playbook_completed(
        self,
        run_id: str,
        playbook_name: str,
        status: str,
        duration_ms: int,
        outputs: dict[str, Any],
        webhook_url: str | None = None,
    ) -> bool:
        """Send notification when a playbook completes.

        Args:
            run_id: Playbook run ID
            playbook_name: Name of the playbook
            status: Final status (success, failed, partial)
            duration_ms: Execution duration in milliseconds
            outputs: Node outputs
            webhook_url: Optional override webhook URL

        Returns:
            True if notification sent successfully, False otherwise
        """
        url = webhook_url or self.webhook_url
        if not url:
            return False

        # Determine emoji based on status
        status_emoji = {
            "success": ":white_check_mark:",
            "failed": ":x:",
            "partial": ":warning:",
        }.get(status, ":grey_question:")

        # Format duration
        duration_sec = duration_ms / 1000
        duration_str = (
            f"{duration_sec:.2f}s" if duration_sec < 60 else f"{duration_sec/60:.1f}m"
        )

        message = {
            "text": f"{status_emoji} Playbook {status.title()}: *{playbook_name}*",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"{status_emoji} Playbook {status.title()}: {playbook_name}",
                    },
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Run ID:*\n`{run_id}`",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Duration:*\n{duration_str}",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Status:*\n{status_emoji} {status.title()}",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Nodes:*\n{len(outputs)}",
                        },
                    ],
                },
            ],
        }

        return await self._send_message(url, message)

    async def notify_approval_required(
        self,
        run_id: str,
        node_id: str,
        node_name: str,
        requested_by: str,
        expires_at: datetime | None,
        webhook_url: str | None = None,
    ) -> bool:
        """Send notification when manual approval is required.

        Args:
            run_id: Playbook run ID
            node_id: Node requiring approval
            node_name: Name of the node
            requested_by: User who initiated the run
            expires_at: Optional expiration time
            webhook_url: Optional override webhook URL

        Returns:
            True if notification sent successfully, False otherwise
        """
        url = webhook_url or self.webhook_url
        if not url:
            return False

        fields = [
            {
                "type": "mrkdwn",
                "text": f"*Run ID:*\n`{run_id}`",
            },
            {
                "type": "mrkdwn",
                "text": f"*Node:*\n{node_name}",
            },
            {
                "type": "mrkdwn",
                "text": f"*Requested By:*\n{requested_by}",
            },
        ]

        if expires_at:
            fields.append(
                {
                    "type": "mrkdwn",
                    "text": f"*Expires:*\n{expires_at.strftime('%Y-%m-%d %H:%M:%S UTC')}",
                }
            )

        message = {
            "text": f":handshake: Approval Required for *{node_name}*",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": ":handshake: Approval Required",
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"A playbook run requires your approval to continue with node *{node_name}*.",
                    },
                },
                {
                    "type": "section",
                    "fields": fields,
                },
            ],
        }

        return await self._send_message(url, message)

    async def notify_run_failed(
        self,
        run_id: str,
        playbook_name: str,
        status: str,
        error_message: str | None = None,
        failed_nodes: list | None = None,
        webhook_url: str | None = None,
    ) -> bool:
        """Send notification when a playbook run fails.

        Args:
            run_id: Playbook run ID
            playbook_name: Name of the playbook
            status: Final failure status (failed, cancelled, timeout)
            error_message: Optional error message
            failed_nodes: Optional list of failed node IDs
            webhook_url: Optional override webhook URL

        Returns:
            True if notification sent successfully, False otherwise
        """
        import os

        url = webhook_url or self.webhook_url or os.getenv("SLACK_WEBHOOK_DEFAULT")
        if not url:
            logger.debug("No Slack webhook URL configured for failure alert")
            return False

        # Check if failure alerts are enabled
        enabled = os.getenv("ENABLE_RUN_FAILURE_NOTIFY", "false").lower() in (
            "true",
            "1",
            "yes",
        )
        if not enabled:
            logger.debug("Run failure notifications are disabled")
            return False

        # Determine emoji based on status
        status_emoji = {
            "failed": ":x:",
            "cancelled": ":no_entry_sign:",
            "timeout": ":alarm_clock:",
        }.get(status, ":warning:")

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{status_emoji} Run Failure Alert",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{playbook_name}* run has *{status}*",
                },
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Run ID:*\n`{run_id}`",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Status:*\n{status_emoji} {status.title()}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Time:*\n{datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}",
                    },
                ],
            },
        ]

        # Add error message if provided
        if error_message:
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Error:*\n```{error_message[:500]}```",
                    },
                }
            )

        # Add failed nodes if provided
        if failed_nodes:
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Failed Nodes:*\n{', '.join(f"`{n}`" for n in failed_nodes[:10])}"
                        + (
                            f" and {len(failed_nodes) - 10} more..."
                            if len(failed_nodes) > 10
                            else ""
                        ),
                    },
                }
            )

        # Add footer
        blocks.append(
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "SOC Copilot v0.7.2 | Automated Failure Alert",
                    },
                ],
            }
        )

        message = {
            "text": f"{status_emoji} Run Failure: {playbook_name} ({status})",
            "blocks": blocks,
        }

        return await self._send_message(url, message)

    async def _send_message(
        self,
        webhook_url: str,
        message: dict[str, Any],
    ) -> bool:
        """Send a message to Slack webhook.

        Args:
            webhook_url: Slack webhook URL
            message: Message payload

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    webhook_url,
                    json=message,
                )

                if response.status_code == 200:
                    logger.info("Slack notification sent successfully")
                    return True
                else:
                    logger.error(
                        f"Slack notification failed with status {response.status_code}: "
                        f"{response.text}"
                    )
                    return False

        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return False
