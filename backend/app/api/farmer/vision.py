# backend/app/api/farmer/vision.py

from fastapi import APIRouter, File, UploadFile, HTTPException, Form
from typing import Optional, List

from app.services.farmer.vision_service import (
    analyze_image,
    get_image_analysis,
    list_images
)

router = APIRouter()


@router.post("/vision/analyze")
async def api_analyze_image(
    file: UploadFile = File(...),
    unit_id: Optional[str] = Form(None),
    tags: Optional[str] = Form(None)
):
    try:
        content = await file.read()
    except Exception:
        raise HTTPException(status_code=400, detail="file_read_error")

    tag_list = tags.split(",") if tags else None
    result = analyze_image(content, unit_id=unit_id, tags=tag_list)
    return result


@router.get("/vision/image/{image_id}")
def api_get_image_analysis(image_id: str):
    res = get_image_analysis(image_id)
    if "error" in res:
        raise HTTPException(status_code=404, detail="not_found")
    return res


@router.get("/vision/images")
def api_list_images(unit_id: Optional[str] = None):
    return list_images(unit_id)
