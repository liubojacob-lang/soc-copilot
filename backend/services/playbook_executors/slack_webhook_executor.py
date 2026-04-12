"""Slack Webhook notification node executor."""

import os
from datetime import UTC
from typing import Any

import httpx

from core.logger import get_logger

from .executor_base import BaseExecutor, ExecutorContext

logger = get_logger(__name__)


class SlackWebhookExecutor(BaseExecutor):
    """Executor for sending Slack webhook notifications."""

    async def execute(self, context: ExecutorContext) -> dict[str, Any]:
        """Send notification to Slack via webhook.

        Args:
            context: Execution context with node definition and inputs

        Returns:
            Output dictionary with notification result
        """
        config = context.node_def.get("config", {})

        # Get webhook URL - support environment variable reference
        webhook_url = config.get("webhook_url", "")
        if webhook_url.startswith("${") and webhook_url.endswith("}"):
            env_var = webhook_url[2:-1]
            webhook_url = os.getenv(env_var, "")

        # Fallback to default if no URL specified
        if not webhook_url:
            webhook_url = os.getenv("SLACK_WEBHOOK_DEFAULT", "")

        if not webhook_url:
            logger.warning(f"[{context.run_id}] No Slack webhook URL configured")
            return {
                "status": "skipped",
                "message": "No webhook URL configured",
            }

        # Build message with template variables
        message_template = config.get(
            "message_template", "Playbook run {{run_id}} status: {{status}}"
        )
        message = self._resolve_template(message_template, context)

        # Get fields to include from output
        include_fields = config.get("include_output_fields", [])
        include_output = {}
        if include_fields:
            for field in include_fields:
                if field in context.input_json:
                    include_output[field] = context.input_json[field]

        # Build Slack blocks payload
        blocks = self._build_slack_blocks(
            message=message,
            run_id=context.run_id,
            node_id=context.node_id,
            include_output=include_output,
        )

        payload = {
            "blocks": blocks,
            "text": message,  # Fallback text
        }

        # Send webhook
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )

                if response.status_code in (200, 204):
                    logger.info(
                        f"[{context.run_id}] Slack notification sent successfully"
                    )
                    return {
                        "status": "success",
                        "message": "Notification sent",
                    }
                else:
                    logger.error(
                        f"[{context.run_id}] Slack notification failed: "
                        f"{response.status_code} {response.text}"
                    )
                    # Don't fail the run - notification failure is non-critical
                    return {
                        "status": "success",  # Return success to not fail the run
                        "message": f"Notification failed but continuing: {response.status_code}",
                        "notification_failed": True,
                    }

        except Exception as e:
            logger.error(f"[{context.run_id}] Slack notification error: {e}")
            # Don't fail the run - notification failure is non-critical
            return {
                "status": "success",
                "message": f"Notification error but continuing: {e!s}",
                "notification_failed": True,
            }

    def _build_slack_blocks(
        self,
        message: str,
        run_id: str,
        node_id: str,
        include_output: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Build Slack blocks format payload.

        Args:
            message: Main message text
            run_id: Playbook run ID
            node_id: Node ID
            include_output: Optional output fields to include

        Returns:
            List of Slack blocks
        """
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🔔 SOC Copilot Notification",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message,
                },
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Run ID:*\n`{run_id[:20]}...`",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Node ID:*\n`{node_id}`",
                    },
                ],
            },
        ]

        # Add output fields if specified
        if include_output:
            fields = []
            for key, value in include_output.items():
                value_str = str(value)
                if len(value_str) > 100:
                    value_str = value_str[:100] + "..."
                fields.append(
                    {
                        "type": "mrkdwn",
                        "text": f"*{key}:*\n{value_str}",
                    }
                )

            if fields:
                blocks.append(
                    {
                        "type": "section",
                        "fields": fields[:4],  # Slack max 4 fields per section
                    }
                )

        # Add footer with timestamp
        from datetime import datetime

        blocks.append(
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Sent at {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')} | SOC Copilot v0.7.2",
                    },
                ],
            }
        )

        return blocks
