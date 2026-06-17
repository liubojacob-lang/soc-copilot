"""
Alert Deduplication and Aggregation Service
Provides smart deduplication and aggregation of security alerts
to reduce alert fatigue.
"""

import hashlib
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from models.security_alert import SecurityAlert

logger = get_logger(__name__)


class AlertDeduplicator:
    """
    Smart alert deduplicator using fingerprinting techniques.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    def generate_fingerprint(
        self, alert: dict[str, Any], method: str = "balanced"
    ) -> str:
        """
        Generate a unique fingerprint for an alert based on its characteristics.

        Args:
            alert: Alert data dictionary
            method: Fingerprinting method (strict, balanced, relaxed)

        Returns:
            Hexadecimal fingerprint string
        """
        fingerprint_components = []

        if method == "strict":
            fingerprint_components = [
                alert.get("source", ""),
                alert.get("event_type", ""),
                alert.get("source_ip", ""),
                alert.get("destination_ip", ""),
                alert.get("rule_id", ""),
                alert.get("agent_name", ""),
            ]
        elif method == "balanced":
            fingerprint_components = [
                alert.get("source", ""),
                alert.get("event_type", ""),
                alert.get("source_ip", ""),
                alert.get("rule_id", ""),
            ]
        elif method == "relaxed":
            fingerprint_components = [
                alert.get("event_type", ""),
                alert.get("source_ip", ""),
            ]
        else:
            fingerprint_components = [
                alert.get("source", ""),
                alert.get("event_type", ""),
                alert.get("source_ip", ""),
            ]

        fingerprint_string = "|".join(str(comp) for comp in fingerprint_components)
        return hashlib.sha256(fingerprint_string.encode()).hexdigest()

    async def find_duplicate(
        self,
        alert: dict[str, Any],
        time_window_hours: int = 1,
        fingerprint_method: str = "balanced",
    ) -> SecurityAlert | None:
        """
        Find a duplicate alert within the specified time window.

        Args:
            alert: New alert data
            time_window_hours: Lookback time window in hours
            fingerprint_method: Fingerprinting method to use

        Returns:
            Existing duplicate alert or None
        """
        fingerprint = self.generate_fingerprint(alert, fingerprint_method)
        cutoff_time = datetime.now(datetime.UTC) - timedelta(hours=time_window_hours)

        query = select(SecurityAlert).where(
            and_(
                SecurityAlert.fingerprint == fingerprint,
                SecurityAlert.created_at >= cutoff_time,
                SecurityAlert.source == alert.get("source"),
            )
        )

        result = await self.session.execute(query)
        return result.scalar_one_or_none()


class AlertAggregator:
    """
    Alert aggregator to group similar alerts and reduce noise.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def aggregate_alerts(
        self, new_alert: SecurityAlert, time_window_hours: int = 1
    ) -> tuple[SecurityAlert, bool]:
        """
        Aggregate a new alert with similar existing alerts.

        Args:
            new_alert: The new alert to aggregate
            time_window_hours: Lookback time window for aggregation

        Returns:
            Tuple of (aggregated_alert, is_new_alert)
        """
        cutoff_time = datetime.now(datetime.UTC) - timedelta(hours=time_window_hours)

        query = select(SecurityAlert).where(
            and_(
                SecurityAlert.source == new_alert.source,
                SecurityAlert.event_type == new_alert.event_type,
                or_(
                    SecurityAlert.source_ip == new_alert.source_ip,
                    SecurityAlert.agent_name == new_alert.agent_name,
                ),
                SecurityAlert.created_at >= cutoff_time,
                SecurityAlert.status != "closed",
                SecurityAlert.status != "false_positive",
            )
        )

        result = await self.session.execute(query)
        existing_alerts = result.scalars().all()

        if existing_alerts:
            primary_alert = max(existing_alerts, key=lambda a: a.created_at)
            await self._update_aggregated_alert(primary_alert, new_alert)
            return primary_alert, False

        return new_alert, True

    async def _update_aggregated_alert(
        self, primary_alert: SecurityAlert, new_alert: SecurityAlert
    ) -> None:
        """
        Update the primary aggregated alert with information from the new alert.

        Args:
            primary_alert: The main alert to update
            new_alert: The new alert contributing to the aggregation
        """
        if not primary_alert.aggregated_count:
            primary_alert.aggregated_count = 1

        primary_alert.aggregated_count += 1
        primary_alert.last_seen_at = datetime.now(datetime.UTC)

        severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}
        new_severity_level = severity_order.get(new_alert.severity, 0)
        current_severity_level = severity_order.get(primary_alert.severity, 0)

        if new_severity_level > current_severity_level:
            primary_alert.severity = new_alert.severity
            primary_alert.escalation_reason = (
                "Escalated due to higher severity alert aggregation"
            )

        if primary_alert.threat_score and new_alert.threat_score:
            primary_alert.threat_score = max(
                primary_alert.threat_score, new_alert.threat_score
            )
        elif new_alert.threat_score:
            primary_alert.threat_score = new_alert.threat_score

        await self.session.commit()


class AlertStormSuppressor:
    """
    Alert storm suppression to prevent flooding during mass events.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.thresholds = {
            "critical": 10,
            "high": 20,
            "medium": 50,
            "low": 100,
            "info": 200,
        }
        self.suppression_window_minutes = 15

    async def check_alert_storm(
        self, source: str, severity: str, time_window_minutes: int = 5
    ) -> tuple[bool, int]:
        """
        Check if we're experiencing an alert storm from a source.

        Args:
            source: Alert source
            severity: Alert severity
            time_window_minutes: Time window to check

        Returns:
            Tuple of (is_storm, alert_count)
        """
        cutoff_time = datetime.now(datetime.UTC) - timedelta(minutes=time_window_minutes)

        query = select(func.count(SecurityAlert.id)).where(
            and_(
                SecurityAlert.source == source,
                SecurityAlert.severity == severity.lower(),
                SecurityAlert.created_at >= cutoff_time,
            )
        )

        result = await self.session.execute(query)
        count = result.scalar() or 0

        threshold = self.thresholds.get(severity.lower(), 50)
        is_storm = count >= threshold

        if is_storm:
            logger.warning(
                f"Alert storm detected! Source={source}, Severity={severity}, "
                f"Count={count}, Threshold={threshold}"
            )

        return is_storm, count

    async def get_suppressed_sources(self) -> list[dict[str, Any]]:
        """
        Get list of currently suppressed sources.

        Returns:
            List of suppressed source information
        """
        cutoff_time = datetime.now(datetime.UTC) - timedelta(
            minutes=self.suppression_window_minutes
        )

        query = (
            select(
                SecurityAlert.source,
                SecurityAlert.severity,
                func.count(SecurityAlert.id).label("count"),
            )
            .where(SecurityAlert.created_at >= cutoff_time)
            .group_by(SecurityAlert.source, SecurityAlert.severity)
            .having(func.count(SecurityAlert.id) >= 10)
        )

        result = await self.session.execute(query)
        suppressed = []

        for row in result.all():
            source, severity, count = row
            threshold = self.thresholds.get(severity.lower(), 50)
            if count >= threshold:
                suppressed.append(
                    {
                        "source": source,
                        "severity": severity,
                        "count": count,
                        "threshold": threshold,
                        "suppressed_until": (
                            datetime.now(datetime.UTC)
                            + timedelta(minutes=self.suppression_window_minutes)
                        ).isoformat(),
                    }
                )

        return suppressed


def get_alert_deduplicator(session: AsyncSession) -> AlertDeduplicator:
    """Factory function to get AlertDeduplicator instance."""
    return AlertDeduplicator(session)


def get_alert_aggregator(session: AsyncSession) -> AlertAggregator:
    """Factory function to get AlertAggregator instance."""
    return AlertAggregator(session)


def get_alert_storm_suppressor(session: AsyncSession) -> AlertStormSuppressor:
    """Factory function to get AlertStormSuppressor instance."""
    return AlertStormSuppressor(session)
