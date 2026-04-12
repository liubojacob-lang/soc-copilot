"""v0.7.0_dag_playbook_engine

Revision ID: 63fcc448222d
Revises: 475ad8e8fb9b
Create Date: 2026-02-08 19:03:31.331460

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "63fcc448222d"
down_revision: Union[str, Sequence[str], None] = "475ad8e8fb9b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to v0.7.0 with DAG playbook support."""

    # Add new columns to playbook_runs table
    op.add_column(
        "playbook_runs",
        sa.Column(
            "engine_version", sa.String(20), nullable=False, server_default="v0.6"
        ),
    )
    op.add_column(
        "playbook_runs",
        sa.Column(
            "failure_strategy",
            sa.String(20),
            nullable=False,
            server_default="fail_fast",
        ),
    )
    op.add_column(
        "playbook_runs",
        sa.Column("cancel_requested_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Update existing records to have engine_version = 'v0.6'
    op.execute(
        "UPDATE playbook_runs SET engine_version = 'v0.6' WHERE engine_version IS NULL"
    )
    op.execute(
        "UPDATE playbook_runs SET failure_strategy = 'fail_fast' WHERE failure_strategy IS NULL"
    )

    # Create playbook_definitions table
    op.create_table(
        "playbook_definitions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("version", sa.String(20), nullable=False, server_default="1.0.0"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("dag_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column(
            "created_by_user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.create_index("idx_playbook_definitions_name", "playbook_definitions", ["name"])
    op.create_index(
        "idx_playbook_definitions_created_by",
        "playbook_definitions",
        ["created_by_user_id"],
    )
    op.create_index(
        "idx_playbook_definitions_is_active", "playbook_definitions", ["is_active"]
    )

    # Add foreign key constraint for definition_id in playbook_runs
    # First drop the existing column without FK
    op.execute("CREATE TABLE playbook_runs_backup AS SELECT * FROM playbook_runs")
    op.drop_column("playbook_runs", "definition_id")
    op.add_column(
        "playbook_runs",
        sa.Column(
            "definition_id",
            sa.String(36),
            sa.ForeignKey("playbook_definitions.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "idx_playbook_runs_definition_id", "playbook_runs", ["definition_id"]
    )

    # Create playbook_node_runs table
    op.create_table(
        "playbook_node_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "run_id",
            sa.String(36),
            sa.ForeignKey("playbook_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("node_id", sa.String(100), nullable=False),
        sa.Column("node_name", sa.String(200), nullable=False),
        sa.Column("node_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("output_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("input_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_playbook_node_runs_run_id", "playbook_node_runs", ["run_id"])
    op.create_index("idx_playbook_node_runs_node_id", "playbook_node_runs", ["node_id"])
    op.create_index("idx_playbook_node_runs_status", "playbook_node_runs", ["status"])

    # Create playbook_node_attempts table
    op.create_table(
        "playbook_node_attempts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "node_run_id",
            sa.String(36),
            sa.ForeignKey("playbook_node_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("attempt_no", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("log_text", sa.Text(), nullable=True),
        sa.Column("output_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("error_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "idx_playbook_node_attempts_node_run", "playbook_node_attempts", ["node_run_id"]
    )

    # Create playbook_approvals table
    op.create_table(
        "playbook_approvals",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "run_id",
            sa.String(36),
            sa.ForeignKey("playbook_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("node_id", sa.String(100), nullable=False),
        sa.Column(
            "requested_by_user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=False,
        ),
        sa.Column(
            "approved_by_user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_playbook_approvals_run_id", "playbook_approvals", ["run_id"])
    op.create_index("idx_playbook_approvals_status", "playbook_approvals", ["status"])
    op.create_index(
        "idx_playbook_approvals_requested_by",
        "playbook_approvals",
        ["requested_by_user_id"],
    )


def downgrade() -> None:
    """Downgrade schema from v0.7.0."""

    # Drop tables in reverse order
    op.drop_table("playbook_approvals")
    op.drop_table("playbook_node_attempts")
    op.drop_table("playbook_node_runs")
    op.drop_table("playbook_definitions")

    # Remove columns from playbook_runs
    op.drop_index("idx_playbook_runs_definition_id", "playbook_runs")
    op.drop_column("playbook_runs", "definition_id")
    op.drop_column("playbook_runs", "cancel_requested_at")
    op.drop_column("playbook_runs", "failure_strategy")
    op.drop_column("playbook_runs", "engine_version")
