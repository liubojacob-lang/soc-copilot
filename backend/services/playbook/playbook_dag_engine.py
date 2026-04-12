"""Enhanced DAG playbook orchestration facade.

Provides explicit node types, execution context, branch/failure handling and rollback hooks
on top of the existing playbook DAG engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class NodeType(str, Enum):
    ACTION = "action"
    CONDITION = "condition"
    APPROVAL = "approval"
    ROLLBACK = "rollback"


class NodeStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    WAITING_APPROVAL = "waiting_approval"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"


@dataclass(slots=True)
class ExecutionContext:
    run_id: str
    tenant_id: str
    variables: dict[str, Any] = field(default_factory=dict)
    node_status: dict[str, NodeStatus] = field(default_factory=dict)
    node_outputs: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DAGNodeSpec:
    id: str
    node_type: NodeType
    depends_on: list[str] = field(default_factory=list)
    on_success: list[str] = field(default_factory=list)
    on_failure: list[str] = field(default_factory=list)
    rollback_node_id: str | None = None


class PlaybookDAGEngine:
    """High-level orchestration semantics, compatible with existing DAG runtime."""

    async def evaluate_next_nodes(
        self, ctx: ExecutionContext, nodes: dict[str, DAGNodeSpec]
    ) -> list[str]:
        ready: list[str] = []
        for node_id, spec in nodes.items():
            if ctx.node_status.get(node_id) is not None:
                continue
            deps_ok = all(
                ctx.node_status.get(dep) == NodeStatus.SUCCESS
                for dep in spec.depends_on
            )
            if deps_ok:
                ready.append(node_id)
        return ready

    async def mark_failure(
        self, ctx: ExecutionContext, node_id: str, nodes: dict[str, DAGNodeSpec]
    ) -> list[str]:
        ctx.node_status[node_id] = NodeStatus.FAILED
        rollback_nodes: list[str] = []
        spec = nodes.get(node_id)
        if spec and spec.rollback_node_id:
            rollback_nodes.append(spec.rollback_node_id)
        rollback_nodes.extend(spec.on_failure if spec else [])
        return rollback_nodes
