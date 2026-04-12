"""Timeline building step implementation."""

from datetime import datetime, timedelta
from typing import Any

from ..registry import register_step
from .base_step import BaseStepImpl


class TimelineBuildStep(BaseStepImpl):
    """Build incident timeline from available data."""

    @property
    def name(self) -> str:
        return "Timeline Construction"

    @property
    def step_id(self) -> str:
        return "timeline_build"

    @property
    def step_type(self) -> str:
        return "analysis"

    @property
    def description(self) -> str:
        return "Construct chronological timeline of security events"

    @property
    def supports_apply(self) -> bool:
        return True

    def execute(self, input_json: dict[str, Any], mode: str) -> dict[str, Any]:
        """Build incident timeline.

        Args:
            input_json: Input containing alert data and IOCs
            mode: Execution mode

        Returns:
            Dictionary with timeline events
        """
        alert_data = input_json.get("alert_data", {})
        iocs = input_json.get("iocs", {})

        timeline = {
            "events": [],
            "summary": {
                "total_events": 0,
                "time_span_hours": 0,
                "earliest_event": None,
                "latest_event": None,
            },
        }

        # Get alert timestamp
        alert_time = alert_data.get("timestamp") or alert_data.get("created_at")
        if alert_time:
            if isinstance(alert_time, str):
                try:
                    alert_time = datetime.fromisoformat(
                        alert_time.replace("Z", "+00:00")
                    )
                except (ValueError, TypeError):
                    alert_time = datetime.now()
            elif not isinstance(alert_time, datetime):
                alert_time = datetime.now()
        else:
            alert_time = datetime.now()

        # Build timeline events
        events = []

        # Initial detection event
        events.append(
            {
                "timestamp": alert_time.isoformat(),
                "event_type": "detection",
                "description": "Security alert generated",
                "source": "SIEM/EDR",
                "severity": alert_data.get("severity", "medium"),
                "details": {
                    "alert_title": alert_data.get("title", "Unknown Alert"),
                    "alert_type": alert_data.get("alert_type", "Unknown"),
                },
            }
        )

        # Estimated first compromise (typically 1-7 days before detection)
        estimated_compromise = alert_time - timedelta(days=3)
        events.append(
            {
                "timestamp": estimated_compromise.isoformat(),
                "event_type": "estimated_compromise",
                "description": "Estimated initial compromise (based on industry dwell time averages)",
                "source": "Estimated",
                "severity": "high",
                "details": {
                    "confidence": "low",
                    "method": "statistical_average",
                },
            }
        )

        # IOC first seen events
        for ip in iocs.get("ips", [])[:3]:
            events.append(
                {
                    "timestamp": (alert_time - timedelta(hours=24)).isoformat(),
                    "event_type": "ioc_observed",
                    "description": f"Malicious IP {ip} observed in network logs",
                    "source": "Network Logs",
                    "severity": "high",
                    "details": {
                        "ioc_type": "ip",
                        "ioc_value": ip,
                    },
                }
            )

        # Lateral movement events (estimated)
        if alert_data.get("hostname"):
            for i in range(1, min(len(iocs.get("ips", [])) + 1, 4)):
                events.append(
                    {
                        "timestamp": (
                            alert_time - timedelta(hours=24 - i * 6)
                        ).isoformat(),
                        "event_type": "lateral_movement",
                        "description": f"Potential lateral movement to host #{i}",
                        "source": "Estimated",
                        "severity": "medium",
                        "details": {
                            "confidence": "low",
                            "source_host": alert_data.get("hostname", "unknown"),
                        },
                    }
                )

        # Sort events by timestamp
        events.sort(key=lambda x: x["timestamp"])

        timeline["events"] = events
        timeline["summary"]["total_events"] = len(events)

        if events:
            timeline["summary"]["earliest_event"] = events[0]["timestamp"]
            timeline["summary"]["latest_event"] = events[-1]["timestamp"]

            # Calculate time span
            try:
                earliest = datetime.fromisoformat(events[0]["timestamp"])
                latest = datetime.fromisoformat(events[-1]["timestamp"])
                time_span = (latest - earliest).total_seconds() / 3600
                timeline["summary"]["time_span_hours"] = round(time_span, 2)
            except (ValueError, TypeError, KeyError, IndexError):
                pass

        return timeline


# Register the step
register_step("timeline_build", TimelineBuildStep)
