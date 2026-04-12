"""v0.7.2_approval_system

Revision ID: v0_7_2_approval_system
Revises: v0_7_1_trigger_system_upgrade
Create Date: 2026-02-09 00:00:00.000000

Adds approval system for human approval nodes in playbooks.
- approvals table with status tracking
- Indexes for status and run_id
- Foreign keys to runs and users
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision: str = "v0_7_2_approval_system"
down_revision: Union[str, Sequence[str], None] = "v0_7_1_trigger_system_upgrade"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to v0.7.2 with approval system."""

    # Import for connection inspection
    import sqlalchemy as sa
    from sqlalchemy.engine import reflection

    # Get connection and inspector
    conn = op.get_bind()
    inspector = reflection.Inspector.from_engine(conn)

    # Get list of existing tables
    existing_tables = inspector.get_table_names()

    # Create playbook_approvals table
    if "playbook_approvals" not in existing_tables:
        op.create_table(
            "playbook_approvals",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "run_id",
                sa.String(36),
                sa.ForeignKey("playbook_runs.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("node_id", sa.String(100), nullable=False, index=True),
            sa.Column(
                "requested_by_user_id",
                sa.String(36),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "approved_by_user_id",
                sa.String(36),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "rejected_by_user_id",
                sa.String(36),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "status",
                sa.String(20),
                nullable=False,
                server_default="pending",
                index=True,
            ),
            sa.Column("title", sa.String(200), nullable=True),
            sa.Column("message", sa.Text(), nullable=True),
            sa.Column("comments", sa.Text(), nullable=True),
            sa.Column("timeout_seconds", sa.Integer(), nullable=True),
            sa.Column(
                "on_timeout", sa.String(20), nullable=False, server_default="fail"
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.utcnow(),
            ),
            sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        )

        # Create indexes
        op.create_index(
            "idx_playbook_approvals_status", "playbook_approvals", ["status"]
        )
        op.create_index(
            "idx_playbook_approvals_run_id", "playbook_approvals", ["run_id"]
        )
        op.create_index(
            "idx_playbook_approvals_created_at", "playbook_approvals", ["created_at"]
        )
        op.create_index(
            "idx_playbook_approvals_expires_at", "playbook_approvals", ["expires_at"]
        )

        # Create composite index for pending approvals lookup
        op.create_index(
            "idx_playbook_approvals_status_created",
            "playbook_approvals",
            ["status", "created_at"],
        )


def downgrade() -> None:
    """Downgrade schema from v0.7.2."""

    # Drop indexes
    try:
        op.drop_index("idx_playbook_approvals_status_created", "playbook_approvals")
    except:
        pass
    op.drop_index("idx_playbook_approvals_expires_at", "playbook_approvals")
    op.drop_index("idx_playbook_approvals_created_at", "playbook_approvals")
    op.drop_index("idx_playbook_approvals_run_id", "playbook_approvals")
    op.drop_index("idx_playbook_approvals_status", "playbook_approvals")

    # Drop table
    op.drop_table("playbook_approvals")
