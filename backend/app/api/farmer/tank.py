# backend/app/api/farmer/tank.py

from fastapi import APIRouter, Body, HTTPException, Query
from typing import Optional, Dict, Any

from app.services.farmer.tank_service import (
    add_tank,
    get_tank,
    list_tanks,
    update_tank,
    delete_tank,
    record_level_reading,
    list_level_readings,
    get_latest_reading,
    estimate_volume_from_reading,
    check_low_level_alert,
    tank_overview,
    estimate_refill_time
)

router = APIRouter()


# Tank CRUD
@router.post("/tank")
def api_add_tank(payload: Dict[str, Any] = Body(...)):
    required = ["farmer_id", "name", "shape", "geometry"]
    for r in required:
        if r not in payload:
            raise HTTPException(status_code=400, detail=f"missing {r}")
    return add_tank(
        farmer_id=payload["farmer_id"],
        name=payload["name"],
        shape=payload["shape"],
        geometry=payload["geometry"],
        capacity_liters=payload.get("capacity_liters"),
        warning_level_pct=payload.get("warning_level_pct"),
        critical_level_pct=payload.get("critical_level_pct"),
        metadata=payload.get("metadata")
    )

@router.get("/tank/{tank_id}")
def api_get_tank(tank_id: str):
    res = get_tank(tank_id)
    if not res:
        raise HTTPException(status_code=404, detail="tank_not_found")
    return res

@router.get("/tanks/{farmer_id}")
def api_list_tanks(farmer_id: str):
    return list_tanks(farmer_id)

@router.put("/tank/{tank_id}")
def api_update_tank(tank_id: str, updates: Dict[str, Any] = Body(...)):
    res = update_tank(tank_id, updates)
    if res.get("error"):
        raise HTTPException(status_code=404, detail=res)
    return res

@router.delete("/tank/{tank_id}")
def api_delete_tank(tank_id: str):
    res = delete_tank(tank_id)
    if res.get("error"):
        raise HTTPException(status_code=404, detail=res)
    return res


# Level readings
@router.post("/tank/{tank_id}/reading")
def api_record_reading(tank_id: str, payload: Dict[str, Any] = Body(...)):
    res = record_level_reading(
        tank_id=tank_id,
        timestamp_iso=payload.get("timestamp_iso"),
        height_m=payload.get("height_m"),
        percent=payload.get("percent"),
        note=payload.get("note"),
        metadata=payload.get("metadata")
    )
    if res.get("error"):
        raise HTTPException(status_code=404, detail=res)
    return res

@router.get("/tank/{tank_id}/readings")
def api_list_readings(tank_id: str, limit: int = Query(200)):
    return list_level_readings(tank_id, limit=limit)

@router.get("/tank/{tank_id}/latest")
def api_latest_reading(tank_id: str):
    res = get_latest_reading(tank_id)
    if not res:
        raise HTTPException(status_code=404, detail="no_readings")
    return res

@router.get("/tank/{tank_id}/volume")
def api_estimate_volume(tank_id: str):
    res = estimate_volume_from_reading(tank_id)
    if res.get("error"):
        raise HTTPException(status_code=400, detail=res)
    return res

@router.get("/tank/{tank_id}/alert")
def api_check_alert(tank_id: str):
    res = check_low_level_alert(tank_id)
    if not res:
        return {"tank_id": tank_id, "alert": None}
    return res

@router.get("/tanks/{farmer_id}/overview")
def api_tank_overview(farmer_id: str):
    return tank_overview(farmer_id)

@router.get("/tank/{tank_id}/estimate-refill")
def api_estimate_refill(tank_id: str, target_liters: float = Query(...), pump_id: Optional[str] = Query(None), pump_rate_lph: Optional[float] = Query(None)):
    res = estimate_refill_time(tank_id, target_liters, pump_id=pump_id, pump_rate_lph=pump_rate_lph)
    if res.get("error"):
        raise HTTPException(status_code=400, detail=res)
    return res
