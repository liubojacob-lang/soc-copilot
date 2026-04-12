"""Decision node executor."""

from typing import Any

from .executor_base import BaseExecutor, ExecutorContext


class DecisionExecutor(BaseExecutor):
    """Executor for conditional branching."""

    async def execute(self, context: ExecutorContext) -> dict[str, Any]:
        """Evaluate decision condition."""
        condition = context.node_def.get("config", {}).get("condition")
        branches = context.node_def.get("config", {}).get("branches", {})

        if not condition:
            return {
                "status": "success",
                "result": "default",
                "branches": branches,
            }

        # Simple condition evaluation
        # Format: field == value, field > value, etc.
        result = await self._evaluate_condition(condition, context)

        return {
            "status": "success",
            "condition": condition,
            "result": result,
            "branches": branches,
        }

    async def _evaluate_condition(
        self, condition: str, context: ExecutorContext
    ) -> bool:
        """Evaluate a condition string."""
        # Parse simple comparisons: field == value, field > value
        import re

        match = re.match(r"(\w+)\s*([><=!]+)\s*(.+)", condition)
        if match:
            field, op, value = match.groups()

            # Get field value from input
            field_value = self._get_input(context, field)

            # Type conversion
            try:
                if isinstance(field_value, str):
                    field_val = field_value
                    val = value.strip("\"'")
                else:
                    field_val = float(field_value)
                    val = float(value)
            except (ValueError, TypeError):
                return False

            # Evaluate
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

        return True
