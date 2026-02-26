"""Add user security columns

Revision ID: e8521c2c56f4
Revises: v0_7_7_ai_task_queue
Create Date: 2026-02-14 22:46:50.522766

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e8521c2c56f4'
down_revision: Union[str, Sequence[str], None] = 'v0_7_7_ai_task_queue'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add user security columns
    op.add_column('users', sa.Column('password_changed_at', sa.String(length=30), nullable=True))
    op.add_column('users', sa.Column('must_change_password', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('failed_login_attempts', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('locked_until', sa.String(length=30), nullable=True))
    op.add_column('users', sa.Column('password_history', sa.JSON(), nullable=False, server_default='[]'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'password_history')
    op.drop_column('users', 'locked_until')
    op.drop_column('users', 'failed_login_attempts')
    op.drop_column('users', 'must_change_password')
    op.drop_column('users', 'password_changed_at')
