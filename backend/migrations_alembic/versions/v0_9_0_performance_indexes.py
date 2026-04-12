"""Add composite indexes for performance optimization

Revision ID: v0_9_0_performance_indexes
Revises:
Create Date: 2025-02-19

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import Index


# revision identifiers, used by Alembic.
revision = "v0_9_0_performance_indexes"
down_revision = "v0_8_0_event_correlation"


def upgrade():
    """Add composite indexes for common query patterns"""

    # Playbook runs indexes
    op.create_index(
        "idx_playbook_run_status_time",
        "playbook_runs",
        ["status", sa.text("started_at DESC")],
    )

    op.create_index(
        "idx_playbook_run_def_time",
        "playbook_runs",
        ["definition_id", sa.text("started_at DESC")],
    )

    # Playbook definitions indexes
    op.create_index(
        "idx_playbook_def_active_time",
        "playbook_definitions",
        ["is_active", sa.text("updated_at DESC")],
    )

    op.create_index(
        "idx_playbook_def_status_published",
        "playbook_definitions",
        ["status", sa.text("published_at DESC")],
    )

    # Users indexes
    op.create_index("idx_user_role_active", "users", ["role", "is_active"])

    # Note: Alerts table doesn't exist yet, skipping those indexes
    # They will be added when the alerts table is created


def downgrade():
    """Remove composite indexes"""

    # Playbook runs
    op.drop_index("idx_playbook_run_status_time", table_name="playbook_runs")
    op.drop_index("idx_playbook_run_def_time", table_name="playbook_runs")

    # Playbook definitions
    op.drop_index("idx_playbook_def_active_time", table_name="playbook_definitions")
    op.drop_index(
        "idx_playbook_def_status_published", table_name="playbook_definitions"
    )

    # Users
    op.drop_index("idx_user_role_active", table_name="users")
