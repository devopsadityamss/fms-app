"""
API Routes — Canopy Coverage Estimation
--------------------------------------

Endpoints:
 - POST /farmer/canopy/from-image         → upload image (multipart)
 - POST /farmer/canopy/from-photo/{id}    → estimate using existing photo_timeline image
 - GET  /farmer/canopy/{canopy_id}        → get a single canopy estimation
 - GET  /farmer/canopy                    → list estimations for a unit
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
from typing import Optional
from app.services.farmer import canopy_estimation_service as svc

router = APIRouter()


@router.post("/farmer/canopy/from-image")
async def api_canopy_from_image(
    file: UploadFile = File(...),
    unit_id: Optional[str] = Form(None),
    tags: Optional[str] = Form(None)
):
    try:
        content = await file.read()
    except:
        raise HTTPException(status_code=400, detail="file_read_error")

    tag_list = [t.strip() for t in tags.split(",")] if tags else []

    result = svc.estimate_canopy_from_bytes(
        img_bytes=content,
        unit_id=unit_id,
        tags=tag_list
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/farmer/canopy/from-photo/{photo_id}")
def api_canopy_from_photo(photo_id: str, unit_id: Optional[str] = Query(None)):
    result = svc.estimate_canopy_from_photo_id(photo_id, unit_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/farmer/canopy/{canopy_id}")
def api_get_canopy(canopy_id: str):
    result = svc.get_canopy_record(canopy_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail="not_found")
    return result


@router.get("/farmer/canopy")
def api_list_canopy(unit_id: Optional[str] = Query(None)):
    return svc.list_canopy_records(unit_id)
