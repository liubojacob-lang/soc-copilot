"""Slack notification node plugin (v0.7.4)."""

from typing import Any, Dict
from datetime import datetime, timezone
import logging

import httpx

from ..base_node import BaseNodePlugin, NodeExecutionContext

logger = logging.getLogger(__name__)


class SlackNotifyPlugin(BaseNodePlugin):
    """Slack webhook notification node.

    This node sends formatted notifications to Slack via webhook URLs.
    Supports rich formatting with Slack blocks and template variables.
    """

    @property
    def node_id(self) -> str:
        return "builtin_slack_notify"

    @property
    def name(self) -> str:
        return "Slack Notification"

    @property
    def node_type(self) -> str:
        return "action"

    @property
    def description(self) -> str:
        return "Send notifications to Slack via webhook"

    def validate_input(self, input_json: Dict[str, Any]) -> None:
        """Validate input before execution."""
        webhook_url = input_json.get("webhook_url")
        message = input_json.get("message")

        if not webhook_url and not input_json.get("use_secret"):
            raise ValueError("webhook_url is required unless use_secret=True")

        if not message:
            raise ValueError("message is required")

    async def execute(self, context: NodeExecutionContext) -> Dict[str, Any]:
        """Send Slack notification.

        Args:
            context: Execution context

        Returns:
            Notification result
        """
        webhook_url = context.input_json.get("webhook_url")
        use_secret = context.input_json.get("use_secret", False)
        secret_name = context.input_json.get("secret_name", "SLACK_WEBHOOK")

        # Get webhook URL from secret if configured
        if use_secret:
            webhook_url = context.secrets.get(secret_name, webhook_url)

        if not webhook_url:
            logger.warning(f"[{context.run_id}] No Slack webhook URL configured")
            return {
                "status": "skipped",
                "message": "No webhook URL configured",
            }

        # Build message
        message_template = context.input_json.get("message", "Playbook run {{run_id}} completed")
        message = self._resolve_template(message_template, context)

        # Get optional fields
        title = context.input_json.get("title", "SOC Copilot Notification")
        color = context.input_json.get("color", "#36a64f")  # Default green
        include_fields = context.input_json.get("include_fields", [])

        # Build Slack payload
        payload = self._build_slack_payload(
            title=title,
            message=message,
            color=color,
            run_id=context.run_id,
            node_name=context.node_name,
            include_fields=include_fields,
            context=context,
        )

        logger.info(f"[{context.run_id}] Sending Slack notification to {webhook_url[:50]}...")

        # Send webhook
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )

                if response.status_code in (200, 204):
                    logger.info(f"[{context.run_id}] Slack notification sent successfully")
                    return {
                        "status": "success",
                        "message": "Notification sent",
                    }
                else:
                    error_msg = f"Slack webhook returned {response.status_code}: {response.text}"
                    logger.error(f"[{context.run_id}] {error_msg}")
                    # Don't fail the run - notification is non-critical
                    return {
                        "status": "success",
                        "message": f"Notification failed but continuing: {error_msg}",
                        "notification_failed": True,
                    }

        except Exception as e:
            logger.error(f"[{context.run_id}] Slack notification error: {e}")
            # Don't fail the run - notification is non-critical
            return {
                "status": "success",
                "message": f"Notification error but continuing: {str(e)}",
                "notification_failed": True,
            }

    def _resolve_template(self, template: str, context: NodeExecutionContext) -> str:
        """Resolve template variables in message.

        Supports: {{run_id}}, {{node_name}}, {{input.xxx}}, {{context.xxx}}
        """
        result = template
        result = result.replace("{{run_id}}", context.run_id[:20] + "...")
        result = result.replace("{{node_name}}", context.node_name)

        # Replace input variables
        for key, value in context.input_json.items():
            placeholder = f"{{{{input.{key}}}}}"
            if placeholder in result:
                result = result.replace(placeholder, str(value))

        # Replace context variables
        for key, value in context.context.items():
            placeholder = f"{{{{context.{key}}}}}"
            if placeholder in result:
                result = result.replace(placeholder, str(value))

        return result

    def _build_slack_payload(
        self,
        title: str,
        message: str,
        color: str,
        run_id: str,
        node_name: str,
        include_fields: list[str],
        context: NodeExecutionContext,
    ) -> Dict[str, Any]:
        """Build Slack attachment payload.

        Args:
            title: Attachment title
            message: Main message text
            color: Sidebar color
            run_id: Playbook run ID
            node_name: Node name
            include_fields: Fields to include from output
            context: Execution context

        Returns:
            Slack webhook payload
        """
        fields = [
            {
                "title": "Run ID",
                "value": f"`{run_id[:20]}...`",
                "short": True,
            },
            {
                "title": "Node",
                "value": node_name,
                "short": True,
            },
        ]

        # Add requested fields
        for field in include_fields:
            if field in context.input_json:
                value = str(context.input_json[field])
                if len(value) > 50:
                    value = value[:50] + "..."
                fields.append({
                    "title": field.replace("_", " ").title(),
                    "value": value,
                    "short": True,
                })

        attachment = {
            "color": color,
            "title": title,
            "text": message,
            "fields": fields[:6],  # Slack limit
            "footer": f"SOC Copilot v0.7.4",
            "ts": int(datetime.now(timezone.utc).timestamp()),
        }

        return {"attachments": [attachment]}
