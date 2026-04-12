"""Decision node plugin for conditional branching (v0.7.4)."""

import logging
import re
from typing import Any

from ..base_node import BaseNodePlugin, NodeExecutionContext

logger = logging.getLogger(__name__)


class DecisionPlugin(BaseNodePlugin):
    """Decision node for conditional branching in playbooks.

    This node evaluates a condition expression and returns a result
    that can be used to control workflow execution paths.

    Supported condition formats:
    - Simple comparison: field == value, field > value, field < value
    - Boolean logic: field (true if field exists and is truthy)
    - Contains: field in value (checks if field is in value list)
    """

    @property
    def node_id(self) -> str:
        return "builtin_decision"

    @property
    def name(self) -> str:
        return "Decision"

    @property
    def node_type(self) -> str:
        return "decision"

    @property
    def description(self) -> str:
        return "Evaluate conditions to control workflow branching"

    async def execute(self, context: NodeExecutionContext) -> dict[str, Any]:
        """Evaluate decision condition.

        Args:
            context: Execution context

        Returns:
            Decision result with boolean outcome and matched branch
        """
        condition = context.input_json.get("condition")
        branches = context.input_json.get("branches", {})
        default_branch = context.input_json.get("default", "false")

        logger.info(f"[{context.run_id}] Evaluating decision: {condition}")

        if not condition:
            # No condition specified, use default
            return {
                "status": "success",
                "result": True,
                "condition": condition or "true",
                "branch": default_branch,
                "branches": branches,
            }

        # Evaluate the condition
        result = self._evaluate_condition(condition, context)

        # Determine which branch to take
        branch_key = str(result).lower() if isinstance(result, bool) else default_branch
        branch_name = branches.get(
            branch_key, branches.get(default_branch, default_branch)
        )

        logger.info(
            f"[{context.run_id}] Decision result: {result}, branch: {branch_name}"
        )

        return {
            "status": "success",
            "result": result,
            "condition": condition,
            "branch": branch_name,
            "branches": branches,
        }

    def _evaluate_condition(
        self, condition: str, context: NodeExecutionContext
    ) -> bool:
        """Evaluate a condition string against context.

        Supported formats:
        - field == value
        - field != value
        - field > value
        - field < value
        - field >= value
        - field <= value
        - field (truthiness check)
        - field in value1,value2,value3

        Args:
            condition: Condition string to evaluate
            context: Execution context with input data

        Returns:
            Boolean result of condition evaluation
        """
        # Try regex match for comparison operators
        match = re.match(
            r"^(\w+(?:\.\w+)*)\s*([><=!]+|in)\s*(.+)$", str(condition).strip()
        )
        if match:
            field_path, op, value = match.groups()

            # Get field value from input
            field_value = self._get_nested_value(context.input_json, field_path)

            # Handle different operators
            if op == "in":
                # Membership check: field in value1,value2,value3
                values = [v.strip() for v in value.split(",")]
                return str(field_value) in values

            # Type conversion for comparisons
            try:
                # Remove quotes from string values
                if isinstance(value, str) and (
                    (value.startswith('"') and value.endswith('"'))
                    or (value.startswith("'") and value.endswith("'"))
                ):
                    field_val = str(field_value or "")
                    val = value[1:-1]
                else:
                    # Try numeric comparison
                    field_val = float(field_value) if field_value is not None else 0
                    val = float(value)
            except (ValueError, TypeError):
                # Fall back to string comparison
                field_val = str(field_value or "")
                val = value.strip("\"'")
                if op not in ("==", "!="):
                    return False

            # Evaluate comparison
            if op == ">":
                return field_val > val
            elif op == "<":
                return field_val < val
            elif op == ">=":
                return field_val >= val
            elif op == "<=":
                return field_val <= val
            elif op == "==":
                return field_val == val
            elif op == "!=":
                return field_val != val

        # Try simple truthiness check: field_name
        field_value = self._get_nested_value(context.input_json, condition.strip())
        return bool(field_value)

    def _get_nested_value(self, data: dict[str, Any], path: str) -> Any:
        """Get nested value from dictionary using dot notation.

        Args:
            data: Source dictionary
            path: Dot-separated path to value

        Returns:
            Value at path or None if not found
        """
        keys = path.split(".")
        value = data

        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None

            if value is None:
                return None

        return value
