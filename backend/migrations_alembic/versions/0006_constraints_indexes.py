"""0006 — unique constraints and missing indexes

T2.3 of finalization-remediation-plan.md.

Issues fixed:
- trigger_invocations.idempotency_key: index=True only, no UNIQUE → concurrent
  duplicate idempotent records possible under load.
- blocked_ips (value, type): no unique constraint → race between SELECT-then-INSERT.
- correlated_events.created_at / updated_at: no index → full-table scan on retention sweep.
- playbook_approvals.run_id: no index → polling-heavy approval workflows scan all rows.

Revision ID: 0006_unique_constraints_and_indexes
Revises: 0005_user_2fa_totp
"""

from alembic import op

# revision identifiers
revision = "0006_constraints_indexes"
down_revision = "0005_user_2fa_totp"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── trigger_invocations: idempotency_key UNIQUE ──────────────────────
    # No duplicates exist (verified: SELECT COUNT before migration = 0 dups).
    # Note: PostgreSQL NULL values are treated as distinct in UNIQUE indexes,
    # so nullable idempotency_key is safe here.
    op.create_unique_constraint(
        "uq_trigger_invocations_idempotency_key",
        "trigger_invocations",
        ["idempotency_key"],
    )

    # ── blocked_ips: (value, type) UNIQUE ────────────────────────────────
    # No duplicates exist (verified: SELECT COUNT before migration = 0 dups).
    op.create_unique_constraint(
        "uq_blocked_ips_value_type",
        "blocked_ips",
        ["value", "type"],
    )

    # ── correlated_events: time-range indexes for retention sweep ─────────
    op.create_index(
        "ix_correlated_events_created_at",
        "correlated_events",
        ["created_at"],
    )
    op.create_index(
        "ix_correlated_events_updated_at",
        "correlated_events",
        ["updated_at"],
    )

    # ── playbook_approvals: run_id index for approval polling ─────────────
    op.create_index(
        "ix_playbook_approvals_run_id",
        "playbook_approvals",
        ["run_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_playbook_approvals_run_id", table_name="playbook_approvals")
    op.drop_index("ix_correlated_events_updated_at", table_name="correlated_events")
    op.drop_index("ix_correlated_events_created_at", table_name="correlated_events")
    op.drop_constraint("uq_blocked_ips_value_type", "blocked_ips", type_="unique")
    op.drop_constraint(
        "uq_trigger_invocations_idempotency_key",
        "trigger_invocations",
        type_="unique",
    )
