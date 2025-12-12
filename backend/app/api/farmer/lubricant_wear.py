# backend/app/api/farmer/lubricant_wear.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services.farmer.lubricant_wear_service import (
    record_lubricant_usage,
    list_lubricant_usage,
    forecast_lubricant_consumption,
    predict_engine_wear,
    fleet_lubricant_forecast,
    fleet_engine_wear
)

router = APIRouter()


# ----------------------
# Payloads
# ----------------------
class LubricantUsagePayload(BaseModel):
    equipment_id: str
    liters_used: float
    performed_at: Optional[str] = None
    notes: Optional[str] = None


class ForecastRequest(BaseModel):
    horizon_months: Optional[int] = 6
    lookback_days: Optional[int] = 365
    safety_buffer_pct: Optional[float] = 0.20


# ----------------------
# Routes
# ----------------------
@router.post("/equipment/{equipment_id}/lubricant/record")
def api_record_lubricant(equipment_id: str, req: LubricantUsagePayload):
    rec = record_lubricant_usage(equipment_id, req.liters_used, performed_at=req.performed_at, notes=req.notes)
    return {"success": True, "record": rec}


@router.get("/equipment/{equipment_id}/lubricant/history")
def api_list_lubricant_history(equipment_id: str):
    return {"equipment_id": equipment_id, "history": list_lubricant_usage(equipment_id)}


@router.post("/equipment/{equipment_id}/lubricant/forecast")
def api_forecast_lubricant(equipment_id: str, req: ForecastRequest):
    res = forecast_lubricant_consumption(equipment_id, horizon_months=req.horizon_months, lookback_days=req.lookback_days, safety_buffer_pct=req.safety_buffer_pct)
    if res is None:
        raise HTTPException(status_code=404, detail="equipment_not_found")
    return res


@router.get("/equipment/{equipment_id}/engine-wear")
def api_predict_engine_wear(equipment_id: str, horizon_months: int = 6):
    res = predict_engine_wear(equipment_id, horizon_months=horizon_months)
    if res is None:
        raise HTTPException(status_code=404, detail="equipment_not_found")
    return res


@router.get("/equipment/lubricant/forecast/fleet")
def api_fleet_lubricant_forecast(horizon_months: int = 6):
    return fleet_lubricant_forecast(horizon_months=horizon_months)


@router.get("/equipment/engine-wear/fleet")
def api_fleet_engine_wear(horizon_months: int = 12):
    return fleet_engine_wear(horizon_months=horizon_months)
