"""
Runtime schema compatibility helpers for security_alerts.

This keeps API integration working when local/dev databases were created from
older migrations and miss newly introduced nullable columns.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger

logger = get_logger(__name__)

_schema_checked = False


async def ensure_security_alerts_schema(session: AsyncSession) -> None:
    """Best-effort patch for sqlite security_alerts schema drift."""
    global _schema_checked
    if _schema_checked:
        return

    bind = session.get_bind()
    if bind is None or bind.dialect.name != "sqlite":
        _schema_checked = True
        return

    try:
        table_info = await session.execute(text("PRAGMA table_info(security_alerts)"))
        rows = table_info.fetchall()
        if not rows:
            # Table does not exist yet; let normal migration/bootstrap create it.
            return

        existing_columns = {row[1] for row in rows}
        needed_columns = {
            "tenant_id": "TEXT NOT NULL DEFAULT 'default'",
            "assigned_at": "DATETIME",
            "resolution_note": "TEXT",
            "root_cause": "TEXT",
            "remediation": "TEXT",
            "resolved_at": "DATETIME",
            "resolved_by": "TEXT",
            "escalated_to": "TEXT",
            "escalated_at": "DATETIME",
            "escalation_reason": "TEXT",
            "threat_score": "INTEGER",
            "enriched_at": "DATETIME",
            "iocs": "JSON",
            "mitre_tactics": "JSON",
            "mitre_techniques": "JSON",
            "tags": "JSON",
            "classification": "VARCHAR(50)",
        }

        missing = {k: v for k, v in needed_columns.items() if k not in existing_columns}
        for column_name, column_def in missing.items():
            await session.execute(
                text(f"ALTER TABLE security_alerts ADD COLUMN {column_name} {column_def}")
            )
            logger.warning("Patched security_alerts missing column: %s", column_name)

        # Backfill legacy fields when old columns exist.
        if "resolution" in existing_columns:
            await session.execute(
                text(
                    "UPDATE security_alerts "
                    "SET resolution_note = resolution "
                    "WHERE resolution_note IS NULL AND resolution IS NOT NULL"
                )
            )
        if "closed_at" in existing_columns:
            await session.execute(
                text(
                    "UPDATE security_alerts "
                    "SET resolved_at = closed_at "
                    "WHERE resolved_at IS NULL AND closed_at IS NOT NULL"
                )
            )
        if "closed_by" in existing_columns:
            await session.execute(
                text(
                    "UPDATE security_alerts "
                    "SET resolved_by = CAST(closed_by AS TEXT) "
                    "WHERE resolved_by IS NULL AND closed_by IS NOT NULL"
                )
            )

        if missing:
            await session.commit()
        _schema_checked = True
    except Exception as exc:
        # Do not block business flow if patching fails.
        logger.warning("security_alerts schema compatibility patch skipped: %s", exc)
