# backend/app/core/seed_rbac.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.role import Role, Permission, RolePermission


DEFAULT_ROLES = [
    ("admin", "System admin"),
    ("farmer", "Farmer user"),
    ("worker", "Farm worker"),
    ("trader", "Crop trader"),
    ("service_provider", "General service provider"),
    ("gov", "Government officer"),
]

DEFAULT_PERMISSIONS = [
    ("manage_farm", "Can manage farm data"),
    ("manage_tasks", "Can create/update tasks"),
    ("view_tasks", "View tasks assigned"),
    ("create_listing", "Create marketplace listing"),
    ("accept_booking", "Accept service bookings"),
    ("manage_users", "Admin permissions"),
]


# Map which roles get which permissions
ROLE_PERMISSION_MAP = {
    "admin": ["manage_users", "manage_farm", "manage_tasks", "create_listing", "accept_booking"],
    "farmer": ["manage_farm", "manage_tasks", "create_listing"],
    "worker": ["view_tasks"],
    "trader": ["create_listing"],
    "service_provider": ["accept_booking"],
    "gov": [],   # pending
}


async def seed_rbac(db: AsyncSession):

    # 1. Seed Roles
    for name, desc in DEFAULT_ROLES:
        exists = await db.scalar(select(Role).where(Role.name == name))
        if not exists:
            db.add(Role(name=name, description=desc))

    # 2. Seed Permissions
    for name, desc in DEFAULT_PERMISSIONS:
        exists = await db.scalar(select(Permission).where(Permission.name == name))
        if not exists:
            db.add(Permission(name=name, description=desc))

    await db.commit()

    # 3. Link Roles ↔ Permissions
    roles = {r.name: r for r in (await db.scalars(select(Role))).all()}
    perms = {p.name: p for p in (await db.scalars(select(Permission))).all()}

    for role_name, perm_names in ROLE_PERMISSION_MAP.items():
        role = roles[role_name]
        for perm_name in perm_names:
            perm = perms[perm_name]

            exists = await db.scalar(
                select(RolePermission).where(
                    RolePermission.role_id == role.id,
                    RolePermission.permission_id == perm.id
                )
            )
            if not exists:
                db.add(RolePermission(role_id=role.id, permission_id=perm.id))

    await db.commit()

    print("RBAC seeded successfully")
