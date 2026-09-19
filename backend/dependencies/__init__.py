"""Authentication and authorization dependencies."""

from dependencies.auth import (
    get_api_key_user,
    get_current_user,
    get_current_user_optional,
    require_admin,
    require_analyst,
    require_role,
)

# dependencies.authorization was removed (T3.5): its resource-ownership
# helpers had zero callers — enforcement lives in the endpoint dependencies.

__all__ = [
    "get_api_key_user",
    "get_current_user",
    "get_current_user_optional",
    "require_admin",
    "require_analyst",
    "require_role",
]
