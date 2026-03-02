"""
Custom Exception Classes

This module defines custom exception classes that use error codes
instead of hardcoded error messages.
"""

from typing import Any, Dict, Optional
from fastapi import HTTPException, status
from core.enums.error_codes import ErrorCode, get_error_message


class APIException(HTTPException):
    """
    Base API exception that uses error codes

    Attributes:
        code: Error code from ErrorCode enum
        status_code: HTTP status code
        details: Additional error details
    """

    def __init__(
        self,
        code: ErrorCode,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.code = code
        self.status_code = status_code
        self.details = details or {}

        # Build error response
        super().__init__(
            status_code=status_code,
            detail={
                "code": str(code),
                "message": get_error_message(code),
                **self.details,
            },
        )


class BadRequestException(APIException):
    """400 Bad Request"""

    def __init__(self, code: ErrorCode, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code=code,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )


class UnauthorizedException(APIException):
    """401 Unauthorized"""

    def __init__(self, code: ErrorCode, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code=code,
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details,
        )


class ForbiddenException(APIException):
    """403 Forbidden"""

    def __init__(self, code: ErrorCode, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code=code,
            status_code=status.HTTP_403_FORBIDDEN,
            details=details,
        )


class NotFoundException(APIException):
    """404 Not Found"""

    def __init__(self, code: ErrorCode, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code=code,
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


class ConflictException(APIException):
    """409 Conflict"""

    def __init__(self, code: ErrorCode, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code=code,
            status_code=status.HTTP_409_CONFLICT,
            details=details,
        )


class UnprocessableEntityException(APIException):
    """422 Unprocessable Entity"""

    def __init__(self, code: ErrorCode, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code=code,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


class TooManyRequestsException(APIException):
    """429 Too Many Requests"""

    def __init__(self, code: ErrorCode, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code=code,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=details,
        )


class InternalServerException(APIException):
    """500 Internal Server Error"""

    def __init__(self, code: ErrorCode, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code=code,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
        )


class ServiceUnavailableException(APIException):
    """503 Service Unavailable"""

    def __init__(self, code: ErrorCode, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code=code,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details,
        )


# ============================================================================
# Convenience Functions for Common Errors
# ============================================================================


def unauthorized(message: Optional[str] = None) -> APIException:
    """Quick unauthorized error"""
    exc = UnauthorizedException(ErrorCode.AUTH_UNAUTHORIZED)
    if message:
        exc.details["message"] = message
    return exc


def forbidden(message: Optional[str] = None) -> APIException:
    """Quick forbidden error"""
    exc = ForbiddenException(ErrorCode.AUTH_FORBIDDEN)
    if message:
        exc.details["message"] = message
    return exc


def not_found(resource: str = "Resource") -> APIException:
    """Quick not found error"""
    return NotFoundException(
        ErrorCode.RESOURCE_NOT_FOUND,
        details={"resource": resource},
    )


def definition_not_found(definition_id: str) -> APIException:
    """Quick definition not found error"""
    return NotFoundException(
        ErrorCode.DEFINITION_NOT_FOUND,
        details={"definition_id": definition_id},
    )


def execution_not_found(execution_id: str) -> APIException:
    """Quick execution not found error"""
    return NotFoundException(
        ErrorCode.EXECUTION_NOT_FOUND,
        details={"execution_id": execution_id},
    )


def trigger_not_found(trigger_id: str) -> APIException:
    """Quick trigger not found error"""
    return NotFoundException(
        ErrorCode.TRIGGER_NOT_FOUND,
        details={"trigger_id": trigger_id},
    )


def invalid_input(field: str, reason: str = "") -> APIException:
    """Quick invalid input error"""
    details = {"field": field}
    if reason:
        details["reason"] = reason
    return BadRequestException(
        ErrorCode.VALIDATION_INVALID_INPUT,
        details=details,
    )


def internal_error(message: Optional[str] = None) -> APIException:
    """Quick internal server error"""
    exc = InternalServerException(ErrorCode.GENERAL_INTERNAL_ERROR)
    if message:
        exc.details["message"] = message
    return exc
