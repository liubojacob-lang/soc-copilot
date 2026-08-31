"""Composite performance indexes for hot tables.

Restores the composite indexes that previously lived in the pre-baseline
migration chain (v1_2_0_phase1_optimizations et al.), which was removed when
the schema baseline was squashed. All of these target the hottest query
shapes: dashboard aggregates, list filtering by status/severity/source, and
audit/user activity lookups.

Adopting an EXISTING database (created by create_all): run
`alembic stamp 0002_performance_indexes` once; no DDL is required because the
baseline schema matches the current models.

Revision ID: 0002_performance_indexes
Revises: 0001_full_baseline
Create Date: 2026-08-30
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0002_performance_indexes"
down_revision = "0001_full_baseline"
branch_labels = None
depends_on = None

# (name, table, columns) — expression columns use sa.text for DESC ordering.
_INDEXES = [
    (
        "ix_security_alerts_source_severity_created",
        "security_alerts",
        ["source", "severity", sa.text("created_at DESC")],
    ),
    (
        "ix_security_alerts_status_created",
        "security_alerts",
        ["status", sa.text("created_at DESC")],
    ),
    (
        "ix_security_alerts_tenant_status_created",
        "security_alerts",
        ["tenant_id", "status", sa.text("created_at DESC")],
    ),
    (
        "ix_security_alerts_assigned_status",
        "security_alerts",
        ["assigned_to", "status"],
    ),
    (
        "ix_security_alerts_agent_name_created",
        "security_alerts",
        ["agent_name", sa.text("created_at DESC")],
    ),
    (
        "ix_security_alerts_source_ip_created",
        "security_alerts",
        ["source_ip", sa.text("created_at DESC")],
    ),
    (
        "idx_playbook_run_trigger_time",
        "playbook_runs",
        ["trigger_id", sa.text("started_at DESC")],
    ),
    (
        "idx_playbook_run_status_started",
        "playbook_runs",
        ["status", sa.text("started_at DESC")],
    ),
    (
        "idx_playbook_run_definition_started",
        "playbook_runs",
        ["definition_id", sa.text("started_at DESC")],
    ),
    (
        "idx_audit_log_user_action",
        "audit_logs",
        ["user_id", "action", sa.text("created_at DESC")],
    ),
    (
        "idx_audit_log_resource",
        "audit_logs",
        ["target_type", "target_id", sa.text("created_at DESC")],
    ),
    (
        "idx_ioc_hits_type_value",
        "ioc_hits",
        ["ioc_type", "ioc_value", sa.text("created_at DESC")],
    ),
    (
        "idx_ioc_hits_asset",
        "ioc_hits",
        ["asset_id", sa.text("created_at DESC")],
    ),
]


def upgrade() -> None:
    for name, table, columns in _INDEXES:
        op.create_index(name, table, columns)


def downgrade() -> None:
    for name, table, _columns in reversed(_INDEXES):
        op.drop_index(name, table_name=table)
