"""Step registry for managing playbook step implementations."""

from .models import BaseStep


class StepRegistry:
    """Registry for playbook step implementations."""

    def __init__(self) -> None:
        """Initialize the step registry."""
        self._steps: dict[str, type[BaseStep]] = {}

    def register(self, step_id: str, step_class: type[BaseStep]) -> None:
        """Register a step implementation.

        Args:
            step_id: Unique step identifier (e.g., "ioc_extract")
            step_class: Step implementation class
        """
        self._steps[step_id] = step_class

    def get_step_implementation(self, step_id: str) -> BaseStep:
        """Get an instance of a step implementation.

        Args:
            step_id: Step identifier

        Returns:
            Step instance

        Raises:
            ValueError: If step is not registered
        """
        if step_id not in self._steps:
            raise ValueError(f"Step not registered: {step_id}")
        return self._steps[step_id]()

    def get_step_name(self, step_id: str) -> str:
        """Get the display name of a step.

        Args:
            step_id: Step identifier

        Returns:
            Step display name
        """
        step = self.get_step_implementation(step_id)
        return step.name

    def get_step_type(self, step_id: str) -> str:
        """Get the type/category of a step.

        Args:
            step_id: Step identifier

        Returns:
            Step type
        """
        step = self.get_step_implementation(step_id)
        return step.step_type

    def list_steps(self) -> list[str]:
        """List all registered step IDs.

        Returns:
            List of step IDs
        """
        return list(self._steps.keys())


# Global registry instance
_registry = StepRegistry()


def get_registry() -> StepRegistry:
    """Get the global step registry instance.

    Returns:
        Global StepRegistry instance
    """
    return _registry


def register_step(step_id: str, step_class: type[BaseStep]) -> None:
    """Register a step with the global registry.

    Args:
        step_id: Unique step identifier
        step_class: Step implementation class
    """
    _registry.register(step_id, step_class)
