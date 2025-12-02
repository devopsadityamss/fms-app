# This example expects environment variables SUPABASE_URL and SUPABASE_SERVICE_KEY
from fastapi import APIRouter, UploadFile, File, HTTPException
from supabase import create_client
import os

router = APIRouter(prefix="/upload", tags=["upload"])

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise RuntimeError("Set SUPABASE env vars")

sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

@router.post("/")
async def upload_file(file: UploadFile = File(...)):
    content = await file.read()
    path = f"attachments/{file.filename}"
    res = sb.storage.from_('attachments').upload(path, content)
    if res.get('error'):
        raise HTTPException(status_code=500, detail=res['error'])
    public = sb.storage.from_('attachments').get_public_url(path)
    return {"path": path, "public_url": public}
