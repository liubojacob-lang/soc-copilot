"""Add marketplace tables

Revision ID: v1_3_0_marketplace
Revises: 4e9cf37ad513
Create Date: 2026-04-12

"""

from alembic import op
import sqlalchemy as sa


revision = "v1_3_0_marketplace"
down_revision = "4e9cf37ad513"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "marketplace_playbooks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(200), sa.CheckConstraint("name IS NOT NULL"), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("version", sa.String(20), server_default="1.0.0"),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("difficulty", sa.String(20), server_default="intermediate"),
        sa.Column("tags", sa.JSON(), server_default="[]"),
        sa.Column(
            "author_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("author_name", sa.String(100), nullable=False),
        sa.Column(
            "source_definition_id",
            sa.String(36),
            sa.ForeignKey("playbook_definitions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("dag_json", sa.JSON(), nullable=False),
        sa.Column("documentation", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column(
            "reviewed_by",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("verified", sa.Boolean(), server_default="0"),
        sa.Column("featured", sa.Boolean(), server_default="0"),
        sa.Column("download_count", sa.Integer(), server_default="0"),
        sa.Column("rating_average", sa.Float(), server_default="0.0"),
        sa.Column("rating_count", sa.Integer(), server_default="0"),
        sa.Column("review_count", sa.Integer(), server_default="0"),
        sa.Column("required_plugins", sa.JSON(), server_default="[]"),
        sa.Column("compatible_versions", sa.JSON(), server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )
    op.create_index("ix_marketplace_playbooks_name", "marketplace_playbooks", ["name"])
    op.create_index("ix_marketplace_playbooks_category", "marketplace_playbooks", ["category"])
    op.create_index("ix_marketplace_playbooks_status", "marketplace_playbooks", ["status"])
    op.create_index("ix_marketplace_playbooks_verified", "marketplace_playbooks", ["verified"])
    op.create_index("ix_marketplace_playbooks_featured", "marketplace_playbooks", ["featured"])
    op.create_index(
        "ix_marketplace_playbooks_status_featured", "marketplace_playbooks", ["status", "featured"]
    )
    op.create_index(
        "ix_marketplace_playbooks_category_status", "marketplace_playbooks", ["category", "status"]
    )

    op.create_table(
        "marketplace_reviews",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "playbook_id",
            sa.String(36),
            sa.ForeignKey("marketplace_playbooks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("username", sa.String(100), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_marketplace_reviews_playbook_id", "marketplace_reviews", ["playbook_id"])
    op.create_index(
        "ix_marketplace_reviews_playbook_user",
        "marketplace_reviews",
        ["playbook_id", "user_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_marketplace_reviews_playbook_user", "marketplace_reviews")
    op.drop_index("ix_marketplace_reviews_playbook_id", "marketplace_reviews")
    op.drop_table("marketplace_reviews")

    op.drop_index("ix_marketplace_playbooks_category_status", "marketplace_playbooks")
    op.drop_index("ix_marketplace_playbooks_status_featured", "marketplace_playbooks")
    op.drop_index("ix_marketplace_playbooks_featured", "marketplace_playbooks")
    op.drop_index("ix_marketplace_playbooks_verified", "marketplace_playbooks")
    op.drop_index("ix_marketplace_playbooks_status", "marketplace_playbooks")
    op.drop_index("ix_marketplace_playbooks_category", "marketplace_playbooks")
    op.drop_index("ix_marketplace_playbooks_name", "marketplace_playbooks")
    op.drop_table("marketplace_playbooks")
