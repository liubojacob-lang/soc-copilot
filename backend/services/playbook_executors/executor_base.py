"""Base executor for playbook nodes."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ExecutorContext:
    """Context passed to node executors."""
    run_id: str
    node_id: str
    node_def: dict[str, Any]
    input_json: dict[str, Any]
    attempt_no: int = 1
    # v0.8.2: User context for approval nodes and audit
    user_id: Optional[str] = None
    username: Optional[str] = None
    # Session for database operations (optional, can be injected)
    session: Optional[Any] = field(default=None, repr=False)


class BaseExecutor(ABC):
    """Base class for node executors."""

    @abstractmethod
    async def execute(self, context: ExecutorContext) -> dict[str, Any]:
        """Execute the node.

        Args:
            context: Execution context with node definition and inputs

        Returns:
            Output dictionary with execution results

        Raises:
            Exception: If execution fails
        """
        pass

    def _get_input(self, context: ExecutorContext, key: str, default: Any = None) -> Any:
        """Get input value from context."""
        return context.input_json.get(key, default)

    def _resolve_template(self, template: str, context: ExecutorContext) -> str:
        """Resolve template variables in string."""
        result = template
        for key, value in context.input_json.items():
            result = result.replace(f"{{{{{key}}}}}", str(value))
        return result
