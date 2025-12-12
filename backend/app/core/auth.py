# backend/app/core/auth.py

import requests
import jwt
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings

# ---------------------------
# NEW IMPORTS ADDED FOR RBAC
# ---------------------------
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.role import Role, Permission, RolePermission, UserRole
from app.models.profile import Profile

security = HTTPBearer()


# ------------------------------------------------
# SUPABASE TOKEN VERIFICATION (UNCHANGED)
# ------------------------------------------------
def verify_token(token: str):
    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_exp": True, "verify_aud": False},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    return payload


async def require_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    return verify_token(token)


# ------------------------------------------------
# SUPABASE REGISTER (UNCHANGED)
# ------------------------------------------------
def supabase_register(email: str, password: str):
    data = {"email": email, "password": password}

    headers = {
        "apikey": settings.SUPABASE_ANON_KEY,
        "Content-Type": "application/json"
    }

    resp = requests.post(
        f"{settings.SUPABASE_URL}/auth/v1/signup",
        json=data,
        headers=headers
    )

    if resp.status_code != 200:
        raise HTTPException(status_code=400, detail=resp.json())

    return resp.json()


# ------------------------------------------------
# SUPABASE LOGIN (UNCHANGED)
# ------------------------------------------------
def supabase_login(email: str, password: str):
    data = {"email": email, "password": password}

    headers = {
        "apikey": settings.SUPABASE_ANON_KEY,
        "Content-Type": "application/json"
    }

    resp = requests.post(
        f"{settings.SUPABASE_URL}/auth/v1/token?grant_type=password",
        json=data,
        headers=headers,
    )

    if resp.status_code != 200:
        raise HTTPException(status_code=400, detail=resp.json())

    return resp.json()


# ------------------------------------------------
# BACKEND JWT DECODING (NEW)
# ------------------------------------------------
def decode_backend_token(token: str):
    """Decode backend-issued JWT (RBAC-enabled)."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        return payload
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid backend token")


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Decode backend JWT that contains:
    - user_id
    - roles
    - active_role
    """
    token = credentials.credentials
    return decode_backend_token(token)


# ------------------------------------------------
# RBAC PERMISSION SYSTEM (NEW)
# ------------------------------------------------

async def get_permissions_for_role(role_name: str, db: AsyncSession):
    """Return list of permission names for a given role."""
    role = await db.scalar(select(Role).where(Role.name == role_name))
    if not role:
        return []

    perm_rows = await db.scalars(
        select(Permission)
        .join(RolePermission)
        .where(RolePermission.role_id == role.id)
    )

    return [p.name for p in perm_rows.all()]


def require_permission(required_permission: str):
    """
    Dependency to enforce RBAC.
    Only user's ACTIVE role is checked.
    """

    async def wrapper(
        user=Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        active_role = user.get("active_role")

        if not active_role:
            raise HTTPException(403, "No active role selected")

        permissions = await get_permissions_for_role(active_role, db)

        if required_permission not in permissions:
            raise HTTPException(
                403,
                f"Permission denied: missing '{required_permission}'",
            )

        return user

    return wrapper


# ------------------------------------------------
# BACKEND TOKEN CREATOR (YOU ADDED THIS — KEPT)
# ------------------------------------------------
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        to_encode["exp"] = datetime.utcnow() + expires_delta
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
