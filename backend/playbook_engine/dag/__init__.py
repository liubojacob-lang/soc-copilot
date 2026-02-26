"""DAG-based playbook execution engine for v0.7."""

from .state_machine import NodeState, NodeStateMachine, validate_state_transition
from .retry_policy import RetryPolicy, RetryResult
from .engine import DAGExecutionEngine, DAGBuilder
from .exceptions import (
    DAGExecutionError,
    DAGDefinitionError,
    DAGCycleError,
    DAGTimeoutError,
    NodeExecutionError,
    NodeTimeoutError,
    DependencyError,
    ExternalServiceError,
    DataValidationError,
    ErrorHandler,
    ErrorCategory,
    ErrorSeverity,
    ErrorContext,
)

__all__ = [
    "NodeState",
    "NodeStateMachine",
    "validate_state_transition",
    "RetryPolicy",
    "RetryResult",
    "DAGExecutionEngine",
    "DAGBuilder",
    # Exceptions
    "DAGExecutionError",
    "DAGDefinitionError",
    "DAGCycleError",
    "DAGTimeoutError",
    "NodeExecutionError",
    "NodeTimeoutError",
    "DependencyError",
    "ExternalServiceError",
    "DataValidationError",
    "ErrorHandler",
    "ErrorCategory",
    "ErrorSeverity",
    "ErrorContext",
]
