import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
from starlette.requests import Request
from ..core.config import settings

security = HTTPBearer()

async def require_user(request: Request, auth=Depends(security)):
    token = auth.credentials
    try:
        # Supabase JWT uses HS256 with the anon key / service key depending on config
        # For server-side validation we should use the SERVICE_ROLE KEY normally.
        payload = jwt.decode(token, settings.SUPABASE_ANON_KEY, algorithms=["HS256"])
        request.state.user_id = payload.get("sub")
        return payload
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
