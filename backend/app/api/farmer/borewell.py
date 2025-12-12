# backend/app/api/farmer/borewell.py

from fastapi import APIRouter, Body, HTTPException, Query
from typing import Optional, Dict, Any, List

from app.services.farmer.borewell_service import (
    add_borewell,
    get_borewell,
    list_borewells,
    update_borewell,
    delete_borewell,
    record_water_level_reading,
    get_readings,
    estimate_recharge_from_rainfall,
    simulate_recharge_from_rain_series,
    estimate_observed_recharge_rate,
    borewell_overview
)

router = APIRouter()

# Borewell registry endpoints
@router.post("/borewell")
def api_add_borewell(payload: Dict[str, Any] = Body(...)):
    required = ["farmer_id", "name"]
    for r in required:
        if r not in payload:
            raise HTTPException(status_code=400, detail=f"missing {r}")
    return add_borewell(
        farmer_id=payload["farmer_id"],
        name=payload["name"],
        location=payload.get("location"),
        depth_m=payload.get("depth_m"),
        static_water_level_m=payload.get("static_water_level_m"),
        recharge_area_m2=payload.get("recharge_area_m2"),
        recharge_coefficient=payload.get("recharge_coefficient"),
        aquifer_area_m2=payload.get("aquifer_area_m2"),
        specific_yield=payload.get("specific_yield"),
        metadata=payload.get("metadata")
    )

@router.get("/borewell/{borewell_id}")
def api_get_borewell(borewell_id: str):
    res = get_borewell(borewell_id)
    if not res:
        raise HTTPException(status_code=404, detail="borewell_not_found")
    return res

@router.get("/borewells/{farmer_id}")
def api_list_borewells(farmer_id: str):
    return list_borewells(farmer_id)

@router.put("/borewell/{borewell_id}")
def api_update_borewell(borewell_id: str, updates: Dict[str, Any] = Body(...)):
    res = update_borewell(borewell_id, updates)
    if res.get("error"):
        raise HTTPException(status_code=404, detail=res)
    return res

@router.delete("/borewell/{borewell_id}")
def api_delete_borewell(borewell_id: str):
    res = delete_borewell(borewell_id)
    if res.get("error"):
        raise HTTPException(status_code=404, detail=res)
    return res

# Water-level readings
@router.post("/borewell/{borewell_id}/reading")
def api_record_reading(borewell_id: str, payload: Dict[str, Any] = Body(...)):
    res = record_water_level_reading(
        borewell_id=borewell_id,
        timestamp_iso=payload.get("timestamp_iso"),
        depth_to_water_m=payload.get("depth_to_water_m"),
        note=payload.get("note"),
        metadata=payload.get("metadata")
    )
    if res.get("error"):
        raise HTTPException(status_code=404, detail=res)
    return res

@router.get("/borewell/{borewell_id}/readings")
def api_get_readings(borewell_id: str, limit: int = Query(200)):
    return get_readings(borewell_id, limit=limit)

# Recharge estimation
@router.get("/borewell/{borewell_id}/estimate-recharge")
def api_estimate_recharge(borewell_id: str, rainfall_mm: float = Query(...), days: int = Query(1)):
    res = estimate_recharge_from_rainfall(borewell_id, rainfall_mm=rainfall_mm, days=days)
    if res.get("error"):
        raise HTTPException(status_code=404, detail=res)
    return res

@router.post("/borewell/{borewell_id}/simulate-recharge")
def api_simulate_recharge(borewell_id: str, payload: Dict[str, Any] = Body(...)):
    # payload: { daily_rainfall_mm: [..], start_depth_to_water_m: optional, days_to_simulate: optional }
    daily = payload.get("daily_rainfall_mm") or []
    start = payload.get("start_depth_to_water_m")
    days = payload.get("days_to_simulate")
    res = simulate_recharge_from_rain_series(borewell_id, daily_rainfall_mm=daily, start_depth_to_water_m=start, days_to_simulate=days)
    if res.get("error"):
        raise HTTPException(status_code=404, detail=res)
    return res

@router.get("/borewell/{borewell_id}/observed-recharge")
def api_observed_recharge(borewell_id: str, lookback_days: int = Query(30)):
    res = estimate_observed_recharge_rate(borewell_id, lookback_days=lookback_days)
    if res.get("error"):
        raise HTTPException(status_code=404, detail=res)
    return res

@router.get("/borewells/{farmer_id}/overview")
def api_borewell_overview(farmer_id: str):
    return borewell_overview(farmer_id)
