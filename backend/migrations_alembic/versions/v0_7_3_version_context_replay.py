"""v0.7.3_version_context_replay

Revision ID: v0_7_3_version_context_replay
Revises: v0_7_2_approval_system
Create Date: 2026-02-09 00:00:00.000000

Adds industrial-grade capabilities to SOC Copilot v0.7.3:
- Playbook version management (draft/published/archived)
- Run context variable system with JSONPath mapping
- Replay functionality with lineage tracking
- Import/Export support (JSON/YAML)

Schema Changes:
- playbook_definitions: Add status, published_at, updated_at, current_version_no
- playbook_definition_versions: New table for version history
- playbook_runs: Add input_context_json, context_json, replay_of_run_id
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision: str = "v0_7_3_version_context_replay"
down_revision: Union[str, Sequence[str], None] = "v0_7_2_approval_system"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to v0.7.3 with version management, context system, and replay."""

    import sqlalchemy as sa
    from sqlalchemy.engine import reflection

    # Get connection and inspector
    conn = op.get_bind()
    inspector = reflection.Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()

    # ============================================================
    # 1. Add columns to playbook_definitions
    # ============================================================
    if "playbook_definitions" in existing_tables:
        # Check if columns exist
        columns = [col["name"] for col in inspector.get_columns("playbook_definitions")]

        # Add status column (draft|published|archived)
        if "status" not in columns:
            op.add_column(
                "playbook_definitions",
                sa.Column(
                    "status",
                    sa.String(20),
                    nullable=False,
                    server_default="draft",
                    index=True,
                ),
            )
            op.create_index(
                "idx_playbook_definitions_status", "playbook_definitions", ["status"]
            )

        # Add published_at column
        if "published_at" not in columns:
            op.add_column(
                "playbook_definitions",
                sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
            )

        # Add current_version_no column
        if "current_version_no" not in columns:
            op.add_column(
                "playbook_definitions",
                sa.Column(
                    "current_version_no",
                    sa.Integer(),
                    nullable=False,
                    server_default="1",
                ),
            )

    # ============================================================
    # 2. Create playbook_definition_versions table
    # ============================================================
    if "playbook_definition_versions" not in existing_tables:
        # Note: SQLite doesn't support adding unique constraints after table creation
        # The unique constraint is handled at the application level by SQLAlchemy
        op.create_table(
            "playbook_definition_versions",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "playbook_definition_id",
                sa.String(36),
                sa.ForeignKey("playbook_definitions.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column("version_no", sa.Integer(), nullable=False),
            sa.Column("dag_json", sa.JSON(), nullable=False),
            sa.Column("name", sa.String(200), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column(
                "created_by_user_id",
                sa.String(36),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.utcnow(),
            ),
            sa.Column("change_note", sa.Text(), nullable=True),
            # Check constraint for positive version numbers
            sa.CheckConstraint("version_no > 0", name="ck_version_no_positive"),
        )

        # Create indexes for version lookup
        op.create_index(
            "idx_playbook_definition_versions_definition_id",
            "playbook_definition_versions",
            ["playbook_definition_id"],
        )
        op.create_index(
            "idx_playbook_definition_versions_version_no",
            "playbook_definition_versions",
            ["version_no"],
        )
        op.create_index(
            "idx_playbook_definition_versions_created_at",
            "playbook_definition_versions",
            ["created_at"],
        )
        # Note: Composite unique constraint handled by SQLAlchemy, not created here due to SQLite limitation

    # ============================================================
    # 3. Add columns to playbook_runs for context system and replay
    # ============================================================
    if "playbook_runs" in existing_tables:
        # Check if columns exist
        columns = [col["name"] for col in inspector.get_columns("playbook_runs")]

        # Add input_context_json column for initial context
        if "input_context_json" not in columns:
            op.add_column(
                "playbook_runs",
                sa.Column(
                    "input_context_json", sa.JSON(), nullable=False, server_default="{}"
                ),
            )

        # Add context_json column for dynamic accumulated variables
        if "context_json" not in columns:
            op.add_column(
                "playbook_runs",
                sa.Column(
                    "context_json", sa.JSON(), nullable=False, server_default="{}"
                ),
            )

        # Add replay_of_run_id column for replay lineage
        # Note: SQLite doesn't support adding FK via ALTER TABLE, FK handled by SQLAlchemy at app level
        if "replay_of_run_id" not in columns:
            op.add_column(
                "playbook_runs",
                sa.Column("replay_of_run_id", sa.String(36), nullable=True, index=True),
            )
            op.create_index(
                "idx_playbook_runs_replay_of_run_id",
                "playbook_runs",
                ["replay_of_run_id"],
            )


def downgrade() -> None:
    """Downgrade schema from v0.7.3."""

    import sqlalchemy as sa

    # ============================================================
    # 1. Remove columns from playbook_runs
    # ============================================================
    try:
        op.drop_index("idx_playbook_runs_replay_of_run_id", "playbook_runs")
    except:
        pass

    try:
        op.drop_column("playbook_runs", "replay_of_run_id")
    except:
        pass

    try:
        op.drop_column("playbook_runs", "context_json")
    except:
        pass

    try:
        op.drop_column("playbook_runs", "input_context_json")
    except:
        pass

    # ============================================================
    # 2. Drop playbook_definition_versions table
    # ============================================================
    # Note: No unique constraint to drop (SQLite limitation)

    try:
        op.drop_index(
            "idx_playbook_definition_versions_created_at",
            "playbook_definition_versions",
        )
    except:
        pass

    try:
        op.drop_index(
            "idx_playbook_definition_versions_version_no",
            "playbook_definition_versions",
        )
    except:
        pass

    try:
        op.drop_index(
            "idx_playbook_definition_versions_definition_id",
            "playbook_definition_versions",
        )
    except:
        pass

    try:
        op.drop_table("playbook_definition_versions")
    except:
        pass

    # ============================================================
    # 3. Remove columns from playbook_definitions
    # ============================================================
    try:
        op.drop_index("idx_playbook_definitions_status", "playbook_definitions")
    except:
        pass

    try:
        op.drop_column("playbook_definitions", "current_version_no")
    except:
        pass

    try:
        op.drop_column("playbook_definitions", "published_at")
    except:
        pass

    try:
        op.drop_column("playbook_definitions", "status")
    except:
        pass
