# app/supabase_auth.py
import os
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import httpx
from jose import jwt

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://oubxfwodihdhtrcqgxjz.supabase.co")
JWKS_URL = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"

security = HTTPBearer()
_jwks = None
