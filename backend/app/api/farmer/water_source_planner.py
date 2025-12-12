# backend/app/api/farmer/water_source_planner.py

from fastapi import APIRouter, Body, HTTPException, Query
from typing import Optional, Dict, Any

from app.services.farmer.water_source_planner_service import (
    plan_sources_for_demand,
    register_source_for_unit,
    list_registered_sources
)

router = APIRouter()

@router.post("/plan-sources/{unit_id}")
def api_plan_sources(unit_id: str, payload: Dict[str, Any] = Body(...)):
    demand = payload.get("demand_liters")
    farmer_id = payload.get("farmer_id")
    if demand is None:
        raise HTTPException(status_code=400, detail="missing demand_liters")
    by_when = payload.get("by_when_iso")
    objective = payload.get("objective", "cost")
    reserve_pct = payload.get("min_tank_reserve_pct", 10.0)
    plan = plan_sources_for_demand(unit_id=unit_id, farmer_id=farmer_id, demand_liters=float(demand), by_when_iso=by_when, objective=objective, min_tank_reserve_pct=float(reserve_pct))
    return plan

@router.post("/register-source/{unit_id}")
def api_register_source(unit_id: str, payload: Dict[str, Any] = Body(...)):
    stype = payload.get("source_type")
    if not stype:
        raise HTTPException(status_code=400, detail="missing source_type")
    return register_source_for_unit(unit_id, stype, payload.get("source_id"), capacity_liters=payload.get("capacity_liters"), cost_per_1000l=payload.get("cost_per_1000l"), max_rate_lph=payload.get("max_rate_lph"), metadata=payload.get("metadata"))

@router.get("/registered-sources/{unit_id}")
def api_list_sources(unit_id: str):
    return {"unit_id": unit_id, "sources": list_registered_sources(unit_id)}
