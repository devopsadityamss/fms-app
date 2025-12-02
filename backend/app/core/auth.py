import requests
import jwt
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings

security = HTTPBearer()

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
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")

    return payload

async def require_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    return verify_token(token)


def supabase_register(email: str, password: str):
    data = {"email": email, "password": password}

    headers = {
        "apikey": settings.SUPABASE_ANON_KEY,
        "Content-Type": "application/json"
    }

    resp = requests.post(f"{settings.SUPABASE_URL}/auth/v1/signup", json=data, headers=headers)

    if resp.status_code != 200:
        raise HTTPException(status_code=400, detail=resp.json())

    return resp.json()


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
