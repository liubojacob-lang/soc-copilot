"""DAG execution exception hierarchy and handling utilities.

This module provides a comprehensive exception hierarchy for DAG execution,
enabling precise error handling, classification, and recovery strategies.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


class ErrorSeverity(Enum):
    """Error severity levels for classification."""
    LOW = "low"  # Minor issues, execution can continue
    MEDIUM = "medium"  # Significant issues, may affect results
    HIGH = "high"  # Critical issues, execution should stop
    FATAL = "fatal"  # Unrecoverable errors


class ErrorCategory(Enum):
    """Error categories for classification and handling."""
    # Configuration errors
    INVALID_DEFINITION = "invalid_definition"
    INVALID_NODE_CONFIG = "invalid_node_config"
    CYCLE_DETECTED = "cycle_detected"
    
    # Execution errors
    NODE_EXECUTION_FAILED = "node_execution_failed"
    TIMEOUT = "timeout"
    RESOURCE_EXHAUSTED = "resource_exhausted"
    
    # Dependency errors
    DEPENDENCY_FAILED = "dependency_failed"
    MISSING_DEPENDENCY = "missing_dependency"
    
    # External service errors
    EXTERNAL_SERVICE_ERROR = "external_service_error"
    API_ERROR = "api_error"
    NETWORK_ERROR = "network_error"
    
    # Data errors
    INVALID_INPUT = "invalid_input"
    INVALID_OUTPUT = "invalid_output"
    DATA_VALIDATION_ERROR = "data_validation_error"
    
    # System errors
    DATABASE_ERROR = "database_error"
    INTERNAL_ERROR = "internal_error"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class ErrorContext:
    """Rich context information for DAG execution errors."""
    run_id: str
    node_id: Optional[str] = None
    step_id: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    trace_id: Optional[str] = None
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    retry_count: int = 0
    duration_ms: Optional[int] = None
    parent_error_id: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging and serialization."""
        return {
            "run_id": self.run_id,
            "node_id": self.node_id,
            "step_id": self.step_id,
            "timestamp": self.timestamp,
            "trace_id": self.trace_id,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "retry_count": self.retry_count,
            "duration_ms": self.duration_ms,
            "parent_error_id": self.parent_error_id,
            "extra": self.extra,
        }


class DAGExecutionError(Exception):
    """Base exception for all DAG execution errors.
    
    Provides rich error context and classification for proper handling.
    """
    
    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN_ERROR,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Optional[ErrorContext] = None,
        recoverable: bool = False,
        retry_after: Optional[int] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.context = context
        self.recoverable = recoverable
        self.retry_after = retry_after  # Seconds to wait before retry
        self.cause = cause
        self.error_id = f"err_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses and logging."""
        return {
            "error_id": self.error_id,
            "message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "recoverable": self.recoverable,
            "retry_after": self.retry_after,
            "context": self.context.to_dict() if self.context else None,
            "cause": str(self.cause) if self.cause else None,
        }


class DAGDefinitionError(DAGExecutionError):
    """Error in DAG definition (invalid structure, cycle, etc.)."""
    
    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.INVALID_DEFINITION,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            category=category,
            severity=ErrorSeverity.HIGH,
            context=context,
            recoverable=False,
            cause=cause,
        )


class DAGCycleError(DAGDefinitionError):
    """Cycle detected in DAG definition."""
    
    def __init__(self, message: str, cycle_nodes: List[str], context: Optional[ErrorContext] = None):
        super().__init__(
            message=message,
            category=ErrorCategory.CYCLE_DETECTED,
            context=context,
        )
        self.cycle_nodes = cycle_nodes


class NodeExecutionError(DAGExecutionError):
    """Error during node execution."""
    
    def __init__(
        self,
        message: str,
        node_id: str,
        step_id: str,
        category: ErrorCategory = ErrorCategory.NODE_EXECUTION_FAILED,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Optional[ErrorContext] = None,
        recoverable: bool = False,
        retry_after: Optional[int] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            category=category,
            severity=severity,
            context=context,
            recoverable=recoverable,
            retry_after=retry_after,
            cause=cause,
        )
        self.node_id = node_id
        self.step_id = step_id


class NodeTimeoutError(NodeExecutionError):
    """Node execution timed out."""
    
    def __init__(
        self,
        node_id: str,
        step_id: str,
        timeout_seconds: int,
        context: Optional[ErrorContext] = None,
    ):
        super().__init__(
            message=f"Node {node_id} timed out after {timeout_seconds}s",
            node_id=node_id,
            step_id=step_id,
            category=ErrorCategory.TIMEOUT,
            severity=ErrorSeverity.HIGH,
            context=context,
            recoverable=True,
            retry_after=min(timeout_seconds, 60),  # Retry after timeout or 60s
        )
        self.timeout_seconds = timeout_seconds


class DependencyError(NodeExecutionError):
    """Error due to failed dependency."""
    
    def __init__(
        self,
        node_id: str,
        step_id: str,
        failed_dependency: str,
        dependency_error: Optional[DAGExecutionError] = None,
        context: Optional[ErrorContext] = None,
    ):
        super().__init__(
            message=f"Dependency {failed_dependency} failed for node {node_id}",
            node_id=node_id,
            step_id=step_id,
            category=ErrorCategory.DEPENDENCY_FAILED,
            severity=ErrorSeverity.MEDIUM,
            context=context,
            recoverable=False,
            cause=dependency_error,
        )
        self.failed_dependency = failed_dependency


class ExternalServiceError(NodeExecutionError):
    """Error from external service (API, database, etc.)."""
    
    def __init__(
        self,
        message: str,
        node_id: str,
        step_id: str,
        service_name: str,
        status_code: Optional[int] = None,
        context: Optional[ErrorContext] = None,
        recoverable: bool = True,
        retry_after: Optional[int] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            node_id=node_id,
            step_id=step_id,
            category=ErrorCategory.EXTERNAL_SERVICE_ERROR,
            severity=ErrorSeverity.MEDIUM,
            context=context,
            recoverable=recoverable,
            retry_after=retry_after,
            cause=cause,
        )
        self.service_name = service_name
        self.status_code = status_code


class DataValidationError(NodeExecutionError):
    """Error in input/output data validation."""
    
    def __init__(
        self,
        message: str,
        node_id: str,
        step_id: str,
        validation_errors: List[Dict[str, Any]],
        context: Optional[ErrorContext] = None,
    ):
        super().__init__(
            message=message,
            node_id=node_id,
            step_id=step_id,
            category=ErrorCategory.DATA_VALIDATION_ERROR,
            severity=ErrorSeverity.MEDIUM,
            context=context,
            recoverable=False,
        )
        self.validation_errors = validation_errors


class DAGTimeoutError(DAGExecutionError):
    """Global DAG execution timed out."""
    
    def __init__(
        self,
        run_id: str,
        timeout_seconds: int,
        completed_nodes: List[str],
        pending_nodes: List[str],
        context: Optional[ErrorContext] = None,
    ):
        super().__init__(
            message=f"DAG execution timed out after {timeout_seconds}s",
            category=ErrorCategory.TIMEOUT,
            severity=ErrorSeverity.HIGH,
            context=context,
            recoverable=False,
        )
        self.timeout_seconds = timeout_seconds
        self.completed_nodes = completed_nodes
        self.pending_nodes = pending_nodes


class ErrorHandler:
    """Centralized error handler for DAG execution.
    
    Provides consistent error handling, logging, and recovery strategies.
    """
    
    def __init__(self, run_id: str, trace_id: Optional[str] = None):
        self.run_id = run_id
        self.trace_id = trace_id
        self._errors: List[DAGExecutionError] = []
    
    def create_context(
        self,
        node_id: Optional[str] = None,
        step_id: Optional[str] = None,
        **kwargs,
    ) -> ErrorContext:
        """Create an error context with common fields."""
        return ErrorContext(
            run_id=self.run_id,
            node_id=node_id,
            step_id=step_id,
            trace_id=self.trace_id,
            **kwargs,
        )
    
    def handle_exception(
        self,
        exception: Exception,
        node_id: Optional[str] = None,
        step_id: Optional[str] = None,
        context: Optional[ErrorContext] = None,
    ) -> DAGExecutionError:
        """Convert a generic exception to a DAGExecutionError.
        
        Args:
            exception: The original exception
            node_id: Optional node ID where the error occurred
            step_id: Optional step ID where the error occurred
            context: Optional error context
            
        Returns:
            A DAGExecutionError with proper classification
        """
        # If already a DAGExecutionError, just record and return
        if isinstance(exception, DAGExecutionError):
            self._errors.append(exception)
            return exception
        
        # Convert to appropriate DAGExecutionError
        context = context or self.create_context(node_id=node_id, step_id=step_id)
        
        # Classify based on exception type
        if isinstance(exception, TimeoutError) or isinstance(exception, asyncio.TimeoutError):
            error = NodeTimeoutError(
                node_id=node_id or "unknown",
                step_id=step_id or "unknown",
                timeout_seconds=300,  # Default timeout
                context=context,
                cause=exception,
            )
        elif isinstance(exception, ValueError):
            error = DataValidationError(
                message=str(exception),
                node_id=node_id or "unknown",
                step_id=step_id or "unknown",
                validation_errors=[{"error": str(exception)}],
                context=context,
            )
        else:
            error = NodeExecutionError(
                message=str(exception),
                node_id=node_id or "unknown",
                step_id=step_id or "unknown",
                context=context,
                recoverable=True,
                cause=exception,
            )
        
        self._errors.append(error)
        return error
    
    def get_all_errors(self) -> List[DAGExecutionError]:
        """Get all recorded errors."""
        return self._errors.copy()
    
    def get_errors_by_severity(self, severity: ErrorSeverity) -> List[DAGExecutionError]:
        """Get errors filtered by severity."""
        return [e for e in self._errors if e.severity == severity]
    
    def has_fatal_errors(self) -> bool:
        """Check if any fatal errors occurred."""
        return any(e.severity == ErrorSeverity.FATAL for e in self._errors)
    
    def should_abort(self) -> bool:
        """Check if execution should be aborted due to errors."""
        return self.has_fatal_errors() or len(self.get_errors_by_severity(ErrorSeverity.HIGH)) > 0


# Import asyncio at module level for TimeoutError handling
import asyncio
