"""
API Routes — Photo Timeline Viewer
---------------------------------

Endpoints:
 - POST   /farmer/photo            -> upload image (multipart/form-data)
 - GET    /farmer/photo/{photo_id} -> metadata for a photo (no raw bytes)
 - GET    /farmer/photo/{photo_id}/image -> raw image bytes (for display/download)
 - DELETE /farmer/photo/{photo_id}
 - GET    /farmer/photos          -> list photos with filters
 - GET    /farmer/photo/timeline  -> timeline feed (recent photos)
"""

from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Query, Response
from typing import Optional, List, Dict, Any

from app.services.farmer import photo_timeline_service as svc

router = APIRouter()


@router.post("/farmer/photo")
async def api_upload_photo(
    file: UploadFile = File(...),
    unit_id: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),         # comma-separated
    notes: Optional[str] = Form(None),
    captured_at: Optional[str] = Form(None),
    run_vision: Optional[bool] = Form(True)
):
    try:
        content = await file.read()
    except Exception:
        raise HTTPException(status_code=400, detail="file_read_error")

    tag_list = [t.strip() for t in tags.split(",")] if tags else []
    rec = svc.add_photo(
        img_bytes=content,
        filename=file.filename,
        unit_id=unit_id,
        tags=tag_list,
        notes=notes,
        captured_at=captured_at,
        run_vision_analysis=run_vision
    )

    # return metadata (no raw bytes)
    meta = {k: v for k, v in rec.items() if k != "bytes"}
    return meta


@router.get("/farmer/photo/{photo_id}")
def api_get_photo(photo_id: str):
    res = svc.get_photo(photo_id)
    if "error" in res:
        raise HTTPException(status_code=404, detail="photo_not_found")
    return res


@router.get("/farmer/photo/{photo_id}/image")
def api_get_photo_image(photo_id: str):
    result = svc.get_photo_bytes(photo_id)
    if not result:
        raise HTTPException(status_code=404, detail="photo_not_found")
    b, content_type, filename = result
    headers = {"Content-Disposition": f'inline; filename="{filename or photo_id}"'}
    return Response(content=b, media_type=content_type, headers=headers)


@router.delete("/farmer/photo/{photo_id}")
def api_delete_photo(photo_id: str):
    ok = svc.delete_photo(photo_id)
    if not ok:
        raise HTTPException(status_code=404, detail="photo_not_found")
    return {"success": True}


@router.get("/farmer/photos")
def api_list_photos(
    unit_id: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    return svc.list_photos(unit_id=unit_id, tag=tag, date_from=date_from, date_to=date_to, limit=limit, offset=offset)


@router.get("/farmer/photo/timeline")
def api_timeline(
    unit_id: Optional[str] = Query(None),
    days_back: Optional[int] = Query(None, ge=1),
    limit: int = Query(50, ge=1, le=500)
):
    return svc.timeline_feed(unit_id=unit_id, days_back=days_back, limit=limit)
