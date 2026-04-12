"""merge_heads

Revision ID: 4e9cf37ad513
Revises: v0_8_1_alert_notes, v1_2_0_alert_deduplication
Create Date: 2026-04-09 21:20:51.940630

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4e9cf37ad513"
down_revision: Union[str, Sequence[str], None] = (
    "v0_8_1_alert_notes",
    "v1_2_0_alert_deduplication",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
