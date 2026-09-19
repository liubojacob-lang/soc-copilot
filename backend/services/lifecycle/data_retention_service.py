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
from collections.abc import Awaitable, Callable
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

    def _cleanup_jobs(
        self, session, now: datetime, only: list[str]
    ) -> dict[str, Awaitable[int]]:
        """Aged-row cleanup tasks for the requested tables, child tables first.

        The playbook_run_steps call passes no time column: its rows are
        selected via the expired parent run.
        """
        from core.config import settings

        aged = self._delete_aged
        d = settings
        builders: dict[str, Callable[[], Awaitable[int]]] = {
            "playbook_run_steps": lambda: aged(
                session,
                "playbook_run_steps",
                None,
                d.playbook_run_retention_days,
                now,
                parent_table="playbook_runs",
                parent_col="started_at",
            ),
            "playbook_runs": lambda: aged(
                session, "playbook_runs", "started_at", d.playbook_run_retention_days, now
            ),
            "siem_logs": lambda: aged(
                session, "siem_logs", "timestamp", d.siem_log_retention_days, now
            ),
            "security_alerts": lambda: aged(
                session,
                "security_alerts",
                "created_at",
                d.security_alert_retention_days,
                now,
            ),
            "ioc_hits": lambda: aged(
                session, "ioc_hits", "created_at", d.ioc_hit_retention_days, now
            ),
            "history": lambda: aged(
                session, "history", "created_at", d.history_retention_days, now
            ),
            "correlated_events": lambda: aged(
                session,
                "correlated_events",
                "created_at",
                d.correlated_event_retention_days,
                now,
            ),
            # Threat-intel rows already past their TTL (previously manual-only).
            "threat_intel_cache": lambda: self._delete_expired_ti(
                session, now, max_age_days=d.threat_intel_cache_retention_days
            ),
        }
        return {table: builders[table]() for table in only}

    async def run_cleanup(self) -> dict[str, int]:
        """Delete aged rows from all managed tables. Returns per-table counts.

        The happy path is a single transaction — on SQLite a mid-cycle
        commit/release makes the next statement re-contend for the write lock
        against live app writers, which deadlocked the cycle in tests.
        Isolation is handled on the failure path instead: when a table's
        cleanup raises, the pass is rolled back and every other table re-runs
        in a fresh transaction, so one broken table never loses the others'
        deletions — the broken table itself is skipped and logged.
        """
        from db.session import AsyncSessionLocal

        stats: dict[str, int] = {}
        pending = self._cleanup_table_order()
        # Every pass either commits, or rolls back and permanently skips one
        # table, so this loop is bounded.
        for _ in range(len(self._cleanup_table_order()) + 1):
            if not pending:
                break
            async with AsyncSessionLocal() as session:
                now = datetime.now(UTC)
                jobs = self._cleanup_jobs(session, now, only=pending)
                pass_stats: dict[str, int] = {}
                first_failure: int | None = None
                for idx, table in enumerate(pending):
                    try:
                        pass_stats[table] = await jobs[table]
                    except Exception as e:
                        logger.error(
                            f"Data retention cleanup failed for {table}: {e}"
                        )
                        first_failure = idx
                        break
                if first_failure is None:
                    try:
                        await session.commit()
                    except Exception as e:
                        logger.error(f"Data retention commit failed: {e}")
                        continue  # nothing committed; retry the same tables
                    stats.update(pass_stats)
                    break
                # A table failed mid-pass: discard this pass's work and re-run
                # every other table in a fresh transaction.
                await session.rollback()
                skipped = pending[first_failure]
                pending = [t for t in pending if t != skipped]
        return stats

    @staticmethod
    def _cleanup_table_order() -> list[str]:
        """Child tables first, then parents, then TTL caches."""
        return [
            "playbook_run_steps",
            "playbook_runs",
            "siem_logs",
            "security_alerts",
            "ioc_hits",
            "history",
            "correlated_events",
            "threat_intel_cache",
        ]

    async def _delete_aged(
        self,
        session,
        table: str,
        time_column: str | None,
        retention_days: int,
        now: datetime,
        parent_table: str | None = None,
        parent_col: str | None = None,
    ) -> int:
        """Delete rows older than the retention window, in bounded batches.

        When parent_table is given, only rows whose parent is ALSO expired are
        removed (keeps child rows alive while the parent is still referenced).

        The cutoff is bound as a typed DateTime parameter so each dialect's
        own binder applies (native datetime on PostgreSQL/asyncpg, its storage
        format on SQLite) — hand-formatting the cutoff as a string fails
        asyncpg's strict typing.
        """
        from sqlalchemy import DateTime, bindparam, text

        from core.config import settings

        if retention_days <= 0:
            return 0

        cutoff = now - timedelta(days=retention_days)
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
                ).bindparams(bindparam("cutoff", type_=DateTime(timezone=True)))
            else:
                stmt = text(
                    f"DELETE FROM {table} WHERE {time_column} < :cutoff"  # nosec B608 - identifiers from internal policy constants
                    f" AND id IN (SELECT id FROM {table} WHERE {time_column} < :cutoff LIMIT :batch)"
                ).bindparams(bindparam("cutoff", type_=DateTime(timezone=True)))

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
        """Purge threat-intel cache rows past expires_at (and very old ones).

        The cache columns are naive DateTime, so the cutoffs are bound as
        typed naive datetime params — hand-formatting them as strings fails
        asyncpg's strict typing, same as in _delete_aged.
        """
        from sqlalchemy import DateTime, bindparam, text

        from core.config import settings

        batch_size = settings.data_retention_batch_size
        total = 0
        while True:
            result = await session.execute(
                text(
                    "DELETE FROM threat_intel_cache WHERE id IN ("
                    "SELECT id FROM threat_intel_cache WHERE expires_at < :now"
                    " OR updated_at < :hard LIMIT :batch)"
                ).bindparams(
                    bindparam("now", type_=DateTime()),
                    bindparam("hard", type_=DateTime()),
                ),
                {
                    "now": now.replace(tzinfo=None),
                    "hard": (now - timedelta(days=max_age_days)).replace(tzinfo=None),
                    "batch": batch_size,
                },
            )
            deleted = result.rowcount or 0
            total += deleted
            if deleted < batch_size:
                break
        return total
