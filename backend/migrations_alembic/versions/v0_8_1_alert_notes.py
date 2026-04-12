"""Add alert notes table

Revision ID: v0_8_1_alert_notes
Revises: v1_2_0_phase1_optimizations
Create Date: 2026-03-02

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = "v0_8_1_alert_notes"
down_revision = "v1_2_0_phase1_optimizations"
branch_labels = None
depends_on = None


def upgrade():
    """Create alert_notes table"""
    op.create_table(
        "alert_notes",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "alert_id",
            sa.Integer(),
            sa.ForeignKey("security_alerts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # Create indexes
    op.create_index("ix_alert_notes_alert_id", "alert_notes", ["alert_id"])
    op.create_index("ix_alert_notes_user_id", "alert_notes", ["user_id"])


def downgrade():
    """Drop alert_notes table"""
    op.drop_index("ix_alert_notes_user_id", table_name="alert_notes")
    op.drop_index("ix_alert_notes_alert_id", table_name="alert_notes")
    op.drop_table("alert_notes")
