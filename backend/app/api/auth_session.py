# backend/app/api/auth_session.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import timedelta
from pydantic import BaseModel

from app.core.database import get_db
from app.models.profile import Profile
from app.models.role import UserRole, Role
from app.core.auth import create_access_token

router = APIRouter(prefix="/auth", tags=["Auth Session"])


class BackendSessionCreate(BaseModel):
    user_id: str
    active_role: str


# ============================================================
# ADDED: Proper request body model for create-profile
# ============================================================
from uuid import UUID

class ProfileCreate(BaseModel):
    id: UUID
    email: str
    full_name: str


# ============================================================
# FIXED: create-profile (now accepts JSON, validates UUID,
#        prevents duplicate creation)
# ============================================================
@router.post("/create-profile")
async def create_profile(payload: ProfileCreate, db: AsyncSession = Depends(get_db)):
    from datetime import datetime

    # Check if profile already exists
    existing = await db.scalar(select(Profile).where(Profile.id == payload.id))
    if existing:
        return {"status": "already_exists"}

    profile = Profile(
        id=payload.id,
        email=payload.email,
        full_name=payload.full_name,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(profile)
    await db.commit()
    return {"status": "profile created"}


# ============================================================
# Existing endpoint — untouched
# ============================================================
@router.post("/create-session")
async def create_session(payload: BackendSessionCreate, db: AsyncSession = Depends(get_db)):
    user_id = payload.user_id
    active_role = payload.active_role

    # 1. Check user exists
    user = await db.scalar(select(Profile).where(Profile.id == user_id))
    if not user:
        raise HTTPException(404, "User not found")

    # 2. Fetch all user roles
    role_mappings = await db.scalars(select(UserRole).where(UserRole.user_id == user_id))
    role_mappings = list(role_mappings)
    role_ids = [rm.role_id for rm in role_mappings]

    roles = await db.scalars(select(Role).where(Role.id.in_(role_ids)))
    roles = [r.name for r in roles]

    if active_role not in roles:
        raise HTTPException(400, "Active role not assigned to user")

    # 3. Create backend JWT
    token_data = {
        "user_id": user_id,
        "active_role": active_role,
        "roles": roles,
    }

    token = create_access_token(
        data=token_data,
        expires_delta=timedelta(days=7)
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "roles": roles,
        "active_role": active_role,
    }
