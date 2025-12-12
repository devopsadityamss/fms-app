# backend/app/api/rbac.py

print("LOADED RBAC FILE:", __file__)
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel

class RoleSwitchRequest(BaseModel):
    user_id: str
    new_active_role: str


from app.core.database import get_db
from app.models.role import Role, Permission, RolePermission, UserRole
from app.models.profile import Profile

# ---- IMPORTANT FIX: avoid name collision between schema Role and model Role ----
from app.schemas.role import (
    RoleCreate, Role as RoleSchema,
    PermissionCreate, Permission as PermissionSchema,
    UserRoleAssign
)

router = APIRouter(prefix="/rbac", tags=["RBAC"])


# -------------------------
# CREATE ROLE
# -------------------------

@router.post("/roles", response_model=RoleSchema)
async def create_role(role_in: RoleCreate, db: AsyncSession = Depends(get_db)):
    role = Role(name=role_in.name, description=role_in.description)
    db.add(role)
    await db.commit()
    await db.refresh(role)
    return role


# -------------------------
# CREATE PERMISSION
# -------------------------

@router.post("/permissions", response_model=PermissionSchema)
async def create_permission(perm_in: PermissionCreate, db: AsyncSession = Depends(get_db)):
    perm = Permission(name=perm_in.name, description=perm_in.description)
    db.add(perm)
    await db.commit()
    await db.refresh(perm)
    return perm


# -------------------------
# ASSIGN ROLE TO USER
# -------------------------

@router.post("/assign-role")
async def assign_role(data: UserRoleAssign, db: AsyncSession = Depends(get_db)):

    # check user exists
    user = await db.scalar(select(Profile).where(Profile.id == data.user_id))
    if not user:
        raise HTTPException(404, "User not found")

    # check role exists
    role = await db.scalar(select(Role).where(Role.id == data.role_id))
    if not role:
        raise HTTPException(404, "Role not found")

    mapping = UserRole(user_id=data.user_id, role_id=data.role_id)
    db.add(mapping)
    await db.commit()
    return {"status": "role assigned"}


# -------------------------
# GET ALL ROLES
# -------------------------

@router.get("/roles", response_model=list[RoleSchema])
async def list_roles(db: AsyncSession = Depends(get_db)):
    roles = await db.scalars(select(Role))
    return roles.all()


# -------------------------
# GET PERMISSIONS OF A ROLE
# -------------------------

@router.get("/roles/{role_id}/permissions")
async def role_permissions(role_id: int, db: AsyncSession = Depends(get_db)):
    perms = await db.scalars(
        select(Permission)
        .join(RolePermission)
        .where(RolePermission.role_id == role_id)
    )
    return perms.all()


# -------------------------
# GET ALL ROLES FOR A USER
# -------------------------

@router.get("/user/{user_id}/roles")
async def get_user_roles(user_id: str, db: AsyncSession = Depends(get_db)):
    try:
        uid = UUID(user_id)
    except ValueError:
        raise HTTPException(400, "Invalid user_id format")

    user = await db.scalar(select(Profile).where(Profile.id == uid))
    if not user:
        new_profile = Profile(
            id=uid,
            email="",
            full_name="",
            created_at=datetime.utcnow()
        )
        db.add(new_profile)
        await db.commit()
        return {"roles": []}
    
    role_mappings = await db.scalars(
        select(UserRole).where(UserRole.user_id == uid)
    )
    role_ids = [rm.role_id for rm in role_mappings]

    if not role_ids:
        return {"roles": []}

    roles = await db.scalars(select(Role).where(Role.id.in_(role_ids)))

    return {"roles": [r.name for r in roles.all()]}


# -------------------------
# GET PERMISSIONS FOR ACTIVE ROLE
# -------------------------

@router.get("/active-role/{role_name}/permissions")
async def get_role_permissions(role_name: str, db: AsyncSession = Depends(get_db)):
    role = await db.scalar(select(Role).where(Role.name == role_name))
    if not role:
        raise HTTPException(404, "Role not found")

    perm_rows = await db.scalars(
        select(Permission)
        .join(RolePermission)
        .where(RolePermission.role_id == role.id)
    )

    return {"permissions": [p.name for p in perm_rows]}


# -------------------------
# SWITCH ACTIVE ROLE (issue new JWT)
# -------------------------

@router.post("/switch-role")
async def switch_role(
    data: RoleSwitchRequest,
    db: AsyncSession = Depends(get_db),
):
    user_id = data.user_id
    new_active_role = data.new_active_role

    # 1. Verify role belongs to user
    role_mappings = await db.scalars(
        select(UserRole).where(UserRole.user_id == user_id)
    )
    role_ids = [rm.role_id for rm in role_mappings]

    roles = await db.scalars(select(Role).where(Role.id.in_(role_ids)))
    role_names = [r.name for r in roles]

    if new_active_role not in role_names:
        raise HTTPException(400, "User does not have this role")

    # 2. Create new backend session JWT
    from app.core.auth import create_access_token
    token_data = {
        "user_id": user_id,
        "active_role": new_active_role,
        "roles": role_names,
    }

    token = create_access_token(data=token_data)

    return {
        "access_token": token,
        "token_type": "bearer",
        "active_role": new_active_role,
    }



# -------------------------
# BULK ASSIGN ROLES — UPDATED & IMPROVED VERSION
# -------------------------

@router.post("/assign-roles-bulk")
async def assign_roles_bulk(data: dict, db: AsyncSession = Depends(get_db)):
    user_id = data.get("user_id")
    role_ids = data.get("role_ids", [])
    if not user_id or not role_ids:
        raise HTTPException(400, "user_id and role_ids are required")
    try:
        uid = UUID(user_id)
    except ValueError:
        raise HTTPException(400, "Invalid user_id format")

    # Check user exists
    user = await db.scalar(select(Profile).where(Profile.id == uid))
    if not user:
        raise HTTPException(404, "User not found")

    # Validate all role_ids exist
    existing_role_ids = await db.scalars(select(Role.id))
    valid_ids = {r for r in existing_role_ids}
    for r in role_ids:
        if r not in valid_ids:
            raise HTTPException(400, f"Invalid role_id {r}")

    # Avoid duplicate assignments
    existing_rows = await db.scalars(
        select(UserRole.role_id).where(UserRole.user_id == uid)
    )
    existing_ids = set(existing_rows)

    for role_id in role_ids:
        if role_id not in existing_ids:
            db.add(UserRole(user_id=uid, role_id=role_id))

    await db.commit()

    # Return role NAMES instead of just IDs (much more useful)
    assigned_roles = await db.scalars(
        select(Role).where(Role.id.in_(role_ids))
    )
    assigned_names = [r.name for r in assigned_roles]

    return {
        "status": "roles assigned",
        "roles": assigned_names
    }