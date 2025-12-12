# backend/app/api/farmer/risk_alerts.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from app.services.farmer.risk_alerts_service import (
    evaluate_risks_for_unit,
    evaluate_risks_for_fleet,
    list_alerts,
    acknowledge_alert,
    record_incident,
    list_incidents
)

router = APIRouter()


# Payloads
class WeatherNow(BaseModel):
    rain_mm_24h: Optional[float] = None
    temp_c_max: Optional[float] = None
    temp_c_min: Optional[float] = None
    humidity_pct: Optional[float] = None


class InputsSnapshot(BaseModel):
    seed_kg_applied: Optional[float] = None
    fertilizer_applied: Optional[Dict[str, float]] = None
    last_pesticide_date: Optional[str] = None


class UnitEvaluateRequest(BaseModel):
    weather_now: Optional[WeatherNow] = None
    lookback_weather: Optional[List[Dict[str, Any]]] = None
    inputs_snapshot: Optional[InputsSnapshot] = None
    soil_quality: Optional[Dict[str, Any]] = None
    crop_stage_name: Optional[str] = None
    historical_incidents: Optional[List[Dict[str, Any]]] = None
    auto_record: Optional[bool] = True


# Endpoints
@router.post("/alerts/evaluate/{unit_id}")
def api_evaluate_unit(unit_id: str, req: UnitEvaluateRequest):
    res = evaluate_risks_for_unit(
        unit_id,
        weather_now=(req.weather_now.dict() if req.weather_now else None),
        lookback_weather=req.lookback_weather,
        inputs_snapshot=(req.inputs_snapshot.dict() if req.inputs_snapshot else None),
        soil_quality=req.soil_quality,
        crop_stage_name=req.crop_stage_name,
        historical_incidents=req.historical_incidents,
        auto_record=req.auto_record
    )
    if res.get("status") == "unit_not_found":
        raise HTTPException(status_code=404, detail="unit_not_found")
    return res


@router.post("/alerts/evaluate/fleet")
def api_evaluate_fleet(payload: Dict[str, Any]):
    """
    Accepts maps:
      weather_map, lookback_weather_map, inputs_snapshots, soil_map, stage_map
    """
    res = evaluate_risks_for_fleet(
        weather_map=payload.get("weather_map"),
        lookback_weather_map=payload.get("lookback_weather_map"),
        inputs_snapshots=payload.get("inputs_snapshots"),
        soil_map=payload.get("soil_map"),
        stage_map=payload.get("stage_map"),
        historical_incidents_map=payload.get("historical_incidents_map"),
        auto_record=payload.get("auto_record", True)
    )
    return res


@router.get("/alerts")
def api_list_alerts(unit_id: Optional[str] = None, status: Optional[str] = None):
    return list_alerts(unit_id=unit_id, status=status)


class AckPayload(BaseModel):
    acknowledged_by: Optional[str] = None
    note: Optional[str] = None


@router.post("/alerts/{alert_id}/ack")
def api_ack_alert(alert_id: str, req: AckPayload):
    res = acknowledge_alert(alert_id, acknowledged_by=req.acknowledged_by, note=req.note)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res


class IncidentPayload(BaseModel):
    unit_id: str
    kind: str
    notes: Optional[str] = None


@router.post("/incidents/record")
def api_record_incident(req: IncidentPayload):
    return record_incident(req.unit_id, req.kind, notes=req.notes)


@router.get("/incidents")
def api_list_incidents(unit_id: Optional[str] = None):
    return list_incidents(unit_id=unit_id)
