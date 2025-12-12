# backend/app/api/farmer/water.py

from fastapi import APIRouter, Body, HTTPException, Query
from typing import Optional, Dict, Any, List

from app.services.farmer.water_service import (
    add_tank,
    get_tank,
    list_tanks,
    update_tank,
    delete_tank,
    record_reading,
    get_readings,
    estimate_current_level,
    estimate_consumption,
    tank_status_overview
)

router = APIRouter()

# Tanks
@router.post("/water/tank")
def api_add_tank(payload: Dict[str, Any] = Body(...)):
    required = ["farmer_id", "name", "capacity_liters"]
    for r in required:
        if r not in payload:
            raise HTTPException(status_code=400, detail=f"missing {r}")
    return add_tank(
        farmer_id=payload["farmer_id"],
        name=payload["name"],
        capacity_liters=payload["capacity_liters"],
        location=payload.get("location"),
        tank_type=payload.get("tank_type"),
        metadata=payload.get("metadata")
    )

@router.get("/water/tank/{tank_id}")
def api_get_tank(tank_id: str):
    res = get_tank(tank_id)
    if not res:
        raise HTTPException(status_code=404, detail="tank_not_found")
    return res

@router.get("/water/tanks/{farmer_id}")
def api_list_tanks(farmer_id: str):
    return list_tanks(farmer_id)

@router.put("/water/tank/{tank_id}")
def api_update_tank(tank_id: str, updates: Dict[str, Any] = Body(...)):
    res = update_tank(tank_id, updates)
    if res.get("error"):
        raise HTTPException(status_code=404, detail=res)
    return res

@router.delete("/water/tank/{tank_id}")
def api_delete_tank(tank_id: str):
    res = delete_tank(tank_id)
    if res.get("error"):
        raise HTTPException(status_code=404, detail=res)
    return res

# Readings
@router.post("/water/tank/{tank_id}/reading")
def api_record_reading(tank_id: str, payload: Dict[str, Any] = Body(...)):
    # allowed fields: timestamp_iso, level_pct, level_mm, note, metadata
    res = record_reading(
        tank_id=tank_id,
        timestamp_iso=payload.get("timestamp_iso"),
        level_pct=payload.get("level_pct"),
        level_mm=payload.get("level_mm"),
        note=payload.get("note"),
        metadata=payload.get("metadata")
    )
    if res.get("error"):
        raise HTTPException(status_code=404, detail=res)
    return res

@router.get("/water/tank/{tank_id}/readings")
def api_get_readings(tank_id: str, limit: int = Query(100)):
    return get_readings(tank_id, limit=limit)

@router.get("/water/tank/{tank_id}/estimate")
def api_estimate_level(tank_id: str):
    res = estimate_current_level(tank_id)
    if res.get("error"):
        raise HTTPException(status_code=404, detail=res)
    return res

@router.get("/water/tank/{tank_id}/consumption")
def api_consumption(tank_id: str, since_iso: Optional[str] = Query(None), until_iso: Optional[str] = Query(None)):
    res = estimate_consumption(tank_id, since_iso=since_iso, until_iso=until_iso)
    if res.get("error"):
        raise HTTPException(status_code=404, detail=res)
    return res

@router.get("/water/tanks/{farmer_id}/overview")
def api_tank_overview(farmer_id: str):
    return tank_status_overview(farmer_id)
