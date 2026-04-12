"""v0.7.1_trigger_system_upgrade

Revision ID: v0_7_1_trigger_system_upgrade
Revises: 63fcc448222d
Create Date: 2026-02-09 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "v0_7_1_trigger_system_upgrade"
down_revision: Union[str, Sequence[str], None] = "63fcc448222d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to v0.7.1 with enhanced trigger system."""

    # Import for connection inspection
    import sqlalchemy as sa
    from sqlalchemy.engine import reflection

    # Get connection and inspector
    conn = op.get_bind()
    inspector = reflection.Inspector.from_engine(conn)

    # Get list of existing tables
    existing_tables = inspector.get_table_names()

    # If tables don't exist yet, skip the migration (SQLAlchemy will create them)
    if "playbook_triggers" not in existing_tables:
        # Tables will be created by SQLAlchemy, not by this migration
        # Just mark the migration as complete
        return

    # Add new columns to playbook_triggers table
    trigger_columns = [
        col["name"] for col in inspector.get_columns("playbook_triggers")
    ]
    if "secret" not in trigger_columns:
        op.add_column(
            "playbook_triggers", sa.Column("secret", sa.String(100), nullable=True)
        )
    if "cron_expr" not in trigger_columns:
        op.add_column(
            "playbook_triggers", sa.Column("cron_expr", sa.String(100), nullable=True)
        )
    if "last_triggered_at" not in trigger_columns:
        op.add_column(
            "playbook_triggers",
            sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
        )

    # Add trigger_id column to playbook_runs if needed
    runs_columns = [col["name"] for col in inspector.get_columns("playbook_runs")]
    if "trigger_id" not in runs_columns:
        op.add_column(
            "playbook_runs", sa.Column("trigger_id", sa.String(36), nullable=True)
        )
        try:
            op.create_index(
                "idx_playbook_runs_trigger_id", "playbook_runs", ["trigger_id"]
            )
        except Exception:
            pass  # Index might already exist

    # Create trigger_invocations table
    if "trigger_invocations" not in existing_tables:
        op.create_table(
            "trigger_invocations",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "trigger_id",
                sa.String(36),
                sa.ForeignKey("playbook_triggers.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("idempotency_key", sa.String(100), nullable=True),
            sa.Column(
                "run_id",
                sa.String(36),
                sa.ForeignKey("playbook_runs.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("request_hash", sa.String(64), nullable=False),
            sa.Column(
                "status", sa.String(20), nullable=False, server_default="pending"
            ),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index(
            "idx_trigger_invocations_trigger_id", "trigger_invocations", ["trigger_id"]
        )
        op.create_index(
            "idx_trigger_invocations_idempotency_key",
            "trigger_invocations",
            ["idempotency_key"],
        )
        op.create_index(
            "idx_trigger_invocations_created_at", "trigger_invocations", ["created_at"]
        )
        op.create_index(
            "idx_trigger_invocations_expires_at", "trigger_invocations", ["expires_at"]
        )

        # Create unique constraint for idempotency
        try:
            op.create_unique_constraint(
                "uq_trigger_invocations_idempotency",
                "trigger_invocations",
                ["trigger_id", "idempotency_key"],
            )
        except Exception:
            pass  # Constraint might already exist


def downgrade() -> None:
    """Downgrade schema from v0.7.1."""

    # Drop trigger_invocations table
    try:
        op.drop_constraint(
            "uq_trigger_invocations_idempotency", "trigger_invocations", type_="unique"
        )
    except:
        pass
    op.drop_index("idx_trigger_invocations_expires_at", "trigger_invocations")
    op.drop_index("idx_trigger_invocations_created_at", "trigger_invocations")
    op.drop_index("idx_trigger_invocations_idempotency_key", "trigger_invocations")
    op.drop_index("idx_trigger_invocations_trigger_id", "trigger_invocations")
    op.drop_table("trigger_invocations")

    # Remove columns from playbook_runs
    op.drop_index("idx_playbook_runs_trigger_id", "playbook_runs")
    op.drop_column("playbook_runs", "trigger_id")

    # Remove columns from playbook_triggers
    op.drop_column("playbook_triggers", "last_triggered_at")
    op.drop_column("playbook_triggers", "cron_expr")
    op.drop_column("playbook_triggers", "secret")
