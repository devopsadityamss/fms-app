# backend/app/api/farmer/task_prioritization.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.services.farmer.task_prioritization_service import (
    prioritize_tasks_for_unit,
    prioritize_tasks_for_fleet
)

router = APIRouter()


class WeatherPayload(BaseModel):
    temp_c_max: Optional[float] = None
    temp_c_min: Optional[float] = None
    rain_mm_24h: Optional[float] = None
    humidity_pct: Optional[float] = None


class InputSnapshotPayload(BaseModel):
    seed_kg_applied: Optional[float] = None
    fertilizer_applied: Optional[Dict[str, float]] = None
    last_pesticide_date: Optional[str] = None


class UnitTaskRequest(BaseModel):
    weather_now: Optional[WeatherPayload] = None
    inputs_snapshot: Optional[InputSnapshotPayload] = None
    crop_stage_name: Optional[str] = None


@router.post("/tasks/prioritize/{unit_id}")
def api_prioritize_unit(unit_id: str, req: UnitTaskRequest):
    res = prioritize_tasks_for_unit(
        unit_id,
        weather_now=(req.weather_now.dict() if req.weather_now else None),
        inputs_snapshot=(req.inputs_snapshot.dict() if req.inputs_snapshot else None),
        crop_stage_name=req.crop_stage_name
    )
    if res.get("status") == "unit_not_found":
        raise HTTPException(status_code=404, detail="unit_not_found")
    return res


@router.post("/tasks/prioritize/fleet")
def api_prioritize_fleet(payload: Dict[str, Any]):
    return prioritize_tasks_for_fleet(
        weather_map=payload.get("weather_map"),
        inputs_snapshots=payload.get("inputs_snapshots"),
        stage_map=payload.get("stage_map")
    )
