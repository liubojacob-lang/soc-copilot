"""0010 — webhook idempotency: per-trigger uniqueness (audit-run1)

Fixes the check-then-act window in TriggerService.handle_webhook: the
dedupe SELECT (check_idempotency) raced against record_invocation because
no constraint backed (trigger_id, request_hash), so concurrent identical
deliveries both executed the playbook in apply mode.

Changes:
- Deduplicate existing trigger_invocations rows sharing (trigger_id,
  request_hash) — keep the newest of each group.
- Unique index on (trigger_id, request_hash): makes the dedupe decision
  database-enforced; handle_webhook now treats IntegrityError as a
  concurrent duplicate and returns the cached invocation.
- Replace the global unique on idempotency_key with (trigger_id,
  idempotency_key): a key is only meaningful within its trigger; the
  global constraint 500'd validly signed requests reusing a key across
  triggers (audit-run1 hardening note).

Revision ID: 0010_trigger_idempotency_unique
Revises: 0009_rca_human_verified_bool
"""

from alembic import op

# revision identifiers
revision = "0010_trigger_idempotency_unique"
down_revision = "0009_rca_human_verified_bool"
branch_labels = None
depends_on = None

TABLE = "trigger_invocations"


def _dedupe_duplicates() -> None:
    """Delete older duplicates per (trigger_id, request_hash), keep newest."""
    op.execute(
        f"""
        DELETE FROM {TABLE} a
        USING {TABLE} b
        WHERE a.trigger_id = b.trigger_id
          AND a.request_hash = b.request_hash
          AND a.created_at < b.created_at
        """
    )
    # Tie-break rows with identical timestamps (same-millisecond bursts)
    op.execute(
        f"""
        DELETE FROM {TABLE} a
        USING {TABLE} b
        WHERE a.trigger_id = b.trigger_id
          AND a.request_hash = b.request_hash
          AND a.created_at = b.created_at
          AND a.id < b.id
        """
    )


def upgrade() -> None:
    _dedupe_duplicates()

    # Drop the global idempotency_key unique (if present) — keys are
    # per-trigger; a global constraint 500'd cross-trigger key reuse.
    from sqlalchemy import text

    conn = op.get_bind()
    old = conn.execute(
        text(
            "SELECT 1 FROM pg_constraint WHERE conname = 'uq_trigger_invocations_idempotency_key'"
        )
    ).scalar()
    if old:
        op.drop_constraint(
            "uq_trigger_invocations_idempotency_key", TABLE, type_="unique"
        )

    op.create_index(
        "ux_trigger_invocations_trigger_request",
        TABLE,
        ["trigger_id", "request_hash"],
        unique=True,
    )
    op.create_index(
        "ux_trigger_invocations_trigger_key",
        TABLE,
        ["trigger_id", "idempotency_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ux_trigger_invocations_trigger_key", table_name=TABLE)
    op.drop_index("ux_trigger_invocations_trigger_request", table_name=TABLE)
    op.create_unique_constraint(
        "uq_trigger_invocations_idempotency_key", TABLE, ["idempotency_key"]
    )
