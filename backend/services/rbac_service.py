"""RBAC service for role and permission management and database seeding (T3.6)."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from models.rbac import Permission, Role, role_permission

logger = get_logger(__name__)

# Canonical system permissions definition (resource, action, description)
SYSTEM_PERMISSIONS = [
    ("assets", "read", "Read access to asset inventory"),
    ("assets", "write", "Create and update asset items"),
    ("assets", "delete", "Delete assets from inventory"),
    ("ioc_hits", "read", "View IOC detection hits"),
    ("ioc_hits", "write", "Create or resolve IOC hits"),
    ("history", "read", "View security event history"),
    ("alerts", "analyze", "Analyze security alerts via AI/rule engines"),
    ("timeline", "build", "Reconstruct incident timelines"),
    ("reports", "generate", "Generate incident and executive reports"),
    ("playbook", "read", "View playbook definitions and runs"),
    ("playbook", "write", "Create, edit and publish playbooks"),
    ("playbook", "run", "Execute playbook instances"),
    ("playbook", "resume", "Approve and resume paused playbooks"),
    ("ti", "query", "Query threat intelligence providers and cache"),
    ("audit_logs", "read", "Read system audit logs"),
    ("admin", "read", "Access administration settings and metrics"),
    ("admin", "write", "Modify administration settings and secrets"),
    ("users", "read", "List and view system users"),
    ("users", "write", "Create, update and manage system users"),
]

# Role to permission codes mapping
SYSTEM_ROLE_PERMISSIONS: dict[str, list[tuple[str, str]]] = {
    "admin": [(res, act) for res, act, _ in SYSTEM_PERMISSIONS],
    "analyst": [
        ("assets", "read"),
        ("assets", "write"),
        ("ioc_hits", "read"),
        ("ioc_hits", "write"),
        ("history", "read"),
        ("alerts", "analyze"),
        ("timeline", "build"),
        ("reports", "generate"),
        ("playbook", "read"),
        ("playbook", "write"),
        ("playbook", "run"),
        ("playbook", "resume"),
        ("ti", "query"),
    ],
    "auditor": [
        ("assets", "read"),
        ("ioc_hits", "read"),
        ("history", "read"),
        ("alerts", "analyze"),
        ("timeline", "build"),
        ("reports", "generate"),
        ("playbook", "read"),
        ("ti", "query"),
        ("audit_logs", "read"),
    ],
}


async def seed_rbac(session: AsyncSession) -> tuple[int, int]:
    """Seed initial system roles and permissions into database idempotently.

    Returns:
        tuple of (roles_seeded, permissions_seeded)
    """
    # 1. Seed permissions
    perm_cache: dict[str, Permission] = {}
    perms_created = 0

    # Query existing permissions
    existing_perms_res = await session.execute(select(Permission))
    existing_perms = {p.code: p for p in existing_perms_res.scalars().all()}
    perm_cache.update(existing_perms)

    for resource, action, desc in SYSTEM_PERMISSIONS:
        code = f"{resource}:{action}"
        if code not in perm_cache:
            perm = Permission(
                id=str(uuid.uuid4()),
                code=code,
                resource=resource,
                action=action,
                description=desc,
            )
            session.add(perm)
            perm_cache[code] = perm
            perms_created += 1

    await session.flush()

    # 2. Seed system roles
    roles_created = 0
    existing_roles_res = await session.execute(select(Role))
    existing_roles = {r.name: r for r in existing_roles_res.scalars().all()}

    role_objs: dict[str, Role] = dict(existing_roles)

    role_descriptions = {
        "admin": "Full system administrator with unrestricted privileges",
        "analyst": "Security analyst with alert triage, hunting and playbook execution privileges",
        "auditor": "Compliance auditor with read-only inspection and audit log privileges",
    }

    for role_name in ("admin", "analyst", "auditor"):
        if role_name not in role_objs:
            role = Role(
                id=str(uuid.uuid4()),
                name=role_name,
                description=role_descriptions.get(role_name),
                is_system=True,
            )
            session.add(role)
            role_objs[role_name] = role
            roles_created += 1

    await session.flush()

    # 3. Seed role_permissions joins
    existing_links_res = await session.execute(
        select(role_permission.c.role_id, role_permission.c.permission_id)
    )
    existing_links = set(existing_links_res.all())

    new_links = 0
    for role_name, allowed_perms in SYSTEM_ROLE_PERMISSIONS.items():
        role = role_objs.get(role_name)
        if not role:
            continue
        for res, act in allowed_perms:
            code = f"{res}:{act}"
            perm = perm_cache.get(code)
            if perm and (role.id, perm.id) not in existing_links:
                await session.execute(
                    role_permission.insert().values(
                        role_id=role.id,
                        permission_id=perm.id,
                    )
                )
                existing_links.add((role.id, perm.id))
                new_links += 1

    await session.commit()
    logger.info(
        f"RBAC seeding completed: {roles_created} roles created, "
        f"{perms_created} perms created, {new_links} links established"
    )
    return roles_created, perms_created
