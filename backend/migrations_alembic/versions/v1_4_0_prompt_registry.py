"""Add prompt_registry table

Revision ID: v1_4_0_prompt_registry
Revises: v1_3_0_marketplace
Create Date: 2026-04-15

"""

from alembic import op
import sqlalchemy as sa

revision = "v1_4_0_prompt_registry"
down_revision = "v1_3_0_marketplace"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "prompt_registry",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("variables", sa.JSON(), server_default="[]"),
        sa.Column(
            "environment",
            sa.String(20),
            server_default="dev",
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "created_by", sa.String(255), server_default="system", nullable=False
        ),
        sa.Column("created_at", sa.String(255), nullable=False),
        sa.Column("updated_at", sa.String(255), nullable=False),
    )
    op.create_index("ix_prompt_registry_name", "prompt_registry", ["name"])
    op.create_index("ix_prompt_registry_version", "prompt_registry", ["version"])
    op.create_index(
        "ix_prompt_registry_environment", "prompt_registry", ["environment"]
    )
    op.create_index("ix_prompt_registry_is_active", "prompt_registry", ["is_active"])
    op.create_index(
        "ix_prompt_env_active",
        "prompt_registry",
        ["environment", "is_active", "name"],
    )
    op.create_unique_constraint(
        "uq_prompt_name_ver_env",
        "prompt_registry",
        ["name", "version", "environment"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_prompt_name_ver_env", "prompt_registry", type_="unique")
    op.drop_index("ix_prompt_env_active", "prompt_registry")
    op.drop_index("ix_prompt_registry_is_active", "prompt_registry")
    op.drop_index("ix_prompt_registry_environment", "prompt_registry")
    op.drop_index("ix_prompt_registry_version", "prompt_registry")
    op.drop_index("ix_prompt_registry_name", "prompt_registry")
    op.drop_table("prompt_registry")
