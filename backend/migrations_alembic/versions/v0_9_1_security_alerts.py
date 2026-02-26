"""v0.9.1: Add security_alerts table for external alert ingestion

Revision ID: v0_9_1_security_alerts
Create Date: 2026-02-24
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

# revision identifiers, used by Alembic.
revision = 'v0_9_1_security_alerts'
down_revision = 'v0_9_0_performance_indexes'
branch_labels = None
depends_on = None


def upgrade():
    """Create security_alerts table."""
    op.create_table(
        'security_alerts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=False),
        sa.Column('external_event_id', sa.String(length=255), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('source_ip', sa.String(length=50), nullable=True),
        sa.Column('destination_ip', sa.String(length=50), nullable=True),
        sa.Column('protocol', sa.String(length=20), nullable=True),
        sa.Column('agent_name', sa.String(length=255), nullable=True),
        sa.Column('agent_id', sa.String(length=50), nullable=True),
        sa.Column('agent_ip', sa.String(length=50), nullable=True),
        sa.Column('rule_id', sa.String(length=100), nullable=True),
        sa.Column('rule_level', sa.Integer(), nullable=True),
        sa.Column('rule_groups', sa.Text(), nullable=True),
        sa.Column('rule_mitre', sa.Text(), nullable=True),
        sa.Column('full_log', sa.Text(), nullable=True),
        sa.Column('location', sa.String(length=500), nullable=True),
        sa.Column('geoip', JSON(), nullable=True),
        sa.Column('raw_data', JSON(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='open'),
        sa.Column('assigned_to', sa.String(length=255), nullable=True),
        sa.Column('resolution', sa.Text(), nullable=True),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('closed_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('event_timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for common queries
    op.create_index('ix_security_alerts_id', 'security_alerts', ['id'], unique=False)
    op.create_index('ix_security_alerts_source', 'security_alerts', ['source'], unique=False)
    op.create_index('ix_security_alerts_external_event_id', 'security_alerts', ['external_event_id'], unique=False)
    op.create_index('ix_security_alerts_event_type', 'security_alerts', ['event_type'], unique=False)
    op.create_index('ix_security_alerts_severity', 'security_alerts', ['severity'], unique=False)
    op.create_index('ix_security_alerts_status', 'security_alerts', ['status'], unique=False)
    op.create_index('ix_security_alerts_source_ip', 'security_alerts', ['source_ip'], unique=False)
    op.create_index('ix_security_alerts_agent_name', 'security_alerts', ['agent_name'], unique=False)
    op.create_index('ix_security_alerts_created_at', 'security_alerts', ['created_at'], unique=False)
    op.create_index('ix_security_alerts_event_timestamp', 'security_alerts', ['event_timestamp'], unique=False)

    # Composite index for deduplication
    op.create_index(
        'ix_security_alerts_source_event_id',
        'security_alerts',
        ['source', 'external_event_id'],
        unique=True
    )

    # Composite index for common filter combinations
    op.create_index(
        'ix_security_alerts_severity_status',
        'security_alerts',
        ['severity', 'status'],
        unique=False
    )


def downgrade():
    """Drop security_alerts table."""
    # Drop indexes
    op.drop_index('ix_security_alerts_severity_status', table_name='security_alerts')
    op.drop_index('ix_security_alerts_source_event_id', table_name='security_alerts')
    op.drop_index('ix_security_alerts_event_timestamp', table_name='security_alerts')
    op.drop_index('ix_security_alerts_created_at', table_name='security_alerts')
    op.drop_index('ix_security_alerts_agent_name', table_name='security_alerts')
    op.drop_index('ix_security_alerts_source_ip', table_name='security_alerts')
    op.drop_index('ix_security_alerts_status', table_name='security_alerts')
    op.drop_index('ix_security_alerts_severity', table_name='security_alerts')
    op.drop_index('ix_security_alerts_event_type', table_name='security_alerts')
    op.drop_index('ix_security_alerts_external_event_id', table_name='security_alerts')
    op.drop_index('ix_security_alerts_source', table_name='security_alerts')
    op.drop_index('ix_security_alerts_id', table_name='security_alerts')

    # Drop table
    op.drop_table('security_alerts')
