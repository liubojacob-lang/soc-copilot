"""Timeline building node plugin (v0.7.4)."""

import logging
from datetime import UTC, datetime
from typing import Any

from ..base_node import BaseNodePlugin, NodeExecutionContext

logger = logging.getLogger(__name__)


class TimelineBuildPlugin(BaseNodePlugin):
    """Build incident timeline from multiple data sources.

    Correlates events chronologically to create a unified timeline.
    """

    @property
    def node_id(self) -> str:
        return "builtin_timeline_build"

    @property
    def name(self) -> str:
        return "Timeline Builder"

    @property
    def node_type(self) -> str:
        return "action"

    @property
    def description(self) -> str:
        return "Build chronological timeline from event data"

    def validate_input(self, input_json: dict[str, Any]) -> None:
        """Validate input before execution."""
        pass

    async def execute(self, context: NodeExecutionContext) -> dict[str, Any]:
        """Execute timeline building.

        Args:
            context: Execution context

        Returns:
            Chronological timeline of events
        """
        events = context.input_json.get("events") or []
        alert = context.input_json.get("alert") or {}
        iocs = context.input_json.get("iocs") or {}

        logger.info(f"[{context.run_id}] Building timeline from {len(events)} events")

        # Build timeline from input data
        timeline = []

        # Add alert creation time as starting point
        if alert:
            timeline.append(
                {
                    "timestamp": alert.get("created_at")
                    or datetime.now(UTC).isoformat(),
                    "event_type": "alert_created",
                    "description": f"Alert '{alert.get('name', 'unknown')}' created",
                    "source": "siem",
                    "severity": alert.get("severity", "unknown"),
                }
            )

        # Add IOC extraction events
        if iocs:
            timeline.append(
                {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "event_type": "ioc_extraction",
                    "description": f"Extracted {sum(len(v) if isinstance(v, list) else 1 for v in iocs.values())} IOCs",
                    "source": "analysis",
                    "details": {
                        k: len(v) if isinstance(v, list) else 1 for k, v in iocs.items()
                    },
                }
            )

        # Sort by timestamp
        timeline.sort(key=lambda x: x.get("timestamp", ""))

        # Add sequence numbers
        for idx, event in enumerate(timeline):
            event["sequence"] = idx + 1

        return {
            "status": "success",
            "event_count": len(timeline),
            "timeline": timeline,
            "summary": {
                "earliest": timeline[0]["timestamp"] if timeline else None,
                "latest": timeline[-1]["timestamp"] if timeline else None,
                "duration_hours": self._calculate_duration(timeline),
            },
        }

    def _calculate_duration(self, timeline: list[dict[str, Any]]) -> float:
        """Calculate duration in hours between first and last event.

        Args:
            timeline: Sorted timeline events

        Returns:
            Duration in hours
        """
        if len(timeline) < 2:
            return 0

        try:
            first = datetime.fromisoformat(
                timeline[0]["timestamp"].replace("Z", "+00:00")
            )
            last = datetime.fromisoformat(
                timeline[-1]["timestamp"].replace("Z", "+00:00")
            )
            return (last - first).total_seconds() / 3600
        except (ValueError, KeyError):
            return 0
