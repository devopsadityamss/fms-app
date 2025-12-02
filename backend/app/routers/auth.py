from fastapi import APIRouter
from pydantic import BaseModel
from app.core.auth import supabase_register, supabase_login

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/register")
async def register_user(req: RegisterRequest):
    return supabase_register(req.email, req.password)


@router.post("/login")
async def login_user(req: LoginRequest):
    return supabase_login(req.email, req.password)
