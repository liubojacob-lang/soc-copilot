"""AI model management tables

Revision ID: v0_7_6
Revises: v0_7_5_dify_integration
Create Date: 2026-02-12

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = "v0_7_6"
down_revision = "v0_7_5_dify_integration"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database."""
    # Create ai_models table
    op.create_table(
        "ai_models",
        sa.Column("id", sa.String(length=100), primary_key=True),
        sa.Column("provider", sa.String(length=50), nullable=False, index=True),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column(
            "is_default", sa.Boolean(), nullable=False, server_default="0", index=True
        ),
        sa.Column("capabilities", sa.JSON(), nullable=True),
        sa.Column("max_tokens", sa.Integer(), nullable=True),
        sa.Column("config", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.String(length=30), nullable=False),
        sa.Column("updated_at", sa.String(length=30), nullable=False),
    )
    # Create index for provider + enabled
    op.create_index(
        "ai_models", "ai_models_provider_enabled_idx", ["provider", "enabled"]
    )

    # Create ai_user_settings table
    op.create_table(
        "ai_user_settings",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(length=36),
            sa.ForeignKey("users.id"),
            nullable=False,
            unique=True,
            index=True,
        ),
        sa.Column("default_model_id", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.String(length=30), nullable=False),
        sa.Column("updated_at", sa.String(length=30), nullable=False),
    )


def downgrade() -> None:
    """Downgrade database."""
    op.drop_table("ai_user_settings")
    op.drop_table("ai_models")
