"""
Archive old data from the database.
Archives alerts, audit logs, and history older than specified days.
"""

import argparse
import asyncio
from datetime import datetime, timedelta

from sqlalchemy import and_, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from db.session import AsyncSessionLocal
from models.audit_log import AuditLog
from models.history import History
from models.security_alert import SecurityAlert

logger = get_logger(__name__)


class DataArchiver:
    """
    Archives old data from the database.
    """

    def __init__(
        self,
        session: AsyncSession,
        archive_days_alerts: int = 90,
        archive_days_history: int = 30,
        archive_days_audit: int = 180,
    ):
        self.session = session
        self.archive_days_alerts = archive_days_alerts
        self.archive_days_history = archive_days_history
        self.archive_days_audit = archive_days_audit

    async def archive_alerts(self) -> int:
        cutoff_date = datetime.utcnow() - timedelta(days=self.archive_days_alerts)

        count_query = select(func.count(SecurityAlert.id)).where(
            and_(
                SecurityAlert.created_at < cutoff_date,
                SecurityAlert.status.in_(["resolved", "false_positive", "closed"]),
            )
        )

        count_result = await self.session.execute(count_query)
        total_count = count_result.scalar() or 0

        if total_count == 0:
            logger.info("No old alerts to archive")
            return 0

        logger.info(f"Found {total_count} old alerts to archive")

        delete_query = delete(SecurityAlert).where(
            and_(
                SecurityAlert.created_at < cutoff_date,
                SecurityAlert.status.in_(["resolved", "false_positive", "closed"]),
            )
        )

        result = await self.session.execute(delete_query)
        await self.session.commit()

        archived_count = result.rowcount
        logger.info(f"Archived {archived_count} alerts")

        return archived_count

    async def archive_history(self) -> int:
        cutoff_date = datetime.utcnow() - timedelta(days=self.archive_days_history)

        count_query = select(func.count(History.id)).where(
            History.created_at < cutoff_date
        )

        count_result = await self.session.execute(count_query)
        total_count = count_result.scalar() or 0

        if total_count == 0:
            logger.info("No old history records to archive")
            return 0

        logger.info(f"Found {total_count} old history records to archive")

        delete_query = delete(History).where(History.created_at < cutoff_date)

        result = await self.session.execute(delete_query)
        await self.session.commit()

        archived_count = result.rowcount
        logger.info(f"Archived {archived_count} history records")

        return archived_count

    async def archive_audit_logs(self) -> int:
        cutoff_date = datetime.utcnow() - timedelta(days=self.archive_days_audit)

        count_query = select(func.count(AuditLog.id)).where(
            AuditLog.created_at < cutoff_date
        )

        count_result = await self.session.execute(count_query)
        total_count = count_result.scalar() or 0

        if total_count == 0:
            logger.info("No old audit logs to archive")
            return 0

        logger.info(f"Found {total_count} old audit logs to archive")

        delete_query = delete(AuditLog).where(AuditLog.created_at < cutoff_date)

        result = await self.session.execute(delete_query)
        await self.session.commit()

        archived_count = result.rowcount
        logger.info(f"Archived {archived_count} audit logs")

        return archived_count

    async def archive_all(self) -> dict[str, int]:
        results = {}
        logger.info("Starting data archival...")
        results["alerts"] = await self.archive_alerts()
        results["history"] = await self.archive_history()
        results["audit_logs"] = await self.archive_audit_logs()
        total = sum(results.values())
        logger.info(f"Data archival complete. Total archived: {total} records")
        return results


async def main():
    parser = argparse.ArgumentParser(
        description="Archive old data from SOC Copilot database"
    )
    parser.add_argument(
        "--alerts-days",
        type=int,
        default=90,
        help="Archive alerts older than this many days",
    )
    parser.add_argument(
        "--history-days",
        type=int,
        default=30,
        help="Archive history older than this many days",
    )
    parser.add_argument(
        "--audit-days",
        type=int,
        default=180,
        help="Archive audit logs older than this many days",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be archived without deleting",
    )

    args = parser.parse_args()

    async with AsyncSessionLocal() as session:
        archiver = DataArchiver(
            session=session,
            archive_days_alerts=args.alerts_days,
            archive_days_history=args.history_days,
            archive_days_audit=args.audit_days,
        )

        if args.dry_run:
            logger.info("Dry run mode - no data will be deleted")
        else:
            results = await archiver.archive_all()
            print("\nArchival Results:")
            print(f"  Alerts: {results['alerts']}")
            print(f"  History: {results['history']}")
            print(f"  Audit Logs: {results['audit_logs']}")
            print(f"  Total: {sum(results.values())}")


if __name__ == "__main__":
    asyncio.run(main())
