"""v0_7_4_secrets_run_queue

Revision ID: v0_7_4_secrets_run_queue
Revises: v0_7_3_version_context_replay
Create Date: 2026-02-10 00:00:00.000000

Adds enterprise SOAR capabilities to SOC Copilot v0.7.4:
- Secrets management (encrypted storage with Fernet)
- Run execution queue (concurrency control with FIFO policy)
- Run recovery (mark orphaned runs after server restart)
- Node plugin system (dynamic loading from plugins/ directory)

Schema Changes:
- secrets: New table for encrypted secret storage
- playbook_runs: Add queued_at column for queue management
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision: str = 'v0_7_4_secrets_run_queue'
down_revision: Union[str, Sequence[str], None] = 'v0_7_3_version_context_replay'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to v0.7.4 with secrets and run queue."""

    import sqlalchemy as sa
    from sqlalchemy.engine import reflection

    # Get connection and inspector
    conn = op.get_bind()
    inspector = reflection.Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()

    # ============================================================
    # 1. Create secrets table
    # ============================================================
    if 'secrets' not in existing_tables:
        op.create_table(
            'secrets',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('name', sa.String(100), unique=True, index=True, nullable=False),
            sa.Column('encrypted_value', sa.Text(), nullable=False),
            sa.Column('created_by_user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.utcnow()),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.utcnow(), onupdate=sa.func.utcnow()),
        )

        # Create indexes for secret lookup
        op.create_index('idx_secrets_name', 'secrets', ['name'])
        op.create_index('idx_secrets_created_at', 'secrets', ['created_at'])

    # ============================================================
    # 2. Add queued_at to playbook_runs
    # ============================================================
    if 'playbook_runs' in existing_tables:
        # Check if columns exist
        columns = [col['name'] for col in inspector.get_columns('playbook_runs')]

        # Add queued_at column
        if 'queued_at' not in columns:
            op.add_column(
                'playbook_runs',
                sa.Column('queued_at', sa.DateTime(timezone=True), nullable=True)
            )
            op.create_index('idx_playbook_runs_queued_at', 'playbook_runs', ['queued_at'])


def downgrade() -> None:
    """Downgrade schema from v0.7.4."""

    import sqlalchemy as sa

    # ============================================================
    # 1. Remove queued_at from playbook_runs
    # ============================================================
    try:
        op.drop_index('idx_playbook_runs_queued_at', 'playbook_runs')
    except:
        pass

    try:
        op.drop_column('playbook_runs', 'queued_at')
    except:
        pass

    # ============================================================
    # 2. Drop secrets table
    # ============================================================
    try:
        op.drop_index('idx_secrets_created_at', 'secrets')
    except:
        pass

    try:
        op.drop_index('idx_secrets_name', 'secrets')
    except:
        pass

    try:
        op.drop_table('secrets')
    except:
        pass
