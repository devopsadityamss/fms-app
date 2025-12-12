# backend/app/api/farmer/irrigation.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from app.services.farmer.irrigation_service import (
    # === Smart Scheduler (forecast-based) ===
    schedule_irrigation_for_unit,
    get_irrigation_schedule,
    list_all_schedules,

    # === Real-time Logger & Recommender ===
    log_irrigation,
    list_irrigation_logs,
    update_soil_moisture,
    update_weather,
    recommend_irrigation,
    irrigation_pattern_analysis,
    irrigation_summary,
)

router = APIRouter()


# ==========================================
# 1. SMART IRRIGATION SCHEDULER ENDPOINTS
# ==========================================

class ET0Day(BaseModel):
    date: str  # YYYY-MM-DD
    et0_mm: float
    rain_mm: Optional[float] = 0.0


class ScheduleRequest(BaseModel):
    et0_forecast: List[ET0Day]
    start_date_iso: Optional[str] = None
    end_date_iso: Optional[str] = None
    soil_moisture_pct: Optional[float] = None
    system_flow_rate_lph: Optional[float] = 2000.0
    kc_override: Optional[float] = None
    mad: Optional[float] = None
    awc_mm_per_m: Optional[float] = None
    avoid_windows: Optional[List[Dict[str, str]]] = None
    lookahead_days: Optional[int] = 14


@router.post("/irrigation/schedule/{unit_id}")
def api_schedule_irrigation(unit_id: str, req: ScheduleRequest):
    schedule = schedule_irrigation_for_unit(
        unit_id,
        et0_forecast=[d.dict() for d in req.et0_forecast],
        start_date_iso=req.start_date_iso,
        end_date_iso=req.end_date_iso,
        soil_moisture_pct=req.soil_moisture_pct,
        system_flow_rate_lph=req.system_flow_rate_lph or 2000.0,
        kc_override=req.kc_override,
        mad=(req.mad if req.mad is not None else None),
        awc_mm_per_m=(req.awc_mm_per_m if req.awc_mm_per_m is not None else None),
        avoid_windows=req.avoid_windows,
        lookahead_days=(req.lookahead_days or 14)
    )
    if schedule.get("status") == "unit_not_found":
        raise HTTPException(status_code=404, detail="unit_not_found")
    return schedule


@router.get("/irrigation/schedule/{unit_id}")
def api_get_schedule(unit_id: str):
    sch = get_irrigation_schedule(unit_id)
    if not sch:
        raise HTTPException(status_code=404, detail="schedule_not_found")
    return sch


@router.get("/irrigation/schedules")
def api_list_schedules():
    return list_all_schedules()


# ==========================================
# 2. REAL-TIME IRRIGATION LOGGING & RECOMMENDATIONS
# ==========================================

class LogIrrigationPayload(BaseModel):
    method: str
    duration_minutes: float
    water_used_liters: Optional[float] = None
    notes: Optional[str] = None


@router.post("/irrigation/log/{unit_id}")
def api_log_irrigation(unit_id: str, payload: LogIrrigationPayload):
    return log_irrigation(
        unit_id=unit_id,
        method=payload.method,
        duration_minutes=payload.duration_minutes,
        water_used_liters=payload.water_used_liters,
        notes=payload.notes
    )


@router.get("/irrigation/logs/{unit_id}")
def api_list_logs(unit_id: str):
    return {"logs": list_irrigation_logs(unit_id)}


@router.post("/irrigation/moisture/{unit_id}")
def api_update_moisture(unit_id: str, moisture_pct: float):
    return update_soil_moisture(unit_id, moisture_pct)


@router.post("/irrigation/weather/{unit_id}")
def api_update_weather(unit_id: str, rainfall_mm: float, et0: float):
    return update_weather(unit_id, rainfall_mm, et0)


@router.get("/irrigation/recommend/{unit_id}")
def api_recommend(
    unit_id: str,
    crop: str,
    stage: str,
    area_acres: float,
    method: str = "flood"
):
    return recommend_irrigation(unit_id, crop, stage, area_acres, method)


@router.get("/irrigation/analysis/{unit_id}")
def api_analysis(unit_id: str):
    return irrigation_pattern_analysis(unit_id)


@router.get("/irrigation/summary/{unit_id}")
def api_summary(unit_id: str, crop: str, stage: str, area_acres: float):
    return irrigation_summary(unit_id, crop, stage, area_acres)