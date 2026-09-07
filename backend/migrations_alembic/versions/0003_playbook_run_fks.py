"""Add FKs on playbook_runs (created_by_user_id, parent_run_id)

created_by_user_id previously had no FK: deleting a user row could leave
runs pointing at a ghost id. The FK uses SET NULL because users are soft
deleted in practice, and parent_run_id cascades with its run.

Note: the deployment this runs against was verified to contain no orphan
rows (0 rows with created_by_user_id/parent_run_id not matching an
existing user/run). If FK creation fails on another environment, clean
orphan values first — the failure mode is loud, not silent corruption.

Revision ID: 0003_playbook_run_fks
Revises: 0002_performance_indexes
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_playbook_run_fks"
down_revision: Union[str, None] = "0002_performance_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("playbook_runs") as batch:
        batch.create_foreign_key(
            "fk_playbook_runs_created_by_users",
            "users",
            ["created_by_user_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch.create_foreign_key(
            "fk_playbook_runs_parent_run",
            "playbook_runs",
            ["parent_run_id"],
            ["id"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    with op.batch_alter_table("playbook_runs") as batch:
        batch.drop_constraint("fk_playbook_runs_parent_run", type_="foreignkey")
        batch.drop_constraint("fk_playbook_runs_created_by_users", type_="foreignkey")
