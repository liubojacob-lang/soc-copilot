"""Models and interfaces for playbook step execution."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class StepResult:
    """Result of a step execution."""

    step_id: str
    success: bool
    output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    skipped: bool = False
    skipped_reason: str | None = None


class BaseStep(ABC):
    """Base class for playbook step implementations."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable step name."""
        ...

    @property
    @abstractmethod
    def step_id(self) -> str:
        """Unique step identifier."""
        ...

    @property
    @abstractmethod
    def step_type(self) -> str:
        """Step type/category (e.g., 'enrichment', 'analysis')."""
        ...

    @property
    def supports_apply(self) -> bool:
        """Whether this step supports apply mode (vs dry_run only)."""
        return True

    @property
    def description(self) -> str:
        """Step description."""
        return ""

    @abstractmethod
    def execute(self, input_json: dict[str, Any], mode: str) -> dict[str, Any]:
        """Execute the step.

        Args:
            input_json: Input data for the step
            mode: Execution mode ('dry_run' or 'apply')

        Returns:
            Step output data
        """
        ...

    def validate_input(self, input_json: dict[str, Any]) -> bool:
        """Validate input data.

        Args:
            input_json: Input data to validate

        Returns:
            True if valid
        """
        return True
