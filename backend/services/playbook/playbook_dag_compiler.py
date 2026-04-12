"""DAG Playbook Compiler - validates and compiles DAG definitions."""

from collections import defaultdict, deque
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger

logger = get_logger(__name__)


class DAGValidationError(Exception):
    """Raised when DAG validation fails."""

    pass


class DAGCompiler:
    """Compiles and validates DAG playbook definitions."""

    # Available node types
    NODE_TYPES = {
        "ti_lookup_otx",
        "extract_iocs",
        "parse_json",
        "decision",
        "sleep",
        "http_request",
        "asset_enrich",
        "risk_score",
        "action_plan",
        "timeline_build",
        "slack_notify",
        "normalize",
        "generate_report",
        "human_approval",
    }

    @staticmethod
    async def validate_and_compile(
        dag_json: dict[str, Any],
        session: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """Validate and compile a DAG definition."""
        if "nodes" not in dag_json:
            raise DAGValidationError("DAG must contain 'nodes' array")
        if "edges" not in dag_json:
            raise DAGValidationError("DAG must contain 'edges' array")

        nodes = dag_json["nodes"]
        edges = dag_json["edges"]

        # Validate node uniqueness
        node_ids = set()
        for node in nodes:
            if "id" not in node:
                raise DAGValidationError(f"Node missing 'id': {node}")
            if node["id"] in node_ids:
                raise DAGValidationError(f"Duplicate node ID: {node['id']}")
            if "type" not in node:
                raise DAGValidationError(f"Node {node['id']} missing 'type'")
            if node["type"] not in DAGCompiler.NODE_TYPES:
                raise DAGValidationError(f"Unknown node type: {node['type']}")
            node_ids.add(node["id"])

        # Validate edge references
        node_ids_set = set(node_ids)
        for edge in edges:
            if "source" not in edge:
                raise DAGValidationError("Edge missing 'source'")
            if "target" not in edge:
                raise DAGValidationError("Edge missing 'target'")
            if edge["source"] not in node_ids_set:
                raise DAGValidationError(
                    f"Edge source node not found: {edge['source']}"
                )
            if edge["target"] not in node_ids_set:
                raise DAGValidationError(
                    f"Edge target node not found: {edge['target']}"
                )

        # Detect cycles
        cycle = DAGCompiler._detect_cycle(nodes, edges)
        if cycle:
            raise DAGValidationError(
                f"Cyclic dependency detected: {' -> '.join(cycle)}"
            )

        # Build compiled DAG
        compiled_dag = DAGCompiler._build_compiled_dag(nodes, edges)

        logger.info(f"DAG validation passed: {len(nodes)} nodes, {len(edges)} edges")
        return compiled_dag

    @staticmethod
    def _detect_cycle(
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
    ) -> list[str] | None:
        """Detect cycles in the DAG using Kahn's algorithm."""
        graph = defaultdict(list)
        in_degree = defaultdict(int)
        node_ids = {node["id"] for node in nodes}

        for node_id in node_ids:
            in_degree[node_id] = 0

        for edge in edges:
            graph[edge["source"]].append(edge["target"])
            in_degree[edge["target"]] += 1

        queue = deque([node_id for node_id in node_ids if in_degree[node_id] == 0])
        visited = 0

        while queue:
            node_id = queue.popleft()
            visited += 1
            for neighbor in graph[node_id]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if visited != len(node_ids):
            return DAGCompiler._find_cycle(graph, node_ids)
        return None

    @staticmethod
    def _find_cycle(
        graph: dict[str, list[str]],
        node_ids: set[str],
    ) -> list[str]:
        """Find and return a cycle in the graph."""
        visited = set()
        rec_stack = set()
        path = []

        def dfs(node_id: str) -> list[str] | None:
            visited.add(node_id)
            rec_stack.add(node_id)
            path.append(node_id)

            for neighbor in graph[node_id]:
                if neighbor not in visited:
                    result = dfs(neighbor)
                    if result:
                        return result
                elif neighbor in rec_stack:
                    cycle_start = path.index(neighbor)
                    return path[cycle_start:] + [neighbor]

            path.pop()
            rec_stack.remove(node_id)
            return None

        for node_id in node_ids:
            if node_id not in visited:
                result = dfs(node_id)
                if result:
                    return result
        return []

    @staticmethod
    def _build_compiled_dag(
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Build compiled DAG with metadata."""
        outgoing = defaultdict(list)
        incoming = defaultdict(list)

        for edge in edges:
            outgoing[edge["source"]].append(
                {
                    "target": edge["target"],
                    "condition": edge.get("condition"),
                }
            )
            incoming[edge["target"]].append(
                {
                    "source": edge["source"],
                    "condition": edge.get("condition"),
                }
            )

        node_ids = {node["id"] for node in nodes}
        root_nodes = [nid for nid in node_ids if not incoming[nid]]
        leaf_nodes = [nid for nid in node_ids if not outgoing[nid]]
        nodes_by_id = {node["id"]: node for node in nodes}

        return {
            "nodes": nodes_by_id,
            "edges": edges,
            "outgoing": dict(outgoing),
            "incoming": dict(incoming),
            "root_nodes": root_nodes,
            "leaf_nodes": leaf_nodes,
            "node_count": len(nodes),
            "edge_count": len(edges),
        }
