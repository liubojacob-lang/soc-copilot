"""Base Node Plugin interface for v7 DAG system (v0.7.4)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class NodeExecutionContext:
    """Execution context for node plugins."""

    run_id: str
    node_id: str
    node_name: str
    input_json: dict[str, Any]
    mode: str  # dry_run or apply
    secrets: dict[str, str] = field(default_factory=dict)  # Resolved secrets
    context: dict[str, Any] = field(default_factory=dict)  # Current run context


class BaseNodePlugin(ABC):
    """Abstract base class for node plugins.

    Node plugins are reusable components that can be dynamically loaded
    and registered with the NodeRegistry for use in playbook DAGs.
    """

    @property
    @abstractmethod
    def node_id(self) -> str:
        """Unique identifier for this node type (e.g., 'builtin_http_request')."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name for this node type."""
        ...

    @property
    @abstractmethod
    def node_type(self) -> str:
        """Type of node: 'action', 'decision', 'trigger', or 'approval'."""
        ...

    @property
    def description(self) -> str:
        """Optional description of what this node does."""
        return ""

    @abstractmethod
    async def execute(self, context: NodeExecutionContext) -> dict[str, Any]:
        """Execute the node logic.

        Args:
            context: Execution context containing inputs, mode, and other data

        Returns:
            Output dictionary containing the node execution result

        Raises:
            Exception: If execution fails (will be caught and logged)
        """
        ...

    def validate_input(self, input_json: dict[str, Any]) -> None:  # noqa: B027
        """Validate input before execution.

        Override this method to provide custom validation.

        Args:
            input_json: Input data to validate

        Raises:
            ValueError: If input is invalid
        """
        pass

    def get_required_secrets(self) -> list[str]:
        """Get list of secret names this node requires.

        Override this method to declare required secrets for
        pre-validation and automatic resolution.

        Returns:
            List of secret names required by this node
        """
        return []
