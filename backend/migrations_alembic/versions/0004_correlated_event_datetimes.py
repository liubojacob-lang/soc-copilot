"""Convert correlated_events timestamps from String(50) to DateTime

The three timestamp columns were ISO text, which forced the retention
service to keep a string-comparison special case and mixed two storage
formats (isoformat from the column default, str(datetime) from service
writes). Real timestamps fix both.

Legacy rows: ISO strings parse cleanly through the I/O conversion that
alembic's batch ALTER performs on PostgreSQL; on SQLite the deployment
should run Scripts/normalize_correlated_event_timestamps.py before this
migration (the development database was normalized out of band).

Revision ID: 0004_correlated_event_datetimes
Revises: 0003_playbook_run_fks
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004_correlated_event_datetimes"
down_revision: Union[str, None] = "0003_playbook_run_fks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("correlated_events") as batch:
        batch.alter_column(
            "created_at",
            type_=sa.DateTime(timezone=True),
            existing_type=sa.String(50),
            existing_nullable=False,
        )
        batch.alter_column(
            "updated_at",
            type_=sa.DateTime(timezone=True),
            existing_type=sa.String(50),
            existing_nullable=False,
        )
        batch.alter_column(
            "resolved_at",
            type_=sa.DateTime(timezone=True),
            existing_type=sa.String(50),
            existing_nullable=True,
        )


def downgrade() -> None:
    with op.batch_alter_table("correlated_events") as batch:
        batch.alter_column(
            "resolved_at",
            type_=sa.String(50),
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=True,
        )
        batch.alter_column(
            "updated_at",
            type_=sa.String(50),
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=False,
        )
        batch.alter_column(
            "created_at",
            type_=sa.String(50),
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=False,
        )
