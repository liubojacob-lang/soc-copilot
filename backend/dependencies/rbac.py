"""Fine-grained RBAC dependency helpers."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status

from dependencies.auth import get_current_user


def require_permission(permission_code: str):
    """FastAPI dependency factory for permission checks.

    Note: this implementation stays backward-compatible by allowing admin role.
    For full enforcement, map user->role->permissions in DB and cache the result.
    """

    async def checker(current_user=Depends(get_current_user)):
        role = getattr(current_user, "role", "analyst")
        role_value = role.value if hasattr(role, "value") else str(role)

        # backward-compatible bridge: admin has all permissions
        if role_value == "admin":
            return

        # placeholder: for now, require explicit permission list on user model if present
        permissions = getattr(current_user, "permissions", []) or []
        if permission_code not in permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {permission_code}",
            )

    return checker
