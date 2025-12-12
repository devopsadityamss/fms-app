# backend/app/api/farmer/emissions.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.services.farmer.emissions_service import (
    equipment_emissions_from_logs,
    equipment_emissions_estimate_from_hours,
    equipment_task_level_emissions,
    fleet_emissions_summary
)

router = APIRouter()


class EmissionFactorsPayload(BaseModel):
    # optional override factors, e.g. {"diesel_l_per_l": 2.68}
    emission_factors: Optional[Dict[str, float]] = None


class TaskEvent(BaseModel):
    task_id: Optional[str] = None
    start_iso: Optional[str] = None
    end_iso: Optional[str] = None
    liters_used: Optional[float] = None
    fuel_type: Optional[str] = "diesel"
    estimated_hours: Optional[float] = None


# equipment-level emissions from logs
@router.get("/equipment/{equipment_id}/emissions")
def api_equipment_emissions(equipment_id: str, lookback_days: int = 90):
    res = equipment_emissions_from_logs(equipment_id, lookback_days=lookback_days)
    if res.get("status") == "no_fuel_logs":
        # return estimated response too so frontend can choose
        est = equipment_emissions_estimate_from_hours(equipment_id, lookback_days=lookback_days)
        return {"from_logs": res, "estimated_from_hours": est}
    return res


# estimate from hours / cost as fallback
@router.get("/equipment/{equipment_id}/emissions/estimate")
def api_equipment_emissions_estimate(equipment_id: str, lookback_days: int = 90):
    res = equipment_emissions_estimate_from_hours(equipment_id, lookback_days=lookback_days)
    if res.get("status") == "equipment_not_found":
        raise HTTPException(status_code=404, detail="equipment_not_found")
    return res


# per-task emissions (POST so frontend can submit tasks)
@router.post("/equipment/{equipment_id}/emissions/tasks")
def api_task_emissions(equipment_id: str, tasks: List[TaskEvent], payload: Optional[EmissionFactorsPayload] = None):
    # convert pydantic tasks to dicts
    task_events = [t.dict() for t in tasks]
    res = equipment_task_level_emissions(equipment_id, task_events, emission_factors=(payload.emission_factors if payload else None))
    return res


# fleet summary
@router.get("/fleet/emissions")
def api_fleet_emissions(lookback_days: int = 90):
    return fleet_emissions_summary(lookback_days=lookback_days)
