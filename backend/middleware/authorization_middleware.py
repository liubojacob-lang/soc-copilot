"""Resource authorization middleware for unified access control."""

from collections.abc import Callable

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from core.logger import get_logger

logger = get_logger(__name__)


class ResourceAuthorizationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for unified resource-level authorization.

    This middleware provides a consistent way to check resource ownership
    and access permissions across all API endpoints.
    """

    # Resource types and their ownership fields
    RESOURCE_CONFIG = {
        # Format: resource_type: { "owner_field": "created_by_user_id", "admin_bypass": True }
        "playbook_runs": {"owner_field": "created_by_user_id", "admin_bypass": True},
        "playbook_definitions": {
            "owner_field": "created_by_user_id",
            "admin_bypass": True,
        },
        "playbook_approvals": {"owner_field": "requester_id", "admin_bypass": True},
        "triggers": {"owner_field": "created_by_user_id", "admin_bypass": True},
        "webhooks": {"owner_field": "created_by_user_id", "admin_bypass": True},
        "api_keys": {"owner_field": "user_id", "admin_bypass": True},
        "secrets": {"owner_field": "created_by_user_id", "admin_bypass": True},
        "assets": {"owner_field": "created_by_user_id", "admin_bypass": True},
        "history": {"owner_field": "user_id", "admin_bypass": True},
    }

    # Paths that require resource authorization
    # NOTE: routes are mounted under /api/v1 (non-/api/v1 /api/* paths are
    # 308-redirected before this middleware sees them), so legacy /api/*
    # prefixes never matched anything. Actual enforcement lives in the
    # endpoint dependencies (require_admin / require_analyst_or_admin);
    # this middleware only annotates request.state for future use.
    PROTECTED_PATHS = {
        "/api/v1/playbook-runs",
        "/api/v1/playbook-definitions",
        "/api/v1/playbook/runs",
        "/api/v1/playbook/definitions",
        "/api/v1/triggers",
        "/api/v1/webhooks",
        "/api/v1/secrets",
        "/api/v1/assets",
        "/api/v1/history",
    }

    # Paths to exclude from authorization
    EXCLUDED_PATHS = {
        "/api/v1/auth",
        "/api/v1/health",
        "/health",
        "/metrics",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/api/v1/admin",  # Admin endpoints have their own authorization
        "/api/v1/audit-logs",  # Audit logs are read-only for auditors
    }

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.resource_config = self.RESOURCE_CONFIG
        self.protected_paths = self.PROTECTED_PATHS
        self.excluded_paths = self.EXCLUDED_PATHS

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and check resource authorization."""
        path = request.url.path
        method = request.method

        # Skip excluded paths
        if any(path.startswith(excluded) for excluded in self.excluded_paths):
            return await call_next(request)

        # Skip non-protected paths
        if not any(path.startswith(protected) for protected in self.protected_paths):
            return await call_next(request)

        # Skip GET requests for list endpoints (handled by query filtering)
        # Only check authorization for specific resource access
        if method == "GET" and self._is_list_endpoint(path):
            return await call_next(request)

        # Get user info from request state
        user_id = getattr(request.state, "user_id", None)
        user_role = getattr(request.state, "user_role", None)

        if not user_id:
            # No user info - let the endpoint handle authentication
            return await call_next(request)

        # Admin bypass - admins can access all resources
        if user_role == "admin":
            return await call_next(request)

        # For resource-specific operations, check ownership
        resource_id = self._extract_resource_id(path)
        resource_type = self._extract_resource_type(path)

        if resource_id and resource_type:
            # Store resource info for endpoint to use
            request.state.resource_id = resource_id
            request.state.resource_type = resource_type
            request.state.require_owner_check = True

        return await call_next(request)

    def _is_list_endpoint(self, path: str) -> bool:
        """Check if the path is a list endpoint (no resource ID)."""
        parts = path.strip("/").split("/")
        # List endpoints have even number of parts: /api/resource
        # Detail endpoints have odd number: /api/resource/id
        if len(parts) == 2:
            return True
        # Check if last part looks like an ID
        if len(parts) >= 3:
            last_part = parts[-1]
            # UUIDs or numeric IDs
            if len(last_part) == 36 and "-" in last_part:
                return False  # UUID - detail endpoint
            if last_part.isdigit():
                return False  # Numeric ID - detail endpoint
            # Actions like "run", "approve", etc.
            if last_part in {"run", "approve", "reject", "cancel", "retry", "clone"}:
                return False
        return True

    def _extract_resource_id(self, path: str) -> str | None:
        """Extract resource ID from path."""
        parts = path.strip("/").split("/")
        if len(parts) >= 3:
            potential_id = parts[-1]
            # Check if it's a UUID
            if len(potential_id) == 36 and "-" in potential_id:
                return potential_id
            # Check if it's a numeric ID
            if potential_id.isdigit():
                return potential_id
        return None

    def _extract_resource_type(self, path: str) -> str | None:
        """Extract resource type from path."""
        parts = path.strip("/").split("/")
        if len(parts) >= 2:
            return parts[1]  # e.g., "playbook-runs"
        return None


def check_resource_ownership(
    resource_type: str,
    resource_owner_id: str,
    current_user_id: str,
    current_user_role: str,
    admin_bypass: bool = True,
) -> bool:
    """
    Check if user has access to a resource.

    Args:
        resource_type: Type of resource (e.g., "playbook_runs")
        resource_owner_id: ID of the resource owner
        current_user_id: ID of the current user
        current_user_role: Role of the current user
        admin_bypass: Whether admins can bypass ownership check

    Returns:
        True if user has access, False otherwise
    """
    # Admin bypass
    if admin_bypass and current_user_role == "admin":
        return True

    # Owner check
    return resource_owner_id == current_user_id


def require_resource_ownership(
    resource_type: str,
    resource_owner_id: str,
    current_user_id: str,
    current_user_role: str,
    admin_bypass: bool = True,
) -> None:
    """
    Require resource ownership, raise HTTPException if not authorized.

    Args:
        resource_type: Type of resource
        resource_owner_id: ID of the resource owner
        current_user_id: ID of the current user
        current_user_role: Role of the current user
        admin_bypass: Whether admins can bypass ownership check

    Raises:
        HTTPException: 403 Forbidden if not authorized
    """
    if not check_resource_ownership(
        resource_type,
        resource_owner_id,
        current_user_id,
        current_user_role,
        admin_bypass,
    ):
        logger.warning(
            f"Resource access denied: user={current_user_id}, role={current_user_role}, "
            f"resource_type={resource_type}, owner={resource_owner_id}"
        )
        raise HTTPException(
            status_code=403, detail="You do not have permission to access this resource"
        )


class ResourceOwnerChecker:
    """
    Helper class for checking resource ownership in endpoints.
    """

    def __init__(self, user_id: str, user_role: str):
        self.user_id = user_id
        self.user_role = user_role

    def can_access(self, resource_owner_id: str, admin_bypass: bool = True) -> bool:
        """Check if user can access a resource."""
        return check_resource_ownership(
            resource_type="resource",
            resource_owner_id=resource_owner_id,
            current_user_id=self.user_id,
            current_user_role=self.user_role,
            admin_bypass=admin_bypass,
        )

    def require_access(self, resource_owner_id: str, admin_bypass: bool = True) -> None:
        """Require access, raise HTTPException if not authorized."""
        require_resource_ownership(
            resource_type="resource",
            resource_owner_id=resource_owner_id,
            current_user_id=self.user_id,
            current_user_role=self.user_role,
            admin_bypass=admin_bypass,
        )

    def is_admin(self) -> bool:
        """Check if user is admin."""
        return self.user_role == "admin"

    def is_owner_or_admin(self, owner_id: str) -> bool:
        """Check if user is owner or admin."""
        return self.user_id == owner_id or self.user_role == "admin"
