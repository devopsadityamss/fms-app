# backend/app/api/farmer/vision_timeline.py

from fastapi import APIRouter, HTTPException
from typing import Optional

from app.services.farmer.timeline_service import get_timeline_for_unit

router = APIRouter()


@router.get("/vision/timeline/{unit_id}")
def api_vision_timeline(unit_id: str, limit: int = 50):
    res = get_timeline_for_unit(unit_id, types=["vision_analysis"], limit=limit)
    if res.get("status") == "unit_not_found":
        raise HTTPException(status_code=404, detail="unit_not_found")
    return res
