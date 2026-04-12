"""Factory for creating node executors."""


from .executor_base import BaseExecutor


class ExecutorFactory:
    """Factory for creating node executors."""

    _executors: dict[str, type[BaseExecutor]] = {}

    @classmethod
    def register(cls, node_type: str, executor_class: type[BaseExecutor]) -> None:
        """Register an executor for a node type."""
        cls._executors[node_type] = executor_class

    @classmethod
    def get_executor(cls, node_type: str) -> BaseExecutor:
        """Get an executor instance for a node type."""
        executor_class = cls._executors.get(node_type)
        if not executor_class:
            raise ValueError(f"No executor registered for node type: {node_type}")
        return executor_class()

    @classmethod
    def list_types(cls) -> list[str]:
        """List all registered node types."""
        return list(cls._executors.keys())


# Import executors to register them
from .decision_executor import DecisionExecutor
from .extract_iocs_executor import ExtractIocsExecutor
from .http_request_executor import HttpRequestExecutor
from .human_approval_executor import HumanApprovalExecutor
from .slack_webhook_executor import SlackWebhookExecutor
from .sleep_executor import SleepExecutor
from .ti_lookup_otx_executor import TiLookupOtxExecutor

# Auto-register
ExecutorFactory.register("ti_lookup_otx", TiLookupOtxExecutor)
ExecutorFactory.register("extract_iocs", ExtractIocsExecutor)
ExecutorFactory.register("decision", DecisionExecutor)
ExecutorFactory.register("sleep", SleepExecutor)
ExecutorFactory.register("http_request", HttpRequestExecutor)
ExecutorFactory.register("human_approval", HumanApprovalExecutor)
ExecutorFactory.register("slack_webhook_notify", SlackWebhookExecutor)
