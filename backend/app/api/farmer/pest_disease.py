# backend/app/api/farmer/pest_disease.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from app.services.farmer.pest_disease_service import (
    record_alert,
    get_alert,
    list_alerts_for_unit,
    compute_risk_score_for_unit,
    simulate_forecast_for_unit,
    aggregate_alerts_summary,
    alert_and_notify_if_critical
)

router = APIRouter()

class AlertPayload(BaseModel):
    reporter_id: str
    unit_id: str
    crop: str
    stage: Optional[str] = None
    alert_type: str
    confidence: float
    image_meta: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    location: Optional[Dict[str, float]] = None
    timestamp_iso: Optional[str] = None
    notify: Optional[bool] = False  # if true, and severity high/critical, attempt notification (callback not wired here)

class WeatherPayload(BaseModel):
    temperature: float
    humidity: float
    rainfall_mm: float
    wind_speed: Optional[float] = 5.0

@router.post("/farmer/pest/alert")
def api_record_alert(req: AlertPayload):
    rec = record_alert(
        reporter_id=req.reporter_id,
        unit_id=req.unit_id,
        crop=req.crop,
        stage=req.stage,
        alert_type=req.alert_type,
        confidence=req.confidence,
        image_meta=req.image_meta,
        notes=req.notes,
        location=req.location,
        timestamp_iso=req.timestamp_iso
    )
    if req.notify:
        # best-effort: try to call optional notification callback if available
        try:
            alert_and_notify_if_critical(rec)
        except Exception:
            pass
    return rec

@router.get("/farmer/pest/alert/{alert_id}")
def api_get_alert(alert_id: str):
    res = get_alert(alert_id)
    if not res:
        raise HTTPException(status_code=404, detail="alert_not_found")
    return res

@router.get("/farmer/pest/alerts/{unit_id}")
def api_list_alerts(unit_id: str, since_days: Optional[int] = 30):
    return {"unit_id": unit_id, "alerts": list_alerts_for_unit(unit_id, since_days=since_days or 30)}

@router.post("/farmer/pest/risk/{unit_id}")
def api_risk_for_unit(unit_id: str, weather: Optional[WeatherPayload] = None, recent_days: Optional[int] = 7):
    w = weather.dict() if weather else None
    res = compute_risk_score_for_unit(unit_id, recent_days=recent_days or 7, weather=w)
    return res

@router.post("/farmer/pest/forecast/{unit_id}")
def api_forecast(unit_id: str, days: Optional[int] = 5, baseline_weather: Optional[List[Dict[str, Any]]] = None):
    res = simulate_forecast_for_unit(unit_id, days=days or 5, baseline_weather=baseline_weather)
    return res

@router.get("/farmer/pest/summary")
def api_aggregate(unit_id: Optional[str] = None, since_days: Optional[int] = 30):
    return aggregate_alerts_summary(unit_id=unit_id, since_days=since_days or 30)
