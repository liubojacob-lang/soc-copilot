"""Audit log archive service for SOC compliance.

v0.8.5: Audit log archiving and cleanup service.
- Archives old audit logs to compressed JSON files
- Supports configurable retention periods
- Provides data export for compliance audits
- Integrates with background task scheduler
"""

import asyncio
import gzip
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from core.config import settings
from core.logger import get_logger
from models.audit_log import AuditLogModel

logger = get_logger(__name__)


class AuditArchiveService:
    """Service for archiving and cleaning up audit logs.

    Features:
    - Archive old logs to compressed JSON files
    - Configurable retention periods
    - Automatic cleanup of archived files
    - Export functionality for compliance audits
    """

    def __init__(
        self,
        session_factory: async_sessionmaker,
        archive_dir: Path | None = None,
        retention_days: int | None = None,
        archive_retention_days: int = 365,
    ):
        self.session_factory = session_factory
        self.archive_dir = (
            archive_dir or Path(__file__).parent.parent / "data" / "audit_archives"
        )
        self.retention_days = retention_days or settings.audit_log_retention_days
        self.archive_retention_days = archive_retention_days
        self._ensure_archive_dir()

    def _ensure_archive_dir(self):
        """Ensure archive directory exists."""
        self.archive_dir.mkdir(parents=True, exist_ok=True)

    def _get_archive_filename(self, date: datetime) -> Path:
        """Get archive filename for a specific date."""
        return self.archive_dir / f"audit_logs_{date.strftime('%Y-%m-%d')}.json.gz"

    async def archive_old_logs(
        self,
        days: int | None = None,
        batch_size: int = 1000,
    ) -> dict:
        """Archive audit logs older than specified days.

        Args:
            days: Archive logs older than this many days (default: from settings)
            batch_size: Number of records to process per batch

        Returns:
            Dict with archive statistics
        """
        days = days if days is not None else self.retention_days
        cutoff = datetime.now(UTC) - timedelta(days=days)
        cutoff_str = cutoff.isoformat()

        stats = {
            "archived_count": 0,
            "files_created": 0,
            "errors": [],
            "start_time": datetime.now().isoformat(),
            "end_time": None,
        }

        logger.info(f"Starting audit log archival (cutoff: {cutoff_str})")

        try:
            async with self.session_factory() as session:
                # Get logs grouped by date
                result = await session.execute(
                    select(
                        func.date(AuditLogModel.created_at).label("log_date"),
                        func.count(AuditLogModel.id).label("count"),
                    )
                    .where(AuditLogModel.created_at < cutoff)
                    .group_by(func.date(AuditLogModel.created_at))
                    .order_by(func.date(AuditLogModel.created_at))
                )

                date_groups = result.all()

                for date_group in date_groups:
                    log_date = date_group[0]
                    date_group[1]

                    try:
                        # Archive logs for this date
                        archived = await self._archive_logs_by_date(
                            session, log_date, batch_size
                        )
                        stats["archived_count"] += archived
                        stats["files_created"] += 1

                        logger.info(f"Archived {archived} logs for {log_date}")

                    except Exception as e:
                        error_msg = f"Failed to archive logs for {log_date}: {e}"
                        logger.error(error_msg)
                        stats["errors"].append(error_msg)

                await session.commit()

        except Exception as e:
            error_msg = f"Archive process failed: {e}"
            logger.error(error_msg)
            stats["errors"].append(error_msg)

        stats["end_time"] = datetime.now().isoformat()

        logger.info(
            f"Archive completed: {stats['archived_count']} logs archived, "
            f"{stats['files_created']} files created, "
            f"{len(stats['errors'])} errors"
        )

        return stats

    async def _archive_logs_by_date(
        self,
        session: AsyncSession,
        log_date: str,
        batch_size: int,
    ) -> int:
        """Archive logs for a specific date to a compressed file.

        Args:
            session: Database session
            log_date: Date string (YYYY-MM-DD)
            batch_size: Number of records per batch

        Returns:
            Number of logs archived
        """
        # Fetch all logs for this date
        offset = 0
        all_logs = []

        while True:
            result = await session.execute(
                select(AuditLogModel)
                .where(func.date(AuditLogModel.created_at) == log_date)
                .order_by(AuditLogModel.created_at)
                .offset(offset)
                .limit(batch_size)
            )
            logs = result.scalars().all()

            if not logs:
                break

            for log in logs:
                created_at_val = (
                    log.created_at.isoformat()
                    if hasattr(log.created_at, "isoformat")
                    else str(log.created_at)
                )
                all_logs.append(
                    {
                        "id": log.id,
                        "user_id": log.user_id,
                        "action": log.action,
                        "method": log.method,
                        "path": log.path,
                        "status_code": log.status_code,
                        "target_type": log.target_type,
                        "target_id": log.target_id,
                        "ip_address": log.ip_address,
                        "user_agent": log.user_agent,
                        "duration_ms": log.duration_ms,
                        "extra_json": log.extra_json,
                        "created_at": created_at_val,
                    }
                )

            offset += batch_size

        if not all_logs:
            return 0

        # Write to compressed file
        archive_file = self._get_archive_filename(
            datetime.strptime(log_date, "%Y-%m-%d")
        )

        with gzip.open(archive_file, "wt", encoding="utf-8") as f:
            json.dump(
                {
                    "date": log_date,
                    "count": len(all_logs),
                    "archived_at": datetime.now().isoformat(),
                    "logs": all_logs,
                },
                f,
                indent=2,
                default=str,
            )

        # Delete archived logs from database
        await session.execute(
            delete(AuditLogModel).where(func.date(AuditLogModel.created_at) == log_date)
        )

        return len(all_logs)

    async def cleanup_archived_files(
        self,
        retention_days: int | None = None,
    ) -> dict:
        """Clean up archived files older than retention period.

        Args:
            retention_days: Delete archives older than this many days

        Returns:
            Dict with cleanup statistics
        """
        retention_days = (
            retention_days if retention_days is not None else self.archive_retention_days
        )
        cutoff_date = datetime.now() - timedelta(days=retention_days)

        stats = {
            "files_deleted": 0,
            "space_freed_bytes": 0,
            "errors": [],
        }

        logger.info(f"Starting archive cleanup (cutoff: {cutoff_date.isoformat()})")

        try:
            for archive_file in self.archive_dir.glob("audit_logs_*.json.gz"):
                try:
                    # Extract date from filename
                    date_str = archive_file.stem.replace("audit_logs_", "").replace(
                        ".json", ""
                    )
                    file_date = datetime.strptime(date_str, "%Y-%m-%d")

                    if file_date < cutoff_date:
                        file_size = archive_file.stat().st_size
                        archive_file.unlink()
                        stats["files_deleted"] += 1
                        stats["space_freed_bytes"] += file_size
                        logger.info(f"Deleted archive: {archive_file.name}")

                except Exception as e:
                    error_msg = f"Failed to process {archive_file}: {e}"
                    logger.error(error_msg)
                    stats["errors"].append(error_msg)

        except Exception as e:
            error_msg = f"Cleanup process failed: {e}"
            logger.error(error_msg)
            stats["errors"].append(error_msg)

        logger.info(
            f"Cleanup completed: {stats['files_deleted']} files deleted, "
            f"{stats['space_freed_bytes'] / 1024 / 1024:.2f} MB freed"
        )

        return stats

    async def export_logs(
        self,
        start_date: datetime,
        end_date: datetime,
        format: str = "json",
        include_archived: bool = True,
    ) -> Path:
        """Export audit logs for a date range.

        Args:
            start_date: Start date for export
            end_date: End date for export
            format: Export format (json, csv)
            include_archived: Include archived logs in export

        Returns:
            Path to exported file
        """
        export_dir = self.archive_dir / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_file = export_dir / f"audit_export_{timestamp}.{format}"

        all_logs = []

        # Fetch from database
        async with self.session_factory() as session:
            result = await session.execute(
                select(AuditLogModel)
                .where(AuditLogModel.created_at >= start_date)
                .where(AuditLogModel.created_at <= end_date)
                .order_by(AuditLogModel.created_at)
            )
            logs = result.scalars().all()

            for log in logs:
                created_at_val = (
                    log.created_at.isoformat()
                    if hasattr(log.created_at, "isoformat")
                    else str(log.created_at)
                )
                all_logs.append(
                    {
                        "id": log.id,
                        "user_id": log.user_id,
                        "action": log.action,
                        "method": log.method,
                        "path": log.path,
                        "status_code": log.status_code,
                        "target_type": log.target_type,
                        "target_id": log.target_id,
                        "ip_address": log.ip_address,
                        "user_agent": log.user_agent,
                        "duration_ms": log.duration_ms,
                        "extra_json": log.extra_json,
                        "created_at": created_at_val,
                        "source": "database",
                    }
                )

        # Include archived logs if requested
        if include_archived:
            for archive_file in self.archive_dir.glob("audit_logs_*.json.gz"):
                try:
                    date_str = archive_file.stem.replace("audit_logs_", "").replace(
                        ".json", ""
                    )
                    file_date = datetime.strptime(date_str, "%Y-%m-%d")

                    if start_date.date() <= file_date.date() <= end_date.date():
                        with gzip.open(archive_file, "rt", encoding="utf-8") as f:
                            data = json.load(f)
                            for log in data.get("logs", []):
                                log["source"] = "archive"
                                all_logs.append(log)

                except Exception as e:
                    logger.warning(f"Failed to read archive {archive_file}: {e}")

        # Sort by created_at
        all_logs.sort(key=lambda x: str(x.get("created_at", "")))

        # Write export file
        if format == "json":
            with open(export_file, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "export_date": datetime.now().isoformat(),
                        "date_range": {
                            "start": start_date.isoformat(),
                            "end": end_date.isoformat(),
                        },
                        "total_count": len(all_logs),
                        "logs": all_logs,
                    },
                    f,
                    indent=2,
                    default=str,
                )
        elif format == "csv":
            import csv

            with open(export_file, "w", newline="", encoding="utf-8") as f:
                if all_logs:
                    writer = csv.DictWriter(f, fieldnames=all_logs[0].keys())
                    writer.writeheader()
                    writer.writerows(all_logs)

        logger.info(f"Exported {len(all_logs)} logs to {export_file}")
        return export_file

    async def get_archive_stats(self) -> dict:
        """Get statistics about archived logs.

        Returns:
            Dict with archive statistics
        """
        stats = {
            "archive_dir": str(self.archive_dir),
            "archive_files": 0,
            "total_size_bytes": 0,
            "oldest_archive": None,
            "newest_archive": None,
            "retention_days": self.retention_days,
            "archive_retention_days": self.archive_retention_days,
        }

        try:
            for archive_file in self.archive_dir.glob("audit_logs_*.json.gz"):
                stats["archive_files"] += 1
                stats["total_size_bytes"] += archive_file.stat().st_size

                date_str = archive_file.stem.replace("audit_logs_", "").replace(
                    ".json", ""
                )
                file_date = datetime.strptime(date_str, "%Y-%m-%d")

                if (
                    stats["oldest_archive"] is None
                    or file_date < stats["oldest_archive"]
                ):
                    stats["oldest_archive"] = file_date.isoformat()
                if (
                    stats["newest_archive"] is None
                    or file_date > stats["newest_archive"]
                ):
                    stats["newest_archive"] = file_date.isoformat()

        except Exception as e:
            logger.error(f"Failed to get archive stats: {e}")

        return stats


# Background task for scheduled archival
async def run_scheduled_archival(
    session_factory: async_sessionmaker,
    interval_hours: int = 24,
):
    """Run scheduled audit log archival.

    Args:
        session_factory: AsyncSession factory
        interval_hours: Hours between archival runs
    """
    service = AuditArchiveService(session_factory)

    while True:
        try:
            logger.info("Running scheduled audit log archival")

            # Archive old logs
            archive_stats = await service.archive_old_logs()
            logger.info(f"Archive completed: {archive_stats}")

            # Cleanup old archives
            cleanup_stats = await service.cleanup_archived_files()
            logger.info(f"Cleanup completed: {cleanup_stats}")

        except Exception as e:
            logger.error(f"Scheduled archival failed: {e}")

        # Wait for next run
        await asyncio.sleep(interval_hours * 3600)


# Singleton instance
_archive_service: AuditArchiveService | None = None


def get_archive_service(session_factory: async_sessionmaker) -> AuditArchiveService:
    """Get or create archive service singleton."""
    global _archive_service
    if _archive_service is None:
        _archive_service = AuditArchiveService(session_factory)
    return _archive_service
