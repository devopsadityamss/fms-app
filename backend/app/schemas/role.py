# backend/app/schemas/role.py

from pydantic import BaseModel
from uuid import UUID


# -----------------------
# ROLE
# -----------------------

class RoleBase(BaseModel):
    name: str
    description: str | None = None


class RoleCreate(RoleBase):
    pass


class Role(RoleBase):
    id: int

    class Config:
        from_attributes = True


# -----------------------
# PERMISSION
# -----------------------

class PermissionBase(BaseModel):
    name: str
    description: str | None = None


class PermissionCreate(PermissionBase):
    pass


class Permission(PermissionBase):
    id: int

    class Config:
        from_attributes = True


# -----------------------
# USER ↔ ROLE ASSIGNMENT
# -----------------------

class UserRoleAssign(BaseModel):
    user_id: UUID
    role_id: int
