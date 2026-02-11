"""Dify to SOC Copilot DAG adapter.

This module provides conversion between Dify workflow format
and SOC Copilot DAG format for bidirectional integration.
"""

import logging
from typing import Any, Dict, List, Optional
from services.dify_service import DifyWorkflow
from core.logger import get_logger

logger = get_logger(__name__)


class DifyDAGAdapter:
    """Adapter for converting between Dify and SOC Copilot DAG formats."""

    # Mapping of Dify node types to SOC Copilot step types
    NODE_TYPE_MAPPING = {
        "start": "manual_trigger",
        "end": "end",
        "llm": "ai_analysis",
        "code": "script_execution",
        "if-else": "decision",
        "variable-assigner": "set_variable",
        "parameter-extractor": "extract_data",
        "iteration": "loop",
        "parallel": "parallel",
        "merge": "merge",
        "http-request": "http_request",
        "tool": "external_tool",
        "question-classifier": "classification",
        "knowledge-retrieval": "ti_lookup",
        "template-transform": "data_transform",
    }

    # Mapping of SOC Copilot step types to Dify node types
    STEP_TYPE_MAPPING = {v: k for k, v in NODE_TYPE_MAPPING.items()}

    def dify_to_dag(self, workflow: DifyWorkflow) -> Dict[str, Any]:
        """Convert Dify workflow to SOC Copilot DAG format.

        Args:
            workflow: Dify workflow model

        Returns:
            SOC Copilot DAG definition
        """
        graph = workflow.graph
        nodes = graph.get("nodes", [])
        edges_data = graph.get("edges", [])

        # Convert nodes
        dag_nodes = []
        for node in nodes:
            dag_node = {
                "id": node.get("id", ""),
                "step_id": self._map_dify_node_type(node.get("type", "")),
                "name": node.get("data", {}).get("title", node.get("id", "")),
                "position_x": node.get("position", {}).get("x", 0),
                "position_y": node.get("position", {}).get("y", 0),
                "config": self._extract_node_config(node),
                "inputs_template": self._extract_node_inputs(node),
                "outputs_mapping": self._extract_node_outputs(node),
            }
            dag_nodes.append(dag_node)

        # Convert edges
        dag_edges = []
        for edge in edges_data:
            dag_edge = {
                "source": edge.get("source", ""),
                "target": edge.get("target", ""),
                "condition": edge.get("data", {}).get("type", ""),
            }
            dag_edges.append(dag_edge)

        # Extract global variables from environment_variables
        global_context = {}
        for var in workflow.environment_variables:
            var_name = var.get("name", "")
            var_value = var.get("value", "")
            if var_name:
                global_context[var_name] = var_value

        return {
            "nodes": dag_nodes,
            "edges": dag_edges,
            "global_context": global_context,
            "metadata": {
                "dify_app_id": workflow.app_id,
                "dify_version": workflow.version,
                "imported_from": "dify",
            },
        }

    def dag_to_dify(self, dag_definition: Dict[str, Any], name: str, description: str = "") -> DifyWorkflow:
        """Convert SOC Copilot DAG to Dify workflow format.

        Args:
            dag_definition: SOC Copilot DAG definition
            name: Workflow name
            description: Workflow description

        Returns:
            Dify workflow model
        """
        nodes = dag_definition.get("nodes", [])
        edges_data = dag_definition.get("edges", [])
        global_context = dag_definition.get("global_context", {})

        # Convert nodes to Dify format
        dify_nodes = []
        for node in nodes:
            dify_node = {
                "id": node.get("id", ""),
                "type": self._map_step_type_to_dify(node.get("step_id", "")),
                "position": {
                    "x": node.get("position_x", 0),
                    "y": node.get("position_y", 0),
                },
                "data": self._build_dify_node_data(node),
            }
            dify_nodes.append(dify_node)

        # Convert edges to Dify format
        dify_edges = []
        for edge in edges_data:
            dify_edge = {
                "id": f"{edge.get('source', '')}-{edge.get('target', '')}",
                "source": edge.get("source", ""),
                "target": edge.get("target", ""),
                "type": "custom",
                "data": {
                    "type": edge.get("condition", "default"),
                    "title": edge.get("condition", "default"),
                },
            }
            dify_edges.append(dify_edge)

        # Convert global_context to environment_variables
        environment_variables = [
            {"name": k, "value": v, "value_type": "string"}
            for k, v in global_context.items()
        ]

        # Build Dify graph
        graph = {
            "nodes": dify_nodes,
            "edges": dify_edges,
        }

        return DifyWorkflow(
            name=name,
            description=description,
            mode="workflow",
            version="1.0.0",
            graph=graph,
            environment_variables=environment_variables,
            conversation_variables=[],
        )

    def _map_dify_node_type(self, dify_type: str) -> str:
        """Map Dify node type to SOC Copilot step type.

        Args:
            dify_type: Dify node type

        Returns:
            SOC Copilot step type
        """
        return self.NODE_TYPE_MAPPING.get(dify_type, dify_type)

    def _map_step_type_to_dify(self, step_type: str) -> str:
        """Map SOC Copilot step type to Dify node type.

        Args:
            step_type: SOC Copilot step type

        Returns:
            Dify node type
        """
        return self.STEP_TYPE_MAPPING.get(step_type, "code")

    def _extract_node_config(self, node: Dict[str, Any]) -> Dict[str, Any]:
        """Extract configuration from Dify node.

        Args:
            node: Dify node data

        Returns:
            Node configuration
        """
        node_type = node.get("type", "")
        node_data = node.get("data", {})

        config = {}

        if node_type == "llm":
            config["model"] = node_data.get("model", {}).get("provider", "")
            config["prompt_template"] = node_data.get("prompt_template", [])

        elif node_type == "code":
            config["code"] = node_data.get("code", "")
            config["language"] = node_data.get("language", "python3")

        elif node_type == "http-request":
            config["method"] = node_data.get("method", "GET")
            config["url"] = node_data.get("url", "")
            config["headers"] = node_data.get("headers", {})

        return config

    def _extract_node_inputs(self, node: Dict[str, Any]) -> Dict[str, Any]:
        """Extract input template from Dify node.

        Args:
            node: Dify node data

        Returns:
            Input template for SOC Copilot
        """
        node_data = node.get("data", {})
        node_type = node.get("type", "")

        inputs = {}

        # Extract variable selectors (Dify uses {{variable}} syntax)
        if node_type == "llm":
            inputs["prompt"] = node_data.get("prompt_template", [])
            inputs["variables"] = node_data.get("variables", [])
        elif node_type == "code":
            inputs["code"] = node_data.get("code", "")
            inputs["variables"] = node_data.get("variables", [])

        return inputs

    def _extract_node_outputs(self, node: Dict[str, Any]) -> Dict[str, str]:
        """Extract output mapping from Dify node.

        Args:
            node: Dify node data

        Returns:
            Output variable mapping
        """
        node_data = node.get("data", "")
        node_type = node.get("type", "")

        outputs = {}

        if node_type == "variable-assigner":
            var_name = node_data.get("variable", "")
            if var_name:
                outputs["result"] = f"{{context.{var_name}}}"

        elif node_type == "code":
            outputs["output"] = "{{node.output}}"

        return outputs

    def _build_dify_node_data(self, node: Dict[str, Any]) -> Dict[str, Any]:
        """Build Dify node data from SOC Copilot node.

        Args:
            node: SOC Copilot node definition

        Returns:
            Dify node data
        """
        step_id = node.get("step_id", "")
        name = node.get("name", "")
        config = node.get("config", {})
        inputs = node.get("inputs_template", {})

        data = {
            "title": name,
            "type": step_id,
        }

        # Build based on step type
        if step_id == "llm" or step_id == "ai_analysis":
            data["model"] = {"provider": config.get("model", "openai")}
            data["prompt_template"] = inputs.get("prompt", "")

        elif step_id == "script_execution" or step_id == "code":
            data["code"] = inputs.get("code", "")
            data["language"] = config.get("language", "python3")

        elif step_id == "http_request":
            data["method"] = config.get("method", "GET")
            data["url"] = inputs.get("url", "")
            data["headers"] = inputs.get("headers", {})

        elif step_id == "decision":
            data["conditions"] = inputs.get("conditions", [])

        return data


class DifyExecutionBridge:
    """Bridge for executing SOC Copilot DAG through Dify engine."""

    def __init__(self, dify_client):
        """Initialize the execution bridge.

        Args:
            dify_client: Dify API client instance
        """
        self.dify_client = dify_client

    async def execute_via_dify(
        self,
        dag_definition: Dict[str, Any],
        input_context: Dict[str, Any],
        mode: str = "dry_run",
        user: str = "soc-copilot"
    ) -> Dict[str, Any]:
        """Execute a DAG definition through Dify workflow engine.

        Args:
            dag_definition: SOC Copilot DAG definition
            input_context: Input variables
            mode: Execution mode (dry_run or apply)
            user: User identifier

        Returns:
            Execution results
        """
        metadata = dag_definition.get("metadata", {})
        dify_app_id = metadata.get("dify_app_id")

        if not dify_app_id:
            raise ValueError("DAG definition is not linked to a Dify workflow")

        # Map SOC Copilot inputs to Dify inputs
        dify_inputs = self._map_inputs_to_dify(input_context, dag_definition)

        # Execute through Dify
        result = await self.dify_client.execute_workflow(
            app_id=dify_app_id,
            inputs=dify_inputs,
            user=user,
            mode=mode
        )

        # Map Dify outputs back to SOC Copilot format
        return self._map_outputs_from_dify(result, dag_definition)

    def _map_inputs_to_dify(self, input_context: Dict[str, Any], dag_definition: Dict[str, Any]) -> Dict[str, Any]:
        """Map SOC Copilot input context to Dify workflow inputs.

        Args:
            input_context: SOC Copilot input
            dag_definition: DAG definition with node mappings

        Returns:
            Dify workflow inputs
        """
        # For now, pass through inputs directly
        # In production, you would map based on node input templates
        return input_context

    def _map_outputs_from_dify(self, dify_result, dag_definition: Dict[str, Any]) -> Dict[str, Any]:
        """Map Dify execution results to SOC Copilot format.

        Args:
            dify_result: Dify execution response
            dag_definition: Original DAG definition

        Returns:
            SOC Copilot formatted outputs
        """
        return {
            "status": dify_result.status,
            "outputs": dify_result.outputs or {},
            "error": dify_result.error,
            "metadata": dify_result.execution_metadata,
            "execution_mode": "dify",
        }
