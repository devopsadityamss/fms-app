# backend/app/api/farmer/recommendations.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.services.farmer.recommendation_engine_service import (
    generate_recommendations_for_unit
)

router = APIRouter()


class RecommendRequest(BaseModel):
    weather_now: Optional[Dict[str, Any]] = None
    inputs_snapshot: Optional[Dict[str, Any]] = None


@router.post("/recommend/{unit_id}")
def api_recommend(unit_id: str, req: RecommendRequest):
    result = generate_recommendations_for_unit(
        unit_id,
        weather_now=req.weather_now,
        inputs_snapshot=req.inputs_snapshot
    )
    if result.get("status") == "unit_not_found":
        raise HTTPException(status_code=404, detail="unit_not_found")
    return result
