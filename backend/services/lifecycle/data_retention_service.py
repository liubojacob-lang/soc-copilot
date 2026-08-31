"""Data retention lifecycle service.

Every table in this platform grows monotonically — alerts, SIEM logs, IOC
hits, playbook runs, AI history — and until now the ONLY automated cleanup
was the audit-log archive. Unbounded growth degrades every index and slows
all hot queries (see architecture review, retention gap).

This service periodically deletes aged rows in bounded batches. Batched
deletes (subquery + DELETE ... IN) work identically on SQLite and PostgreSQL
and keep transactions short so the hot path is never blocked. Tables are
pruned child-first where parent/child relationships exist (playbook run
steps before runs). Audit logs are intentionally NOT handled here — the
AuditArchiveService already archives-then-deletes them.

Configure per-table windows via DATA_RETENTION_* settings; set a window to 0
to keep that table forever.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from core.lifecycle import LifecycleService, ServicePriority
from core.logger import get_logger

logger = get_logger(__name__)


class DataRetentionService(LifecycleService):
    """Bounded-batch retention cleanup for fast-growing tables.

    Priority: OPTIONAL
    Dependencies: database
    """

    def __init__(self) -> None:
        self._task: asyncio.Task | None = None

    @property
    def name(self) -> str:
        return "data_retention"

    @property
    def priority(self) -> ServicePriority:
        return ServicePriority.OPTIONAL

    @property
    def dependencies(self) -> list[str]:
        return ["database"]

    async def start(self) -> None:
        from core.config import settings

        if not settings.data_retention_enabled:
            logger.info("Data retention disabled (DATA_RETENTION_ENABLED=false)")
            return

        self._task = asyncio.create_task(self._run_loop(), name="data-retention-loop")
        logger.info(
            "Data retention service started (interval=%sh)",
            settings.data_retention_interval_hours,
        )

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None
        logger.info("Data retention service stopped")

    async def _run_loop(self) -> None:
        from core.config import settings

        interval = timedelta(hours=settings.data_retention_interval_hours)
        while True:
            try:
                stats = await self.run_cleanup()
                if any(stats.values()):
                    logger.info(f"Data retention cycle: {stats}")
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Data retention cycle failed: {e}")
            await asyncio.sleep(interval.total_seconds())

    async def run_cleanup(self) -> dict[str, int]:
        """Delete aged rows from all managed tables. Returns per-table counts."""
        from core.config import settings
        from db.session import AsyncSessionLocal

        stats: dict[str, int] = {}
        async with AsyncSessionLocal() as session:
            now = datetime.now(UTC)

            # Child tables first, then parents. The child call passes no time
            # column: its rows are selected via the expired parent.
            stats["playbook_run_steps"] = await self._delete_aged(
                session,
                "playbook_run_steps",
                None,
                settings.playbook_run_retention_days,
                now,
                parent_table="playbook_runs",
                parent_col="started_at",
            )
            stats["playbook_runs"] = await self._delete_aged(
                session,
                "playbook_runs",
                "started_at",
                settings.playbook_run_retention_days,
                now,
            )
            stats["siem_logs"] = await self._delete_aged(
                session,
                "siem_logs",
                "timestamp",
                settings.siem_log_retention_days,
                now,
            )
            stats["security_alerts"] = await self._delete_aged(
                session,
                "security_alerts",
                "created_at",
                settings.security_alert_retention_days,
                now,
            )
            stats["ioc_hits"] = await self._delete_aged(
                session,
                "ioc_hits",
                "created_at",
                settings.ioc_hit_retention_days,
                now,
            )
            stats["history"] = await self._delete_aged(
                session,
                "history",
                "created_at",
                settings.history_retention_days,
                now,
            )
            stats["correlated_events"] = await self._delete_aged(
                session,
                "correlated_events",
                "created_at",
                settings.correlated_event_retention_days,
                now,
                string_column=True,  # created_at is a String ISO column here
            )
            # Threat-intel rows already past their TTL (previously manual-only).
            stats["threat_intel_cache"] = await self._delete_expired_ti(
                session,
                now,
                max_age_days=settings.threat_intel_cache_retention_days,
            )
            # Similarity cache rows whose TTL column was never enforced.
            stats["event_similarities"] = await self._delete_expired_similarities(
                session, now
            )
            await session.commit()
        return stats

    async def _delete_aged(
        self,
        session,
        table: str,
        time_column: str | None,
        retention_days: int,
        now: datetime,
        parent_table: str | None = None,
        parent_col: str | None = None,
        string_column: bool = False,
    ) -> int:
        """Delete rows older than the retention window, in bounded batches.

        When parent_table is given, only rows whose parent is ALSO expired are
        removed (keeps child rows alive while the parent is still referenced).

        DateTime columns get a space-separated cutoff — the exact format
        SQLAlchemy's SQLite binder writes, and parseable by PostgreSQL.
        String timestamp columns (correlated_events) keep isoformat, which
        sorts correctly as text.
        """
        from sqlalchemy import text

        from core.config import settings

        if retention_days <= 0:
            return 0

        cutoff_dt = now - timedelta(days=retention_days)
        cutoff = (
            cutoff_dt.isoformat()
            if string_column
            else cutoff_dt.strftime("%Y-%m-%d %H:%M:%S.%f")
        )
        batch_size = settings.data_retention_batch_size
        total = 0

        while True:
            if parent_table:
                child_fk = self._child_fk_for(parent_table)
                stmt = text(
                    f"DELETE FROM {table} WHERE id IN ("  # nosec B608 - identifiers from internal policy constants
                    f"SELECT {table}.id FROM {table} JOIN {parent_table}"
                    f" ON {table}.{child_fk} = {parent_table}.id"
                    f" WHERE {parent_table}.{parent_col} < :cutoff LIMIT :batch)"
                )
            else:
                stmt = text(
                    f"DELETE FROM {table} WHERE {time_column} < :cutoff"  # nosec B608 - identifiers from internal policy constants
                    f" AND id IN (SELECT id FROM {table} WHERE {time_column} < :cutoff LIMIT :batch)"
                )

            result = await session.execute(
                stmt, {"cutoff": cutoff, "batch": batch_size}
            )
            deleted = result.rowcount or 0
            total += deleted
            if deleted < batch_size:
                break
        return total

    @staticmethod
    def _child_fk_for(parent_table: str) -> str:
        """Foreign-key column linking a child table to its parent."""
        return {"playbook_runs": "run_id"}.get(parent_table, f"{parent_table[:-1]}_id")

    async def _delete_expired_ti(
        self, session, now: datetime, max_age_days: int
    ) -> int:
        """Purge threat-intel cache rows past expires_at (and very old ones)."""
        from sqlalchemy import text

        from core.config import settings

        hard_cutoff = (now - timedelta(days=max_age_days)).strftime(
            "%Y-%m-%d %H:%M:%S.%f"
        )
        batch_size = settings.data_retention_batch_size
        total = 0
        while True:
            result = await session.execute(
                text(
                    "DELETE FROM threat_intel_cache WHERE id IN ("
                    "SELECT id FROM threat_intel_cache WHERE expires_at < :now"
                    " OR updated_at < :hard LIMIT :batch)"
                ),
                {
                    "now": now.strftime("%Y-%m-%d %H:%M:%S.%f"),
                    "hard": hard_cutoff,
                    "batch": batch_size,
                },
            )
            deleted = result.rowcount or 0
            total += deleted
            if deleted < batch_size:
                break
        return total

    async def _delete_expired_similarities(self, session, now: datetime) -> int:
        """Enforce event_similarities.ttl_seconds, which no job ever did."""
        from sqlalchemy import text

        result = await session.execute(
            text(
                """
                DELETE FROM event_similarities WHERE id IN (
                    SELECT id FROM event_similarities
                    WHERE datetime(created_at, '+' || ttl_seconds || ' seconds') < :now
                )
                """
            ),
            {"now": now.isoformat()},
        )
        return result.rowcount or 0
