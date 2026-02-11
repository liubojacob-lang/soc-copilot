"""Add Dify workflow integration fields

Revision ID: v0_7_5_dify_integration
Revises: v0_7_4_secrets_run_queue
Create Date: 2026-02-10

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'v0_7_5_dify_integration'
down_revision = 'v0_7_4_secrets_run_queue'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add Dify integration fields to playbook_definitions
    op.add_column('playbook_definitions', sa.Column('dify_app_id', sa.String(100), nullable=True, index=True))
    op.add_column('playbook_definitions', sa.Column('dify_synced_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('playbook_definitions', sa.Column('execution_engine', sa.String(20), server_default='native', nullable=False))


def downgrade() -> None:
    # Remove Dify integration fields from playbook_definitions
    op.drop_column('playbook_definitions', 'execution_engine')
    op.drop_column('playbook_definitions', 'dify_synced_at')
    op.drop_column('playbook_definitions', 'dify_app_id')
