"""v1.1.0 architecture upgrade (event bus, tenant + rbac prep)

Revision ID: v1_1_0_arch_upgrade
Revises: v0_9_1_security_alerts
Create Date: 2026-02-25
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "v1_1_0_arch_upgrade"
down_revision = "v0_9_1_security_alerts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # tenant columns
    op.add_column("security_alerts", sa.Column("tenant_id", sa.String(length=64), nullable=False, server_default="default"))
    op.create_index("ix_security_alerts_tenant_id", "security_alerts", ["tenant_id"], unique=False)

    op.add_column("correlation_rules", sa.Column("tenant_id", sa.String(length=64), nullable=False, server_default="default"))
    op.create_index("ix_correlation_rules_tenant_id", "correlation_rules", ["tenant_id"], unique=False)

    op.add_column("users", sa.Column("tenant_id", sa.String(length=64), nullable=False, server_default="default"))
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"], unique=False)

    # RBAC core tables
    op.create_table(
        "roles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_roles_name", "roles", ["name"], unique=True)

    op.create_table(
        "permissions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("resource", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_permissions_code", "permissions", ["code"], unique=True)
    op.create_index("ix_permissions_resource", "permissions", ["resource"], unique=False)
    op.create_index("ix_permissions_action", "permissions", ["action"], unique=False)
    op.create_index("ix_permissions_resource_action", "permissions", ["resource", "action"], unique=False)

    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.String(length=36), nullable=False),
        sa.Column("permission_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"]),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"]),
        sa.PrimaryKeyConstraint("role_id", "permission_id"),
    )


def downgrade() -> None:
    op.drop_table("role_permissions")

    op.drop_index("ix_permissions_resource_action", table_name="permissions")
    op.drop_index("ix_permissions_action", table_name="permissions")
    op.drop_index("ix_permissions_resource", table_name="permissions")
    op.drop_index("ix_permissions_code", table_name="permissions")
    op.drop_table("permissions")

    op.drop_index("ix_roles_name", table_name="roles")
    op.drop_table("roles")

    op.drop_index("ix_users_tenant_id", table_name="users")
    op.drop_column("users", "tenant_id")

    op.drop_index("ix_correlation_rules_tenant_id", table_name="correlation_rules")
    op.drop_column("correlation_rules", "tenant_id")

    op.drop_index("ix_security_alerts_tenant_id", table_name="security_alerts")
    op.drop_column("security_alerts", "tenant_id")
