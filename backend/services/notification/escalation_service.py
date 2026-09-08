"""v1.1: Notification escalation service for unacknowledged alerts.

This service checks for alerts that have been created more than 30 minutes ago
and are still unacknowledged, then sends escalated notifications to on-call
personnel via Slack and Feishu.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import select

from core.logger import get_logger
from db.session import AsyncSessionLocal
from models.on_call_schedule import OnCallSchedule
from services.notification_service import NotificationService

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)

# Configuration constants
ESCALATION_THRESHOLD_MINUTES = 30  # Alert unacknowledged for > 30 min
ESCALATION_CHECK_INTERVAL_SECONDS = 300  # Check every 5 minutes


class EscalationService:
    """Service for escalating unacknowledged alerts to on-call personnel.

    Uses the on_call_schedules table to find current on-call users and
    sends high-priority notifications via configured channels.
    """

    def __init__(self, session_factory=None):
        self._session_factory = session_factory or AsyncSessionLocal

    async def check_and_escalate(self) -> dict:
        """Check for unacknowledged alerts and escalate if needed.

        Returns a summary dict of actions taken.
        """

        summary = {
            "checked_at": datetime.now(UTC).isoformat(),
            "escalated": 0,
            "skipped": 0,
            "errors": 0,
            "details": [],
        }

        async with self._session_factory() as session:
            # Get current on-call users
            on_call_users = await self._get_current_on_call_users(session)
            if not on_call_users:
                logger.debug("No on-call users found for escalation check")
                summary["skipped"] = 1
                summary["details"].append("No on-call users configured")
                return summary

            # Find unacknowledged alerts older than threshold
            threshold = datetime.now(UTC) - timedelta(
                minutes=ESCALATION_THRESHOLD_MINUTES
            )

            alerts = await self._get_unacknowledged_alerts(session, threshold)

            if not alerts:
                logger.debug("No unacknowledged alerts require escalation")
                return summary

            # Send escalated notifications
            notifier = NotificationService()
            channels = ["feishu", "slack"]

            for alert in alerts:
                try:
                    alert_dict = self._alert_to_dict(alert)
                    alert_dict["escalation"] = True
                    alert_dict["on_call_users"] = on_call_users

                    await notifier.send_alert(alert_dict, channels=channels)
                    summary["escalated"] += 1
                    summary["details"].append(
                        {
                            "alert_id": alert_dict.get("id"),
                            "title": alert_dict.get("title"),
                            "on_call": on_call_users,
                        }
                    )
                    logger.info(
                        f"Escalated alert {alert_dict.get('id')} to "
                        f"on-call users: {on_call_users}"
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to escalate alert {getattr(alert, 'id', '?')}: {e}"
                    )
                    summary["errors"] += 1

        return summary

    async def _get_current_on_call_users(self, session: AsyncSession) -> list[str]:
        """Get user IDs currently on call (within their schedule window)."""
        now = datetime.now(UTC)

        result = await session.execute(
            select(OnCallSchedule)
            .where(OnCallSchedule.start_date <= now)
            .where(OnCallSchedule.end_date >= now)
            .where(OnCallSchedule.is_primary == True)
            .order_by(OnCallSchedule.start_date.desc())
        )
        schedules = result.scalars().all()

        user_ids = list(dict.fromkeys(s.user_id for s in schedules))
        logger.debug(f"Current on-call users ({now.isoformat()}): {user_ids}")
        return user_ids

    async def _get_unacknowledged_alerts(
        self, session: AsyncSession, threshold: datetime
    ) -> list:
        """Find security alerts created before threshold and not acknowledged."""
        from models.security_alert import SecurityAlert

        result = await session.execute(
            select(SecurityAlert)
            .where(SecurityAlert.created_at < threshold)
            .where(SecurityAlert.status.in_(["new", "investigating"]))
            .order_by(SecurityAlert.created_at.asc())
            .limit(50)  # Process in batches to avoid overwhelming
        )
        return list(result.scalars().all())

    @staticmethod
    def _alert_to_dict(alert) -> dict:
        """Convert a SecurityAlert ORM object to a dict for the notification service."""
        return {
            "id": getattr(alert, "id", "unknown"),
            "title": getattr(alert, "title", "Unacknowledged Alert"),
            "severity": getattr(alert, "severity", "medium"),
            "source": getattr(alert, "source", "unknown"),
            "created_at": (
                alert.created_at.isoformat()
                if hasattr(alert, "created_at") and alert.created_at
                else "unknown"
            ),
            "status": getattr(alert, "status", "unknown"),
            "description": getattr(alert, "description", ""),
        }


# Singleton instance
_escalation_service: EscalationService | None = None


def get_escalation_service() -> EscalationService:
    """Get or create the singleton escalation service instance."""
    global _escalation_service
    if _escalation_service is None:
        _escalation_service = EscalationService()
    return _escalation_service
