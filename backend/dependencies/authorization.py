"""Authorization dependencies for FastAPI endpoints."""

from fastapi import Depends, HTTPException, Request

from dependencies.auth import get_current_user
from middleware.authorization_middleware import ResourceOwnerChecker
from models.user import UserModel


def get_resource_checker(
    current_user: UserModel = Depends(get_current_user),
) -> ResourceOwnerChecker:
    """
    Get a ResourceOwnerChecker instance for the current user.

    Usage in endpoints:
        @router.delete("/{resource_id}")
        async def delete_resource(
            resource_id: str,
            checker: ResourceOwnerChecker = Depends(get_resource_checker),
            session: AsyncSession = Depends(get_session),
        ):
            resource = await get_resource_from_db(session, resource_id)
            checker.require_access(resource.created_by_user_id)
            # ... delete resource
    """
    return ResourceOwnerChecker(
        user_id=current_user.id,
        user_role=(
            current_user.role.value
            if hasattr(current_user.role, "value")
            else current_user.role
        ),
    )


def require_owner_or_admin(
    resource_owner_id: str,
    current_user: UserModel = Depends(get_current_user),
) -> None:
    """
    Dependency that requires the current user to be the resource owner or an admin.

    Usage:
        @router.delete("/{resource_id}")
        async def delete_resource(
            resource_id: str,
            session: AsyncSession = Depends(get_session),
            current_user: UserModel = Depends(get_current_user),
            _: None = Depends(lambda: require_owner_or_admin(resource.owner_id, current_user)),
        ):
            # ... delete resource
    """
    user_role = (
        current_user.role.value
        if hasattr(current_user.role, "value")
        else current_user.role
    )
    checker = ResourceOwnerChecker(user_id=current_user.id, user_role=user_role)
    checker.require_access(resource_owner_id)


class ResourceAccess:
    """
    Class-based dependency for resource access control.

    Usage:
        @router.get("/{resource_id}")
        async def get_resource(
            resource_id: str,
            access: ResourceAccess = Depends(ResourceAccess("playbook_runs")),
            session: AsyncSession = Depends(get_session),
        ):
            resource = await get_resource(session, resource_id)
            access.check(resource.created_by_user_id)
            return resource
    """

    def __init__(self, resource_type: str):
        self.resource_type = resource_type

    async def __call__(
        self,
        request: Request,
        current_user: UserModel = Depends(get_current_user),
    ) -> "ResourceAccess":
        """Initialize the dependency with the current user."""
        self.user_id = current_user.id
        self.user_role = (
            current_user.role.value
            if hasattr(current_user.role, "value")
            else current_user.role
        )
        self.request = request
        return self

    def can_access(self, owner_id: str, admin_bypass: bool = True) -> bool:
        """Check if user can access a resource."""
        if admin_bypass and self.user_role == "admin":
            return True
        return self.user_id == owner_id

    def check(self, owner_id: str, admin_bypass: bool = True) -> None:
        """Check access and raise HTTPException if denied."""
        if not self.can_access(owner_id, admin_bypass):
            raise HTTPException(
                status_code=403,
                detail=f"You do not have permission to access this {self.resource_type}",
            )

    def is_admin(self) -> bool:
        """Check if user is admin."""
        return self.user_role == "admin"

    def is_owner_or_admin(self, owner_id: str) -> bool:
        """Check if user is owner or admin."""
        return self.user_id == owner_id or self.user_role == "admin"
