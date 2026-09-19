"""Add TOTP two-factor authentication columns to users table.

Revision ID: 0005_user_2fa_totp
Revises: 0004_correlated_event_datetimes
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005_user_2fa_totp"
down_revision: Union[str, None] = "0004_correlated_event_datetimes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("totp_secret", sa.String(length=255), nullable=True))
        batch.add_column(
            sa.Column(
                "is_totp_enabled",
                sa.Boolean(),
                server_default=sa.false(),
                nullable=False,
            )
        )
        batch.add_column(
            sa.Column(
                "totp_policy",
                sa.String(length=32),
                server_default="sudo",
                nullable=False,
            )
        )
        batch.add_column(
            sa.Column("totp_backup_codes", sa.String(length=1024), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_column("totp_backup_codes")
        batch.drop_column("totp_policy")
        batch.drop_column("is_totp_enabled")
        batch.drop_column("totp_secret")
