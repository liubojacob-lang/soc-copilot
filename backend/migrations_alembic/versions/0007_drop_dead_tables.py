"""0007 — drop dead tables (T3.5 dead-code sweep)

Tables removed (all verified to have zero producers or zero readers):
- event_similarities: no writer ever existed; only the retention sweeper
  deleted from it (that sweeper path is removed with this migration).
- on_call_schedules: read by the escalation service but never written —
  the lookup could only ever return empty (stubbed accordingly).
- playbook_nodes / playbook_edges: the DAG engine stores the graph in
  playbook_definitions.definition_json; these tables were never used.

Revision ID: 0007_drop_dead_tables
Revises: 0006_constraints_indexes
"""

from alembic import op

# revision identifiers
revision = "0007_drop_dead_tables"
down_revision = "0006_constraints_indexes"
branch_labels = None
depends_on = None

_DEAD_TABLES = [
    "event_similarities",
    "on_call_schedules",
    "playbook_nodes",
    "playbook_edges",
]


def upgrade() -> None:
    for table in _DEAD_TABLES:
        op.execute(f'DROP TABLE IF EXISTS "{table}"')


def downgrade() -> None:
    # Recreate bare schemas so downgrade does not break alembic traversal.
    # Data lost by upgrade() is NOT restored (rows, if any, were orphans).
    op.execute("""
        CREATE TABLE IF NOT EXISTS event_similarities (
            id VARCHAR(36) PRIMARY KEY,
            event_id_1 VARCHAR(255) NOT NULL,
            event_id_2 VARCHAR(255) NOT NULL,
            similarity FLOAT NOT NULL,
            created_at VARCHAR(50) NOT NULL,
            ttl_seconds INTEGER
        )
        """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS on_call_schedules (
            id VARCHAR(36) PRIMARY KEY,
            user_id VARCHAR(255) NOT NULL,
            rotation_group VARCHAR(100) NOT NULL,
            start_date TIMESTAMP WITH TIME ZONE NOT NULL,
            end_date TIMESTAMP WITH TIME ZONE NOT NULL,
            is_primary BOOLEAN NOT NULL DEFAULT FALSE
        )
        """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS playbook_nodes (
            id VARCHAR(36) PRIMARY KEY,
            definition_id VARCHAR(36) NOT NULL
                REFERENCES playbook_definitions(id) ON DELETE CASCADE,
            node_id VARCHAR(100) NOT NULL,
            step_id VARCHAR(100) NOT NULL,
            name VARCHAR(200) NOT NULL,
            retry_policy_json JSON,
            timeout_seconds INTEGER DEFAULT 300,
            position_x FLOAT,
            position_y FLOAT,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL
        )
        """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS playbook_edges (
            id VARCHAR(36) PRIMARY KEY,
            definition_id VARCHAR(36) NOT NULL
                REFERENCES playbook_definitions(id) ON DELETE CASCADE,
            source_node_id VARCHAR(100) NOT NULL,
            target_node_id VARCHAR(100) NOT NULL,
            condition_expression TEXT,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL
        )
        """)
