"""Unit tests for PlaybookDAGEngine."""

import pytest
from services.playbook_dag_engine import (
    PlaybookDAGEngine,
    ExecutionContext,
    DAGNodeSpec,
    NodeType,
    NodeStatus,
)


class TestNodeType:
    """Tests for NodeType enum."""

    def test_node_type_values(self):
        """Test that NodeType has expected values."""
        assert NodeType.ACTION == "action"
        assert NodeType.CONDITION == "condition"
        assert NodeType.APPROVAL == "approval"
        assert NodeType.ROLLBACK == "rollback"

    def test_node_type_string_conversion(self):
        """Test NodeType string conversion."""
        assert str(NodeType.ACTION) == "action"
        assert NodeType.CONDITION.value == "condition"


class TestNodeStatus:
    """Tests for NodeStatus enum."""

    def test_node_status_values(self):
        """Test that NodeStatus has expected values."""
        assert NodeStatus.PENDING == "pending"
        assert NodeStatus.RUNNING == "running"
        assert NodeStatus.SUCCESS == "success"
        assert NodeStatus.FAILED == "failed"
        assert NodeStatus.SKIPPED == "skipped"
        assert NodeStatus.WAITING_APPROVAL == "waiting_approval"
        assert NodeStatus.ROLLING_BACK == "rolling_back"
        assert NodeStatus.ROLLED_BACK == "rolled_back"


class TestExecutionContext:
    """Tests for ExecutionContext dataclass."""

    def test_execution_context_creation(self):
        """Test creating ExecutionContext."""
        ctx = ExecutionContext(
            run_id="run-123",
            tenant_id="tenant-456",
        )
        
        assert ctx.run_id == "run-123"
        assert ctx.tenant_id == "tenant-456"
        assert ctx.variables == {}
        assert ctx.node_status == {}
        assert ctx.node_outputs == {}

    def test_execution_context_with_variables(self):
        """Test ExecutionContext with variables."""
        ctx = ExecutionContext(
            run_id="run-123",
            tenant_id="tenant-456",
            variables={"key": "value", "count": 42},
        )
        
        assert ctx.variables["key"] == "value"
        assert ctx.variables["count"] == 42

    def test_execution_context_with_node_status(self):
        """Test ExecutionContext with node status."""
        ctx = ExecutionContext(
            run_id="run-123",
            tenant_id="tenant-456",
            node_status={"node-1": NodeStatus.SUCCESS, "node-2": NodeStatus.RUNNING},
        )
        
        assert ctx.node_status["node-1"] == NodeStatus.SUCCESS
        assert ctx.node_status["node-2"] == NodeStatus.RUNNING


class TestDAGNodeSpec:
    """Tests for DAGNodeSpec dataclass."""

    def test_dag_node_spec_basic(self):
        """Test creating basic DAGNodeSpec."""
        spec = DAGNodeSpec(
            id="node-1",
            node_type=NodeType.ACTION,
        )
        
        assert spec.id == "node-1"
        assert spec.node_type == NodeType.ACTION
        assert spec.depends_on == []
        assert spec.on_success == []
        assert spec.on_failure == []
        assert spec.rollback_node_id is None

    def test_dag_node_spec_with_dependencies(self):
        """Test DAGNodeSpec with dependencies."""
        spec = DAGNodeSpec(
            id="node-2",
            node_type=NodeType.ACTION,
            depends_on=["node-1"],
            on_success=["node-3"],
            on_failure=["rollback-1"],
            rollback_node_id="rollback-1",
        )
        
        assert spec.depends_on == ["node-1"]
        assert spec.on_success == ["node-3"]
        assert spec.on_failure == ["rollback-1"]
        assert spec.rollback_node_id == "rollback-1"

    def test_dag_node_spec_approval_type(self):
        """Test DAGNodeSpec with approval type."""
        spec = DAGNodeSpec(
            id="approval-1",
            node_type=NodeType.APPROVAL,
            depends_on=["action-1"],
        )
        
        assert spec.node_type == NodeType.APPROVAL


class TestPlaybookDAGEngine:
    """Tests for PlaybookDAGEngine."""

    @pytest.fixture
    def engine(self):
        """Create engine instance."""
        return PlaybookDAGEngine()

    @pytest.fixture
    def context(self):
        """Create execution context."""
        return ExecutionContext(
            run_id="test-run",
            tenant_id="test-tenant",
        )

    @pytest.mark.asyncio
    async def test_evaluate_next_nodes_no_dependencies(self, engine, context):
        """Test evaluating nodes with no dependencies."""
        nodes = {
            "start": DAGNodeSpec(id="start", node_type=NodeType.ACTION),
            "end": DAGNodeSpec(id="end", node_type=NodeType.ACTION, depends_on=["start"]),
        }
        
        ready = await engine.evaluate_next_nodes(context, nodes)
        
        assert "start" in ready
        assert "end" not in ready

    @pytest.mark.asyncio
    async def test_evaluate_next_nodes_with_completed_deps(self, engine, context):
        """Test evaluating nodes with completed dependencies."""
        context.node_status["start"] = NodeStatus.SUCCESS
        
        nodes = {
            "start": DAGNodeSpec(id="start", node_type=NodeType.ACTION),
            "middle": DAGNodeSpec(id="middle", node_type=NodeType.ACTION, depends_on=["start"]),
            "end": DAGNodeSpec(id="end", node_type=NodeType.ACTION, depends_on=["middle"]),
        }
        
        ready = await engine.evaluate_next_nodes(context, nodes)
        
        assert "middle" in ready
        assert "end" not in ready

    @pytest.mark.asyncio
    async def test_evaluate_next_nodes_multiple_deps(self, engine, context):
        """Test evaluating nodes with multiple dependencies."""
        context.node_status["node-1"] = NodeStatus.SUCCESS
        context.node_status["node-2"] = NodeStatus.SUCCESS
        
        nodes = {
            "node-1": DAGNodeSpec(id="node-1", node_type=NodeType.ACTION),
            "node-2": DAGNodeSpec(id="node-2", node_type=NodeType.ACTION),
            "merge": DAGNodeSpec(
                id="merge",
                node_type=NodeType.ACTION,
                depends_on=["node-1", "node-2"],
            ),
        }
        
        ready = await engine.evaluate_next_nodes(context, nodes)
        
        assert "merge" in ready

    @pytest.mark.asyncio
    async def test_evaluate_next_nodes_partial_deps(self, engine, context):
        """Test evaluating nodes with partial dependencies completed."""
        context.node_status["node-1"] = NodeStatus.SUCCESS
        context.node_status["node-2"] = NodeStatus.RUNNING
        
        nodes = {
            "node-1": DAGNodeSpec(id="node-1", node_type=NodeType.ACTION),
            "node-2": DAGNodeSpec(id="node-2", node_type=NodeType.ACTION),
            "merge": DAGNodeSpec(
                id="merge",
                node_type=NodeType.ACTION,
                depends_on=["node-1", "node-2"],
            ),
        }
        
        ready = await engine.evaluate_next_nodes(context, nodes)
        
        assert "merge" not in ready

    @pytest.mark.asyncio
    async def test_evaluate_next_nodes_already_processed(self, engine, context):
        """Test that already processed nodes are not returned."""
        context.node_status["start"] = NodeStatus.SUCCESS
        context.node_status["middle"] = NodeStatus.FAILED
        
        nodes = {
            "start": DAGNodeSpec(id="start", node_type=NodeType.ACTION),
            "middle": DAGNodeSpec(id="middle", node_type=NodeType.ACTION, depends_on=["start"]),
        }
        
        ready = await engine.evaluate_next_nodes(context, nodes)
        
        assert "start" not in ready
        assert "middle" not in ready

    @pytest.mark.asyncio
    async def test_mark_failure_basic(self, engine, context):
        """Test marking node as failed."""
        nodes = {
            "action-1": DAGNodeSpec(id="action-1", node_type=NodeType.ACTION),
        }
        
        rollback_nodes = await engine.mark_failure(context, "action-1", nodes)
        
        assert context.node_status["action-1"] == NodeStatus.FAILED
        assert rollback_nodes == []

    @pytest.mark.asyncio
    async def test_mark_failure_with_rollback(self, engine, context):
        """Test marking failure with rollback node."""
        nodes = {
            "action-1": DAGNodeSpec(
                id="action-1",
                node_type=NodeType.ACTION,
                rollback_node_id="rollback-1",
            ),
            "rollback-1": DAGNodeSpec(id="rollback-1", node_type=NodeType.ROLLBACK),
        }
        
        rollback_nodes = await engine.mark_failure(context, "action-1", nodes)
        
        assert context.node_status["action-1"] == NodeStatus.FAILED
        assert "rollback-1" in rollback_nodes

    @pytest.mark.asyncio
    async def test_mark_failure_with_on_failure_hooks(self, engine, context):
        """Test marking failure with on_failure hooks."""
        nodes = {
            "action-1": DAGNodeSpec(
                id="action-1",
                node_type=NodeType.ACTION,
                on_failure=["notify-1", "cleanup-1"],
            ),
        }
        
        rollback_nodes = await engine.mark_failure(context, "action-1", nodes)
        
        assert "notify-1" in rollback_nodes
        assert "cleanup-1" in rollback_nodes

    @pytest.mark.asyncio
    async def test_mark_failure_with_rollback_and_hooks(self, engine, context):
        """Test marking failure with both rollback and hooks."""
        nodes = {
            "action-1": DAGNodeSpec(
                id="action-1",
                node_type=NodeType.ACTION,
                rollback_node_id="rollback-1",
                on_failure=["notify-1"],
            ),
        }
        
        rollback_nodes = await engine.mark_failure(context, "action-1", nodes)
        
        assert "rollback-1" in rollback_nodes
        assert "notify-1" in rollback_nodes

    @pytest.mark.asyncio
    async def test_complex_dag_workflow(self, engine, context):
        """Test complex DAG workflow execution."""
        nodes = {
            "start": DAGNodeSpec(id="start", node_type=NodeType.ACTION),
            "parallel-1": DAGNodeSpec(
                id="parallel-1",
                node_type=NodeType.ACTION,
                depends_on=["start"],
            ),
            "parallel-2": DAGNodeSpec(
                id="parallel-2",
                node_type=NodeType.ACTION,
                depends_on=["start"],
            ),
            "merge": DAGNodeSpec(
                id="merge",
                node_type=NodeType.ACTION,
                depends_on=["parallel-1", "parallel-2"],
            ),
            "end": DAGNodeSpec(
                id="end",
                node_type=NodeType.ACTION,
                depends_on=["merge"],
            ),
        }
        
        ready = await engine.evaluate_next_nodes(context, nodes)
        assert ready == ["start"]
        
        context.node_status["start"] = NodeStatus.SUCCESS
        ready = await engine.evaluate_next_nodes(context, nodes)
        assert set(ready) == {"parallel-1", "parallel-2"}
        
        context.node_status["parallel-1"] = NodeStatus.SUCCESS
        context.node_status["parallel-2"] = NodeStatus.SUCCESS
        ready = await engine.evaluate_next_nodes(context, nodes)
        assert ready == ["merge"]
        
        context.node_status["merge"] = NodeStatus.SUCCESS
        ready = await engine.evaluate_next_nodes(context, nodes)
        assert ready == ["end"]

    @pytest.mark.asyncio
    async def test_dag_with_approval_node(self, engine, context):
        """Test DAG with approval node."""
        nodes = {
            "start": DAGNodeSpec(id="start", node_type=NodeType.ACTION),
            "approval": DAGNodeSpec(
                id="approval",
                node_type=NodeType.APPROVAL,
                depends_on=["start"],
            ),
            "end": DAGNodeSpec(
                id="end",
                node_type=NodeType.ACTION,
                depends_on=["approval"],
            ),
        }
        
        ready = await engine.evaluate_next_nodes(context, nodes)
        assert ready == ["start"]
        
        context.node_status["start"] = NodeStatus.SUCCESS
        ready = await engine.evaluate_next_nodes(context, nodes)
        assert ready == ["approval"]

    @pytest.mark.asyncio
    async def test_dag_with_condition_node(self, engine, context):
        """Test DAG with condition node."""
        nodes = {
            "start": DAGNodeSpec(id="start", node_type=NodeType.ACTION),
            "condition": DAGNodeSpec(
                id="condition",
                node_type=NodeType.CONDITION,
                depends_on=["start"],
                on_success=["action-true"],
                on_failure=["action-false"],
            ),
            "action-true": DAGNodeSpec(
                id="action-true",
                node_type=NodeType.ACTION,
                depends_on=["condition"],
            ),
            "action-false": DAGNodeSpec(
                id="action-false",
                node_type=NodeType.ACTION,
                depends_on=["condition"],
            ),
        }
        
        ready = await engine.evaluate_next_nodes(context, nodes)
        assert ready == ["start"]
        
        context.node_status["start"] = NodeStatus.SUCCESS
        ready = await engine.evaluate_next_nodes(context, nodes)
        assert ready == ["condition"]
