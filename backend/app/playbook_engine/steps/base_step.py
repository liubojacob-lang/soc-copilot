"""Base step class for playbook step implementations."""

from ..models import BaseStep


class BaseStepImpl(BaseStep):
    """Base implementation with common utilities."""

    def validate_input(self, input_json: dict) -> bool:
        """Validate input has required fields."""
        return isinstance(input_json, dict)

    def _log_dry_run(self, message: str) -> None:
        """Log a dry-run message."""
        print(f"[DRY RUN] {message}")
