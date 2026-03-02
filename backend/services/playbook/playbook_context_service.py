"""Playbook Context Variable Service for v0.7.3.

This service handles:
- Variable template rendering ({{context.xxx}}, {{input.xxx}}, {{node.<node_id>.field}}, {{secret.xxx}})
- JSONPath extraction from node outputs
- Context merging during playbook execution
- Initial context building from input
"""

import re
import json
from typing import Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ContextVariableRenderer:
    """Service for rendering context variables in playbook templates."""

    # Variable reference patterns
    CONTEXT_VAR_PATTERN = re.compile(r'\{\{context\.([^}]+)\}\}')
    INPUT_VAR_PATTERN = re.compile(r'\{\{input\.([^}]+)\}\}')
    NODE_VAR_PATTERN = re.compile(r'\{\{node\.([^}]+)\}\}')
    SECRET_VAR_PATTERN = re.compile(r'\{\{secret\.([^}]+)\}\}')  # v0.7.4: Secret references

    @staticmethod
    def render_template(template: Any, context: dict[str, Any], input_data: dict[str, Any],
                        node_outputs: dict[str, dict[str, Any]], secrets: dict[str, str] | None = None) -> Any:
        """
        Render a template by replacing variable references with actual values.

        Supports:
        - {{context.xxx}} - References context variables
        - {{input.xxx}} - References initial input
        - {{node.<node_id>.field}} - References output from specific node
        - {{secret.xxx}} - References secret values (v0.7.4)

        Args:
            template: Template (string, dict, or list) to render
            context: Current context dictionary
            input_data: Initial input data
            node_outputs: Dictionary of node outputs {node_id: output_dict}
            secrets: Dictionary of secret values {name: value} (v0.7.4)

        Returns:
            Rendered value with variables replaced
        """
        if isinstance(template, str):
            return ContextVariableRenderer._render_string(template, context, input_data, node_outputs, secrets)
        elif isinstance(template, dict):
            return {
                key: ContextVariableRenderer.render_template(value, context, input_data, node_outputs, secrets)
                for key, value in template.items()
            }
        elif isinstance(template, list):
            return [
                ContextVariableRenderer.render_template(item, context, input_data, node_outputs, secrets)
                for item in template
            ]
        else:
            return template

    @staticmethod
    def _render_string(template: str, context: dict[str, Any], input_data: dict[str, Any],
                       node_outputs: dict[str, dict[str, Any]], secrets: dict[str, str] | None = None) -> str:
        """Render variable references in a string template."""
        result = template

        # Replace {{context.xxx}} references
        def replace_context_var(match):
            path = match.group(1)
            value = ContextVariableRenderer._get_nested_value(context, path)
            if value is None:
                logger.warning(f"Context variable 'context.{path}' not found, using empty string")
                return ""
            return str(value)

        result = ContextVariableRenderer.CONTEXT_VAR_PATTERN.sub(replace_context_var, result)

        # Replace {{input.xxx}} references
        def replace_input_var(match):
            path = match.group(1)
            value = ContextVariableRenderer._get_nested_value(input_data, path)
            if value is None:
                logger.warning(f"Input variable 'input.{path}' not found, using empty string")
                return ""
            return str(value)

        result = ContextVariableRenderer.INPUT_VAR_PATTERN.sub(replace_input_var, result)

        # Replace {{node.<node_id>.field}} references
        def replace_node_var(match):
            path = match.group(1)
            parts = path.split('.', 1)
            if len(parts) < 2:
                logger.warning(f"Invalid node variable reference 'node.{path}', expected 'node.<node_id>.field'")
                return ""

            node_id, field_path = parts[0], parts[1]
            if node_id not in node_outputs:
                logger.warning(f"Node '{node_id}' output not found in context")
                return ""

            value = ContextVariableRenderer._get_nested_value(node_outputs[node_id], field_path)
            if value is None:
                logger.warning(f"Field '{field_path}' not found in node '{node_id}' output")
                return ""

            return str(value)

        result = ContextVariableRenderer.NODE_VAR_PATTERN.sub(replace_node_var, result)

        # v0.7.4: Replace {{secret.xxx}} references
        if secrets:
            def replace_secret_var(match):
                secret_name = match.group(1)
                if secret_name in secrets:
                    return str(secrets[secret_name])
                else:
                    logger.warning(f"Secret '{secret_name}' not found in provided secrets")
                    return ""

            result = ContextVariableRenderer.SECRET_VAR_PATTERN.sub(replace_secret_var, result)

        return result

    @staticmethod
    def _get_nested_value(data: dict[str, Any], path: str) -> Any:
        """Get nested value from dictionary using dot notation."""
        keys = path.split('.')
        value = data

        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None

            if value is None:
                return None

        return value

    @staticmethod
    def extract_jsonpath(data: dict[str, Any], jsonpath: str) -> Any:
        """
        Extract value from data using JSONPath expression.

        Supports:
        - $.field - Root field
        - $.field.nested - Nested field
        - $.array[0] - Array index (basic support)
        - field - Shorthand for $.field

        Args:
            data: Source data dictionary
            jsonpath: JSONPath expression

        Returns:
            Extracted value or None if not found
        """
        if not jsonpath:
            return None

        # Normalize path - ensure it starts with $.
        path = jsonpath.strip()
        if not path.startswith('$'):
            path = '$.' + path

        # Remove leading $.
        if path.startswith('$.'):
            path = path[2:]

        return ContextVariableRenderer._get_nested_value(data, path)

    @staticmethod
    def merge_context(base_context: dict[str, Any], updates: dict[str, Any],
                      prefix: Optional[str] = None) -> dict[str, Any]:
        """
        Merge updates into base context.

        Args:
            base_context: Existing context
            updates: New values to merge
            prefix: Optional prefix for update keys (e.g., 'context.')

        Returns:
            Updated context dictionary
        """
        result = base_context.copy()

        for key, value in updates.items():
            full_key = f"{prefix}.{key}" if prefix else key
            ContextVariableRenderer._set_nested_value(result, full_key, value)

        return result

    @staticmethod
    def _set_nested_value(data: dict[str, Any], path: str, value: Any) -> None:
        """Set nested value in dictionary using dot notation."""
        keys = path.split('.')
        current = data

        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            elif not isinstance(current[key], dict):
                current[key] = {}
            current = current[key]

        current[keys[-1]] = value

    @staticmethod
    def build_initial_context(input_data: dict[str, Any], run_metadata: dict[str, Any]) -> dict[str, Any]:
        """
        Build initial context for a playbook run.

        Args:
            input_data: User-provided input data
            run_metadata: Run metadata (run_id, started_at, etc.)

        Returns:
            Initial context dictionary
        """
        return {
            "input": input_data.copy(),
            "run": run_metadata.copy(),
            "context": {},  # Will be populated during execution
        }

    @staticmethod
    def apply_outputs_mapping(context: dict[str, Any], node_output: dict[str, Any],
                               outputs_mapping: dict[str, str]) -> dict[str, Any]:
        """
        Apply outputs_mapping to merge node outputs into context.

        Args:
            context: Current context
            node_output: Output from executed node
            outputs_mapping: Map of JSONPath expressions to context keys

        Returns:
            Updated context
        """
        if not outputs_mapping:
            return context

        updates = {}

        for jsonpath, context_key in outputs_mapping.items():
            value = ContextVariableRenderer.extract_jsonpath(node_output, jsonpath)
            if value is not None:
                # Support context key with or without 'context.' prefix
                if context_key.startswith('context.'):
                    updates[context_key[8:]] = value
                else:
                    updates[context_key] = value
            else:
                logger.warning(f"JSONPath '{jsonpath}' not found in node output")

        return ContextVariableRenderer.merge_context(context, updates, prefix="context")


class PlaybookContextService:
    """High-level service for managing playbook execution context."""

    def __init__(self):
        self.renderer = ContextVariableRenderer()

    def initialize_run_context(self, run_id: str, input_data: dict[str, Any],
                               definition_id: Optional[str] = None) -> dict[str, Any]:
        """Initialize context for a new playbook run."""
        metadata = {
            "run_id": run_id,
            "started_at": datetime.utcnow().isoformat(),
            "definition_id": definition_id,
        }

        return self.renderer.build_initial_context(input_data, metadata)

    def render_node_inputs(self, node_inputs_template: dict[str, Any],
                           context: dict[str, Any], secrets: dict[str, str] | None = None) -> dict[str, Any]:
        """Render input template for node execution.

        Args:
            node_inputs_template: Template with variable references
            context: Current context dictionary
            secrets: Optional dictionary of resolved secret values

        Returns:
            Rendered inputs with variables replaced
        """
        return self.renderer.render_template(
            node_inputs_template,
            context.get("context", {}),
            context.get("input", {}),
            context.get("nodes", {}),
            secrets
        )

    def merge_node_output(self, context: dict[str, Any], node_id: str,
                           node_output: dict[str, Any], outputs_mapping: dict[str, str]) -> dict[str, Any]:
        """Merge node output into context using outputs_mapping."""
        # Store raw node output for reference
        if "nodes" not in context:
            context["nodes"] = {}
        context["nodes"][node_id] = node_output

        # Apply outputs_mapping to update context
        return self.renderer.apply_outputs_mapping(context, node_output, outputs_mapping)

    def extract_variable_references(self, template: Any) -> list[str]:
        """Extract all variable references from a template."""
        references = []

        def extract(value):
            if isinstance(value, str):
                for match in self.renderer.CONTEXT_VAR_PATTERN.finditer(value):
                    references.append(f"context.{match.group(1)}")
                for match in self.renderer.INPUT_VAR_PATTERN.finditer(value):
                    references.append(f"input.{match.group(1)}")
                for match in self.renderer.NODE_VAR_PATTERN.finditer(value):
                    references.append(f"node.{match.group(1)}")
            elif isinstance(value, dict):
                for v in value.values():
                    extract(v)
            elif isinstance(value, list):
                for item in value:
                    extract(item)

        extract(template)
        return list(set(references))


# Singleton instance
context_service = PlaybookContextService()
