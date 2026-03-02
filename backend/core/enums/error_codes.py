"""
Error Code Definitions

This module defines all error codes used throughout the application.
Error codes follow the format: DOMAIN_SPECIFIC_ERROR

Example:
- AUTH_INVALID_CREDENTIALS: Authentication related error
- RESOURCE_NOT_FOUND: Resource related error
"""

from enum import Enum


class ErrorCode(str, Enum):
    """Base error code enum"""

    def __str__(self) -> str:
        return self.value


# ============================================================================
# Authentication & Authorization Errors (AUTH_xxx)
# ============================================================================
class AuthError(ErrorCode):
    """Authentication and authorization errors"""

    INVALID_CREDENTIALS = "AUTH_INVALID_CREDENTIALS"
    INVALID_TOKEN = "AUTH_INVALID_TOKEN"
    TOKEN_EXPIRED = "AUTH_TOKEN_EXPIRED"
    TOKEN_MISSING = "AUTH_TOKEN_MISSING"
    INSUFFICIENT_PERMISSIONS = "AUTH_INSUFFICIENT_PERMISSIONS"
    USER_NOT_FOUND = "AUTH_USER_NOT_FOUND"
    USER_DISABLED = "AUTH_USER_DISABLED"
    SESSION_EXPIRED = "AUTH_SESSION_EXPIRED"
    LOGIN_FAILED = "AUTH_LOGIN_FAILED"
    LOGOUT_FAILED = "AUTH_LOGOUT_FAILED"
    UNAUTHORIZED = "AUTH_UNAUTHORIZED"
    FORBIDDEN = "AUTH_FORBIDDEN"


# ============================================================================
# Resource Errors (RESOURCE_xxx)
# ============================================================================
class ResourceError(ErrorCode):
    """Resource related errors"""

    NOT_FOUND = "RESOURCE_NOT_FOUND"
    ALREADY_EXISTS = "RESOURCE_ALREADY_EXISTS"
    CONFLICT = "RESOURCE_CONFLICT"
    LOCKED = "RESOURCE_LOCKED"
    DEPENDENCY_EXISTS = "RESOURCE_DEPENDENCY_EXISTS"
    VERSION_CONFLICT = "RESOURCE_VERSION_CONFLICT"


# ============================================================================
# Definition Specific Errors (DEFINITION_xxx)
# ============================================================================
class DefinitionError(ErrorCode):
    """Playbook definition errors"""

    NOT_FOUND = "DEFINITION_NOT_FOUND"
    INVALID_FORMAT = "DEFINITION_INVALID_FORMAT"
    INVALID_DAG = "DEFINITION_INVALID_DAG"
    CYCLE_DETECTED = "DEFINITION_CYCLE_DETECTED"
    MISSING_REQUIRED_FIELD = "DEFINITION_MISSING_REQUIRED_FIELD"


# ============================================================================
# Execution Errors (EXECUTION_xxx)
# ============================================================================
class ExecutionError(ErrorCode):
    """Playbook execution errors"""

    NOT_FOUND = "EXECUTION_NOT_FOUND"
    ALREADY_RUNNING = "EXECUTION_ALREADY_RUNNING"
    FAILED = "EXECUTION_FAILED"
    CANCELLED = "EXECUTION_CANCELLED"
    TIMEOUT = "EXECUTION_TIMEOUT"
    NODE_FAILED = "EXECUTION_NODE_FAILED"
    QUEUE_FULL = "EXECUTION_QUEUE_FULL"
    INVALID_STATE = "EXECUTION_INVALID_STATE"
    NOT_APPROVED = "EXECUTION_NOT_APPROVED"


# ============================================================================
# Trigger Errors (TRIGGER_xxx)
# ============================================================================
class TriggerError(ErrorCode):
    """Trigger related errors"""

    NOT_FOUND = "TRIGGER_NOT_FOUND"
    INVALID_TYPE = "TRIGGER_INVALID_TYPE"
    INVALID_CRON = "TRIGGER_INVALID_CRON"
    ALREADY_ACTIVE = "TRIGGER_ALREADY_ACTIVE"
    CREATION_FAILED = "TRIGGER_CREATION_FAILED"
    WEBHOOK_FAILED = "TRIGGER_WEBHOOK_FAILED"


# ============================================================================
# Validation Errors (VALIDATION_xxx)
# ============================================================================
class ValidationError(ErrorCode):
    """Input validation errors"""

    INVALID_INPUT = "VALIDATION_INVALID_INPUT"
    MISSING_REQUIRED_FIELD = "VALIDATION_MISSING_REQUIRED_FIELD"
    INVALID_FORMAT = "VALIDATION_INVALID_FORMAT"
    INVALID_VALUE = "VALIDATION_INVALID_VALUE"
    OUT_OF_RANGE = "VALIDATION_OUT_OF_RANGE"
    INVALID_JSON = "VALIDATION_INVALID_JSON"
    INVALID_QUERY_PARAM = "VALIDATION_INVALID_QUERY_PARAM"


# ============================================================================
# Configuration Errors (CONFIG_xxx)
# ============================================================================
class ConfigError(ErrorCode):
    """Configuration related errors"""

    NOT_CONFIGURED = "CONFIG_NOT_CONFIGURED"
    INVALID_VALUE = "CONFIG_INVALID_VALUE"
    MISSING_REQUIRED = "CONFIG_MISSING_REQUIRED"
    LOAD_FAILED = "CONFIG_LOAD_FAILED"
    SAVE_FAILED = "CONFIG_SAVE_FAILED"


# ============================================================================
# External Service Errors (SERVICE_xxx)
# ============================================================================
class ServiceError(ErrorCode):
    """External service errors"""

    UNAVAILABLE = "SERVICE_UNAVAILABLE"
    TIMEOUT = "SERVICE_TIMEOUT"
    CONNECTION_FAILED = "SERVICE_CONNECTION_FAILED"
    API_ERROR = "SERVICE_API_ERROR"
    RATE_LIMITED = "SERVICE_RATE_LIMITED"
    DIFY_CONNECTION_FAILED = "SERVICE_DIFY_CONNECTION_FAILED"
    AI_MODEL_ERROR = "SERVICE_AI_MODEL_ERROR"


# ============================================================================
# Database Errors (DATABASE_xxx)
# ============================================================================
class DatabaseError(ErrorCode):
    """Database related errors"""

    CONNECTION_FAILED = "DATABASE_CONNECTION_FAILED"
    QUERY_FAILED = "DATABASE_QUERY_FAILED"
    CONSTRAINT_VIOLATION = "DATABASE_CONSTRAINT_VIOLATION"
    TRANSACTION_FAILED = "DATABASE_TRANSACTION_FAILED"
    ALREADY_EXISTS = "DATABASE_ALREADY_EXISTS"


# ============================================================================
# File/System Errors (FILE_xxx)
# ============================================================================
class FileError(ErrorCode):
    """File system errors"""

    NOT_FOUND = "FILE_NOT_FOUND"
    PERMISSION_DENIED = "FILE_PERMISSION_DENIED"
    TOO_LARGE = "FILE_TOO_LARGE"
    INVALID_TYPE = "FILE_INVALID_TYPE"
    UPLOAD_FAILED = "FILE_UPLOAD_FAILED"
    DOWNLOAD_FAILED = "FILE_DOWNLOAD_FAILED"


# ============================================================================
# Marketplace Errors (MARKETPLACE_xxx)
# ============================================================================
class MarketplaceError(ErrorCode):
    """Marketplace related errors"""

    DOWNLOAD_FAILED = "MARKETPLACE_DOWNLOAD_FAILED"
    INVALID_URL = "MARKETPLACE_INVALID_URL"
    REPO_NOT_FOUND = "MARKETPLACE_REPO_NOT_FOUND"
    INSTALL_FAILED = "MARKETPLACE_INSTALL_FAILED"


# ============================================================================
# Secrets/Encryption Errors (SECRET_xxx)
# ============================================================================
class SecretError(ErrorCode):
    """Secrets and encryption errors"""

    NOT_FOUND = "SECRET_NOT_FOUND"
    DECRYPTION_FAILED = "SECRET_DECRYPTION_FAILED"
    ENCRYPTION_FAILED = "SECRET_ENCRYPTION_FAILED"
    KEY_MISSING = "SECRET_KEY_MISSING"


# ============================================================================
# Audit Errors (AUDIT_xxx)
# ============================================================================
class AuditError(ErrorCode):
    """Audit logging errors"""

    LOG_FAILED = "AUDIT_LOG_FAILED"
    RETRIEVE_FAILED = "AUDIT_RETRIEVE_FAILED"


# ============================================================================
# Notification Errors (NOTIFICATION_xxx)
# ============================================================================
class NotificationError(ErrorCode):
    """Notification related errors"""

    SEND_FAILED = "NOTIFICATION_SEND_FAILED"
    CONFIG_INVALID = "NOTIFICATION_CONFIG_INVALID"
    CHANNEL_NOT_CONFIGURED = "NOTIFICATION_CHANNEL_NOT_CONFIGURED"


# ============================================================================
# General Errors (GENERAL_xxx)
# ============================================================================
class GeneralError(ErrorCode):
    """General application errors"""

    INTERNAL_ERROR = "GENERAL_INTERNAL_ERROR"
    NOT_IMPLEMENTED = "GENERAL_NOT_IMPLEMENTED"
    MAINTENANCE_MODE = "GENERAL_MAINTENANCE_MODE"
    RATE_LIMITED = "GENERAL_RATE_LIMITED"
    UNKNOWN_ERROR = "GENERAL_UNKNOWN_ERROR"


# Error code to default message mapping (English)
# This will be used as fallback when translation is not available
ERROR_MESSAGES = {
    # Auth errors
    AuthError.INVALID_CREDENTIALS: "Invalid username or password",
    AuthError.INVALID_TOKEN: "Invalid authentication token",
    AuthError.TOKEN_EXPIRED: "Authentication token has expired",
    AuthError.TOKEN_MISSING: "Authentication token is required",
    AuthError.INSUFFICIENT_PERMISSIONS: "Insufficient permissions to perform this action",
    AuthError.USER_NOT_FOUND: "User not found",
    AuthError.USER_DISABLED: "User account has been disabled",
    AuthError.SESSION_EXPIRED: "Session has expired",
    AuthError.LOGIN_FAILED: "Login failed",
    AuthError.LOGOUT_FAILED: "Logout failed",
    AuthError.UNAUTHORIZED: "Authentication required",
    AuthError.FORBIDDEN: "Access forbidden",

    # Resource errors
    ResourceError.NOT_FOUND: "Resource not found",
    ResourceError.ALREADY_EXISTS: "Resource already exists",
    ResourceError.CONFLICT: "Resource conflict",
    ResourceError.LOCKED: "Resource is locked",
    ResourceError.DEPENDENCY_EXISTS: "Resource has dependencies",
    ResourceError.VERSION_CONFLICT: "Resource version conflict",

    # Definition errors
    DefinitionError.NOT_FOUND: "Playbook definition not found",
    DefinitionError.INVALID_FORMAT: "Invalid playbook definition format",
    DefinitionError.INVALID_DAG: "Invalid DAG structure",
    DefinitionError.CYCLE_DETECTED: "Cycle detected in playbook DAG",
    DefinitionError.MISSING_REQUIRED_FIELD: "Missing required field in definition",

    # Execution errors
    ExecutionError.NOT_FOUND: "Execution not found",
    ExecutionError.ALREADY_RUNNING: "Execution is already running",
    ExecutionError.FAILED: "Execution failed",
    ExecutionError.CANCELLED: "Execution was cancelled",
    ExecutionError.TIMEOUT: "Execution timed out",
    ExecutionError.NODE_FAILED: "Execution node failed",
    ExecutionError.QUEUE_FULL: "Execution queue is full",
    ExecutionError.INVALID_STATE: "Invalid execution state",
    ExecutionError.NOT_APPROVED: "Execution not approved",

    # Trigger errors
    TriggerError.NOT_FOUND: "Trigger not found",
    TriggerError.INVALID_TYPE: "Invalid trigger type",
    TriggerError.INVALID_CRON: "Invalid cron expression",
    TriggerError.ALREADY_ACTIVE: "Trigger is already active",
    TriggerError.CREATION_FAILED: "Failed to create trigger",
    TriggerError.WEBHOOK_FAILED: "Webhook execution failed",

    # Validation errors
    ValidationError.INVALID_INPUT: "Invalid input",
    ValidationError.MISSING_REQUIRED_FIELD: "Missing required field",
    ValidationError.INVALID_FORMAT: "Invalid format",
    ValidationError.INVALID_VALUE: "Invalid value",
    ValidationError.OUT_OF_RANGE: "Value out of range",
    ValidationError.INVALID_JSON: "Invalid JSON format",
    ValidationError.INVALID_QUERY_PARAM: "Invalid query parameter",

    # Config errors
    ConfigError.NOT_CONFIGURED: "Not configured",
    ConfigError.INVALID_VALUE: "Invalid configuration value",
    ConfigError.MISSING_REQUIRED: "Missing required configuration",
    ConfigError.LOAD_FAILED: "Failed to load configuration",
    ConfigError.SAVE_FAILED: "Failed to save configuration",

    # Service errors
    ServiceError.UNAVAILABLE: "Service unavailable",
    ServiceError.TIMEOUT: "Service request timed out",
    ServiceError.CONNECTION_FAILED: "Failed to connect to service",
    ServiceError.API_ERROR: "Service API error",
    ServiceError.RATE_LIMITED: "Service rate limit exceeded",
    ServiceError.DIFY_CONNECTION_FAILED: "Failed to connect to Dify",
    ServiceError.AI_MODEL_ERROR: "AI model error",

    # Database errors
    DatabaseError.CONNECTION_FAILED: "Database connection failed",
    DatabaseError.QUERY_FAILED: "Database query failed",
    DatabaseError.CONSTRAINT_VIOLATION: "Database constraint violation",
    DatabaseError.TRANSACTION_FAILED: "Database transaction failed",
    DatabaseError.ALREADY_EXISTS: "Database record already exists",

    # File errors
    FileError.NOT_FOUND: "File not found",
    FileError.PERMISSION_DENIED: "File permission denied",
    FileError.TOO_LARGE: "File too large",
    FileError.INVALID_TYPE: "Invalid file type",
    FileError.UPLOAD_FAILED: "File upload failed",
    FileError.DOWNLOAD_FAILED: "File download failed",

    # Marketplace errors
    MarketplaceError.DOWNLOAD_FAILED: "Failed to download from marketplace",
    MarketplaceError.INVALID_URL: "Invalid marketplace URL",
    MarketplaceError.REPO_NOT_FOUND: "Repository not found",
    MarketplaceError.INSTALL_FAILED: "Failed to install from marketplace",

    # Secret errors
    SecretError.NOT_FOUND: "Secret not found",
    SecretError.DECRYPTION_FAILED: "Failed to decrypt secret",
    SecretError.ENCRYPTION_FAILED: "Failed to encrypt secret",
    SecretError.KEY_MISSING: "Encryption key missing",

    # Audit errors
    AuditError.LOG_FAILED: "Failed to write audit log",
    AuditError.RETRIEVE_FAILED: "Failed to retrieve audit logs",

    # Notification errors
    NotificationError.SEND_FAILED: "Failed to send notification",
    NotificationError.CONFIG_INVALID: "Invalid notification configuration",
    NotificationError.CHANNEL_NOT_CONFIGURED: "Notification channel not configured",

    # General errors
    GeneralError.INTERNAL_ERROR: "Internal server error",
    GeneralError.NOT_IMPLEMENTED: "Feature not implemented",
    GeneralError.MAINTENANCE_MODE: "System is in maintenance mode",
    GeneralError.RATE_LIMITED: "Rate limit exceeded",
    GeneralError.UNKNOWN_ERROR: "An unknown error occurred",
}


def get_error_message(code: ErrorCode) -> str:
    """Get default error message for error code"""
    return ERROR_MESSAGES.get(code, str(code))
