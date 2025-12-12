# backend/app/api/farmer/future_risk.py

from fastapi import APIRouter, Query, Body, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.services.farmer.future_risk_service import simulate_future_risk

router = APIRouter()

class WeatherDayOverride(BaseModel):
    temp: Optional[float] = None
    rain_mm: Optional[float] = None
    humidity: Optional[float] = None

class FutureRiskSimRequest(BaseModel):
    days: Optional[int] = 7
    farmer_id: Optional[str] = None
    crop: Optional[str] = None
    stage: Optional[str] = None
    weather_forecast_override: Optional[List[WeatherDayOverride]] = None
    schedule_override: Optional[Dict[str, Any]] = None
    behaviour_modifier: Optional[Dict[str, Any]] = None
    simulate_execute_plan: Optional[bool] = False
    base_seed_risk: Optional[float] = None

@router.get("/future-risk/{unit_id}")
def api_future_risk(unit_id: int,
                    days: int = Query(7),
                    farmer_id: Optional[str] = Query(None),
                    crop: Optional[str] = Query(None),
                    stage: Optional[str] = Query(None),
                    simulate_execute_plan: bool = Query(False)):
    """
    Returns a default 7-day future risk projection (or days specified).
    """
    try:
        res = simulate_future_risk(unit_id=unit_id, days=days, farmer_id=farmer_id, crop=crop, stage=stage, simulate_execute_plan=simulate_execute_plan)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/future-risk/{unit_id}/3-day")
def api_future_risk_3(unit_id: int, farmer_id: Optional[str] = Query(None), crop: Optional[str] = Query(None), stage: Optional[str] = Query(None)):
    try:
        res = simulate_future_risk(unit_id=unit_id, days=3, farmer_id=farmer_id, crop=crop, stage=stage)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/future-risk/{unit_id}/simulate")
def api_future_risk_simulate(unit_id: int, payload: FutureRiskSimRequest = Body(...)):
    body = payload.dict()
    # convert weather overrides to plain dicts expected by service
    wf = None
    if body.get("weather_forecast_override"):
        wf = []
        for w in body.get("weather_forecast_override"):
            wf.append({"temp": w.get("temp"), "rain_mm": w.get("rain_mm"), "humidity": w.get("humidity")})
    try:
        res = simulate_future_risk(
            unit_id=unit_id,
            days=body.get("days", 7),
            farmer_id=body.get("farmer_id"),
            crop=body.get("crop"),
            stage=body.get("stage"),
            weather_forecast_override=wf,
            schedule_override=body.get("schedule_override"),
            behaviour_modifier=body.get("behaviour_modifier"),
            simulate_execute_plan=bool(body.get("simulate_execute_plan", False)),
            base_seed_risk=body.get("base_seed_risk")
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
