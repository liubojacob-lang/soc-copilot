-- SOC Copilot v0.7 - DAG-Based Playbook Engine
-- Migration: Add support for DAG-based playbook execution
-- Date: 2025-02-08

-- ============================================
-- Table: playbook_definitions
-- Stores DAG-based playbook definitions
-- ============================================
CREATE TABLE IF NOT EXISTS playbook_definitions (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    version TEXT DEFAULT '1.0.0',
    definition_json TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_playbook_definitions_name ON playbook_definitions(name);
CREATE INDEX IF NOT EXISTS idx_playbook_definitions_created_by ON playbook_definitions(created_by);
CREATE INDEX IF NOT EXISTS idx_playbook_definitions_is_active ON playbook_definitions(is_active);

-- ============================================
-- Table: playbook_nodes
-- Stores node definitions within a playbook
-- ============================================
CREATE TABLE IF NOT EXISTS playbook_nodes (
    id TEXT PRIMARY KEY,
    definition_id TEXT NOT NULL,
    node_id TEXT NOT NULL,
    step_id TEXT NOT NULL,
    name TEXT NOT NULL,
    retry_policy_json TEXT,
    timeout_seconds INTEGER DEFAULT 300,
    position_x REAL,
    position_y REAL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (definition_id) REFERENCES playbook_definitions(id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_playbook_nodes_definition_node ON playbook_nodes(definition_id, node_id);
CREATE INDEX IF NOT EXISTS idx_playbook_nodes_step_id ON playbook_nodes(step_id);

-- ============================================
-- Table: playbook_edges
-- Stores edges (connections) between nodes
-- ============================================
CREATE TABLE IF NOT EXISTS playbook_edges (
    id TEXT PRIMARY KEY,
    definition_id TEXT NOT NULL,
    source_node_id TEXT NOT NULL,
    target_node_id TEXT NOT NULL,
    condition_expression TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (definition_id) REFERENCES playbook_definitions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_playbook_edges_definition ON playbook_edges(definition_id);
CREATE INDEX IF NOT EXISTS idx_playbook_edges_source ON playbook_edges(source_node_id);
CREATE INDEX IF NOT EXISTS idx_playbook_edges_target ON playbook_edges(target_node_id);

-- ============================================
-- Table: playbook_node_runs
-- Tracks execution of nodes within a DAG run
-- ============================================
CREATE TABLE IF NOT EXISTS playbook_node_runs (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    node_id TEXT NOT NULL,
    step_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    duration_ms INTEGER,
    input_json TEXT DEFAULT '{}',
    output_json TEXT DEFAULT '{}',
    error_message TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES playbook_runs(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_playbook_node_runs_run_id ON playbook_node_runs(run_id);
CREATE INDEX IF NOT EXISTS idx_playbook_node_runs_node_id ON playbook_node_runs(node_id);
CREATE INDEX IF NOT EXISTS idx_playbook_node_runs_status ON playbook_node_runs(status);

-- ============================================
-- Table: playbook_node_attempts
-- Tracks retry attempts for failed nodes
-- ============================================
CREATE TABLE IF NOT EXISTS playbook_node_attempts (
    id TEXT PRIMARY KEY,
    node_run_id TEXT NOT NULL,
    attempt_number INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    error_message TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (node_run_id) REFERENCES playbook_node_runs(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_playbook_node_attempts_node_run ON playbook_node_attempts(node_run_id);

-- ============================================
-- Table: playbook_triggers
-- Stores trigger configurations for playbooks
-- ============================================
CREATE TABLE IF NOT EXISTS playbook_triggers (
    id TEXT PRIMARY KEY,
    definition_id TEXT NOT NULL,
    type TEXT NOT NULL,
    name TEXT,
    config_json TEXT NOT NULL,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT,
    FOREIGN KEY (definition_id) REFERENCES playbook_definitions(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_playbook_triggers_definition ON playbook_triggers(definition_id);
CREATE INDEX IF NOT EXISTS idx_playbook_triggers_type ON playbook_triggers(type);
CREATE INDEX IF NOT EXISTS idx_playbook_triggers_is_active ON playbook_triggers(is_active);

-- ============================================
-- Table: playbook_approvals
-- Stores approval requests for human-in-the-loop nodes
-- ============================================
CREATE TABLE IF NOT EXISTS playbook_approvals (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    node_id TEXT NOT NULL,
    requested_by TEXT NOT NULL,
    requested_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    approved_by TEXT,
    approved_at TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'pending',
    comment TEXT,
    expires_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES playbook_runs(id) ON DELETE CASCADE,
    FOREIGN KEY (requested_by) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (approved_by) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_playbook_approvals_run_id ON playbook_approvals(run_id);
CREATE INDEX IF NOT EXISTS idx_playbook_approvals_status ON playbook_approvals(status);
CREATE INDEX IF NOT EXISTS idx_playbook_approvals_requested_by ON playbook_approvals(requested_by);

-- ============================================
-- Add columns to playbook_runs for DAG support
-- ============================================
ALTER TABLE playbook_runs ADD COLUMN execution_mode TEXT DEFAULT 'linear';
ALTER TABLE playbook_runs ADD COLUMN definition_id TEXT;
ALTER TABLE playbook_runs ADD COLUMN idempotency_key TEXT;
ALTER TABLE playbook_runs ADD COLUMN parent_run_id TEXT;
ALTER TABLE playbook_runs ADD COLUMN trigger_source TEXT DEFAULT 'manual';

CREATE INDEX IF NOT EXISTS idx_playbook_runs_execution_mode ON playbook_runs(execution_mode);
CREATE INDEX IF NOT EXISTS idx_playbook_runs_definition_id ON playbook_runs(definition_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_playbook_runs_idempotency_key ON playbook_runs(idempotency_key);
CREATE INDEX IF NOT EXISTS idx_playbook_runs_parent_run_id ON playbook_runs(parent_run_id);
CREATE INDEX IF NOT EXISTS idx_playbook_runs_trigger_source ON playbook_runs(trigger_source);

-- ============================================
-- Insert sample DAG definition for testing
-- ============================================
INSERT INTO playbook_definitions (
    id, name, description, version, definition_json, created_by
) VALUES (
    'demo-parallel-analysis',
    'Parallel Threat Analysis',
    'Demo DAG playbook with parallel TI lookup and asset enrichment',
    '1.0.0',
    '{"nodes": [{"id": "extract", "step_id": "ioc_extract", "name": "Extract IOCs"}, {"id": "ti_lookup", "step_id": "ti_lookup_otx", "name": "OTX Lookup"}, {"id": "enrich", "step_id": "asset_enrich", "name": "Enrich Assets"}, {"id": "score", "step_id": "risk_score", "name": "Risk Score"}], "edges": [{"source": "extract", "target": "ti_lookup"}, {"source": "extract", "target": "enrich"}, {"source": "ti_lookup", "target": "score"}, {"source": "enrich", "target": "score"}]}',
    'system'
);

-- ============================================
-- Migration complete
-- ============================================
