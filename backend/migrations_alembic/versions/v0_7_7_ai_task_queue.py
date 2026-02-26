"""v0.7.7 AI Task Queue

Revision ID: v0_7_7_ai_task_queue
Revises: v0_7_6
Create Date: 2026-02-14

Adds support for background AI task processing with:
- Task queue table for async AI operations
- Status tracking (pending, processing, completed, failed, timeout)
- Retry support and priority queue
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'v0_7_7_ai_task_queue'
down_revision = 'v0_7_6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create ai_tasks table
    op.create_table(
        'ai_tasks',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('task_type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        
        # Input data
        sa.Column('input_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('prompt', sa.Text(), nullable=True),
        sa.Column('model_id', sa.String(100), nullable=True),
        sa.Column('provider', sa.String(50), nullable=True),
        
        # Output data
        sa.Column('result', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        
        # Timing
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('timeout_seconds', sa.Integer, server_default='300'),
        
        # Ownership
        sa.Column('user_id', sa.String(36), nullable=True),
        sa.Column('request_id', sa.String(36), nullable=True),
        
        # Retry info
        sa.Column('retry_count', sa.Integer, server_default='0'),
        sa.Column('max_retries', sa.Integer, server_default='2'),
        
        # Priority
        sa.Column('priority', sa.Integer, server_default='0'),
    )
    
    # Create indexes for efficient querying
    op.create_index('ix_ai_tasks_task_type', 'ai_tasks', ['task_type'])
    op.create_index('ix_ai_tasks_status', 'ai_tasks', ['status'])
    op.create_index('ix_ai_tasks_user_id', 'ai_tasks', ['user_id'])
    op.create_index('ix_ai_tasks_created_at', 'ai_tasks', ['created_at'])
    
    # Composite index for common query patterns
    op.create_index(
        'ix_ai_tasks_status_priority_created',
        'ai_tasks',
        ['status', 'priority', 'created_at'],
        postgresql_where=sa.text("status IN ('pending', 'processing')"),
    )
    
    # Add comments for documentation
    op.execute("""
        COMMENT ON TABLE ai_tasks IS 'Background AI task queue for async processing';
        COMMENT ON COLUMN ai_tasks.task_type IS 'Type of AI task: alert_analysis, timeline_analysis, report_generation, chat_completion, ioc_analysis';
        COMMENT ON COLUMN ai_tasks.status IS 'Task status: pending, processing, completed, failed, timeout';
        COMMENT ON COLUMN ai_tasks.priority IS 'Task priority (higher = more urgent, 0-10)';
        COMMENT ON COLUMN ai_tasks.timeout_seconds IS 'Maximum execution time before timeout';
    """)


def downgrade() -> None:
    op.drop_index('ix_ai_tasks_status_priority_created', table_name='ai_tasks')
    op.drop_index('ix_ai_tasks_created_at', table_name='ai_tasks')
    op.drop_index('ix_ai_tasks_user_id', table_name='ai_tasks')
    op.drop_index('ix_ai_tasks_status', table_name='ai_tasks')
    op.drop_index('ix_ai_tasks_task_type', table_name='ai_tasks')
    op.drop_table('ai_tasks')
