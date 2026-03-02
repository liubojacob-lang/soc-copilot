"""Common schemas for unified API responses.

This module provides:
- Unified API response wrapper
- Paginated response structure
- Error response structure
- Helper functions for creating responses

Usage:
    from schemas.common import APIResponse, success_response, paginated_response

    @router.get("/items")
    async def get_items() -> APIResponse[List[Item]]:
        items = await service.get_items()
        return success_response(data=items)
"""

from datetime import datetime, timezone
from typing import Generic, TypeVar, Optional, List, Any
from pydantic import BaseModel, Field, ConfigDict

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """Unified API response wrapper.
    
    All API endpoints should return this structure for consistency.
    
    Attributes:
        code: Response code (SUCCESS for success, error code for errors)
        message: Human-readable response message
        data: Response payload (generic type)
        trace_id: Request trace ID for debugging
        timestamp: Response timestamp (UTC)
    """
    
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "code": "SUCCESS",
                "message": "OK",
                "data": {},
                "trace_id": "abc123def456",
                "timestamp": "2024-01-01T00:00:00Z"
            }
        }
    )
    
    code: str = Field(default="SUCCESS", description="Response code")
    message: str = Field(default="OK", description="Response message")
    data: Optional[T] = Field(default=None, description="Response payload")
    trace_id: Optional[str] = Field(default=None, description="Request trace ID")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Response timestamp (UTC)"
    )


class PaginatedData(BaseModel, Generic[T]):
    """Paginated data structure for list responses.
    
    Attributes:
        items: List of items on current page
        total: Total count of items
        page: Current page number (1-indexed)
        page_size: Number of items per page
        total_pages: Total number of pages
        has_next: Whether there is a next page
        has_prev: Whether there is a previous page
    """
    
    model_config = ConfigDict(populate_by_name=True)
    
    items: List[T] = Field(default_factory=list, description="List of items")
    total: int = Field(default=0, ge=0, description="Total count")
    page: int = Field(default=1, ge=1, description="Current page (1-indexed)")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")
    total_pages: int = Field(default=0, ge=0, description="Total pages")
    has_next: bool = Field(default=False, description="Has next page")
    has_prev: bool = Field(default=False, description="Has previous page")
    
    @classmethod
    def create(
        cls,
        items: List[T],
        total: int,
        page: int = 1,
        page_size: int = 20
    ) -> "PaginatedData[T]":
        """Create paginated data with auto-calculated fields.
        
        Args:
            items: List of items for current page
            total: Total count of items
            page: Current page number (1-indexed)
            page_size: Number of items per page
            
        Returns:
            PaginatedData instance with calculated total_pages, has_next, has_prev
        """
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1
        )


class PaginatedResponse(APIResponse[PaginatedData[T]], Generic[T]):
    """Unified paginated response.
    
    Extends APIResponse with PaginatedData as the data type.
    """
    
    pass


class ErrorDetail(BaseModel):
    """Error detail structure for validation and business errors.
    
    Attributes:
        field: Field name that caused the error (optional)
        message: Detailed error message
        code: Error code for programmatic handling
    """
    
    field: Optional[str] = Field(default=None, description="Field that caused error")
    message: str = Field(..., description="Error message")
    code: Optional[str] = Field(default=None, description="Error code")


class ErrorResponse(BaseModel):
    """Standard error response structure.
    
    Used by exception handlers to return consistent error responses.
    
    Attributes:
        code: Error code (e.g., VALIDATION_ERROR, NOT_FOUND)
        message: Human-readable error message
        detail: Additional error details (optional)
        trace_id: Request trace ID for debugging
        timestamp: Error timestamp (UTC)
        request_id: Original request ID (optional)
    """
    
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "detail": {"field": "email", "message": "Invalid email format"},
                "trace_id": "abc123def456",
                "timestamp": "2024-01-01T00:00:00Z",
                "request_id": "req-123"
            }
        }
    )
    
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    detail: Optional[Any] = Field(default=None, description="Error details")
    trace_id: Optional[str] = Field(default=None, description="Request trace ID")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Error timestamp (UTC)"
    )
    request_id: Optional[str] = Field(default=None, description="Original request ID")


class HealthCheckResponse(BaseModel):
    """Health check response structure.
    
    Attributes:
        status: Service status (ok, degraded, error)
        version: Application version
        components: Component health status
    """
    
    status: str = Field(default="ok", description="Service status")
    version: str = Field(..., description="Application version")
    components: Optional[dict[str, str]] = Field(
        default=None,
        description="Component health status"
    )
    uptime_seconds: Optional[float] = Field(
        default=None,
        description="Service uptime in seconds"
    )


def success_response(
    data: T = None,
    message: str = "OK",
    trace_id: str = None
) -> APIResponse[T]:
    """Create a success response.
    
    Args:
        data: Response payload
        message: Success message (default: "OK")
        trace_id: Request trace ID
        
    Returns:
        APIResponse with success status
        
    Example:
        @router.get("/users/{user_id}")
        async def get_user(user_id: str) -> APIResponse[UserResponse]:
            user = await user_service.get(user_id)
            return success_response(data=user, message="User retrieved")
    """
    return APIResponse(
        code="SUCCESS",
        message=message,
        data=data,
        trace_id=trace_id
    )


def created_response(
    data: T = None,
    message: str = "Resource created successfully",
    trace_id: str = None
) -> APIResponse[T]:
    """Create a resource created response.
    
    Args:
        data: Created resource data
        message: Creation message
        trace_id: Request trace ID
        
    Returns:
        APIResponse with creation status
    """
    return APIResponse(
        code="CREATED",
        message=message,
        data=data,
        trace_id=trace_id
    )


def paginated_response(
    items: List[T],
    total: int,
    page: int = 1,
    page_size: int = 20,
    message: str = "OK",
    trace_id: str = None
) -> PaginatedResponse[T]:
    """Create a paginated response.
    
    Args:
        items: List of items for current page
        total: Total count of items
        page: Current page number (1-indexed)
        page_size: Number of items per page
        message: Response message
        trace_id: Request trace ID
        
    Returns:
        PaginatedResponse with paginated data
        
    Example:
        @router.get("/users")
        async def list_users(
            page: int = 1,
            page_size: int = 20
        ) -> PaginatedResponse[UserResponse]:
            users, total = await user_service.list(page, page_size)
            return paginated_response(
                items=users,
                total=total,
                page=page,
                page_size=page_size
            )
    """
    paginated_data = PaginatedData.create(items, total, page, page_size)
    return PaginatedResponse(
        code="SUCCESS",
        message=message,
        data=paginated_data,
        trace_id=trace_id
    )


def error_response(
    code: str,
    message: str,
    detail: Any = None,
    trace_id: str = None,
    request_id: str = None
) -> ErrorResponse:
    """Create an error response.
    
    Args:
        code: Error code
        message: Error message
        detail: Additional error details
        trace_id: Request trace ID
        request_id: Original request ID
        
    Returns:
        ErrorResponse instance
    """
    return ErrorResponse(
        code=code,
        message=message,
        detail=detail,
        trace_id=trace_id,
        request_id=request_id
    )


class PaginationParams(BaseModel):
    """Standard pagination parameters for request queries.
    
    Attributes:
        page: Page number (1-indexed)
        page_size: Number of items per page
        sort_by: Field to sort by (optional)
        sort_order: Sort order (asc/desc)
    """
    
    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")
    sort_by: Optional[str] = Field(default=None, description="Field to sort by")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$", description="Sort order")
    
    @property
    def offset(self) -> int:
        """Calculate offset for database query."""
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        """Get limit for database query (alias for page_size)."""
        return self.page_size
