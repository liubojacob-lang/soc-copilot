"""Authentication and authorization dependencies."""

from dependencies.auth import (
    get_api_key_user,
    get_current_user,
    get_current_user_optional,
    require_admin,
    require_analyst,
    require_role,
)
from dependencies.authorization import (
    ResourceAccess,
    get_resource_checker,
    require_owner_or_admin,
)

__all__ = [
    "ResourceAccess",
    "get_api_key_user",
    "get_current_user",
    "get_current_user_optional",
    "get_resource_checker",
    "require_admin",
    "require_analyst",
    "require_owner_or_admin",
    "require_role",
]
