# backend/app/api/farmer/fuel_analytics.py

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from app.services.farmer.fuel_analytics_service import (
    log_fuel_usage,
    analyze_fuel_usage,
    detect_fuel_theft,
    fleet_fuel_dashboard
)

router = APIRouter()


class FuelLogPayload(BaseModel):
    equipment_id: str
    liters: float
    cost: float
    operator_id: Optional[str] = None
    timestamp: Optional[str] = None


@router.post("/fuel/log")
def api_log_fuel(req: FuelLogPayload):
    return log_fuel_usage(req.equipment_id, req.liters, req.cost, req.operator_id, req.timestamp)


@router.get("/fuel/{equipment_id}/analytics")
def api_fuel_analytics(equipment_id: str):
    return analyze_fuel_usage(equipment_id)


@router.get("/fuel/{equipment_id}/theft")
def api_fuel_theft(equipment_id: str):
    return detect_fuel_theft(equipment_id)


@router.get("/fuel/dashboard/fleet")
def api_fuel_dashboard():
    return fleet_fuel_dashboard()
