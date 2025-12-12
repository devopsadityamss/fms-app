# backend/app/api/farmer/schedule.py

from fastapi import APIRouter, Query, Body, HTTPException
from typing import Optional, Dict, Any
from pydantic import BaseModel

from app.services.farmer.schedule_service import generate_schedule

router = APIRouter()

class ScheduleRequest(BaseModel):
    farmer_id: Optional[str] = None
    crop: Optional[str] = None
    stage: Optional[str] = None
    area_ha: Optional[float] = None
    expected_yield_t_per_ha: Optional[float] = None
    max_today_actions: Optional[int] = None

@router.get("/schedule/{unit_id}")
def api_get_schedule(unit_id: int,
                     farmer_id: Optional[str] = Query(None),
                     crop: Optional[str] = Query(None),
                     stage: Optional[str] = Query(None),
                     area_ha: Optional[float] = Query(None),
                     expected_yield_t_per_ha: Optional[float] = Query(None),
                     max_today_actions: Optional[int] = Query(None)):
    """
    Returns a schedule grouped into today / next_3_days / next_7_days.
    """
    try:
        schedule = generate_schedule(unit_id=unit_id, farmer_id=farmer_id, crop=crop, stage=stage, area_ha=area_ha, expected_yield_t_per_ha=expected_yield_t_per_ha, max_today_actions=max_today_actions)
        return schedule
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/schedule/{unit_id}/evaluate")
def api_evaluate_schedule(unit_id: int, payload: ScheduleRequest = Body(...)):
    body = payload.dict()
    try:
        schedule = generate_schedule(unit_id=unit_id, farmer_id=body.get("farmer_id"), crop=body.get("crop"), stage=body.get("stage"), area_ha=body.get("area_ha"), expected_yield_t_per_ha=body.get("expected_yield_t_per_ha"), max_today_actions=body.get("max_today_actions"))
        return schedule
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
