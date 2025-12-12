# backend/app/api/farmer/pump.py

from fastapi import APIRouter, Body, HTTPException, Query
from typing import Optional, Dict, Any, List

from app.services.farmer.pump_service import (
    add_pump,
    get_pump,
    list_pumps,
    update_pump,
    delete_pump,
    record_usage,
    list_usage,
    compute_efficiency_metrics,
    estimate_energy_for_volume,
    predict_maintenance_due,
    pump_overview
)

router = APIRouter()

# Pump CRUD
@router.post("/pump")
def api_add_pump(payload: Dict[str, Any] = Body(...)):
    required = ["farmer_id", "name"]
    for r in required:
        if r not in payload:
            raise HTTPException(status_code=400, detail=f"missing {r}")
    return add_pump(
        farmer_id=payload["farmer_id"],
        name=payload["name"],
        equipment_id=payload.get("equipment_id"),
        pump_type=payload.get("pump_type", "centrifugal"),
        rated_flow_lph=payload.get("rated_flow_lph"),
        rated_power_kw=payload.get("rated_power_kw"),
        rated_head_m=payload.get("rated_head_m"),
        metadata=payload.get("metadata")
    )

@router.get("/pump/{pump_id}")
def api_get_pump(pump_id: str):
    res = get_pump(pump_id)
    if not res:
        raise HTTPException(status_code=404, detail="pump_not_found")
    return res

@router.get("/pumps/{farmer_id}")
def api_list_pumps(farmer_id: str):
    return list_pumps(farmer_id)

@router.put("/pump/{pump_id}")
def api_update_pump(pump_id: str, updates: Dict[str, Any] = Body(...)):
    res = update_pump(pump_id, updates)
    if res.get("error"):
        raise HTTPException(status_code=404, detail=res)
    return res

@router.delete("/pump/{pump_id}")
def api_delete_pump(pump_id: str):
    res = delete_pump(pump_id)
    if res.get("error"):
        raise HTTPException(status_code=404, detail=res)
    return res

# Usage
@router.post("/pump/{pump_id}/usage")
def api_record_usage(pump_id: str, payload: Dict[str, Any] = Body(...)):
    # allowed fields: start_iso, end_iso, duration_hours, flow_rate_lph, volume_liters, energy_kwh, fuel_liters, note, metadata
    res = record_usage(
        pump_id=pump_id,
        start_iso=payload.get("start_iso"),
        end_iso=payload.get("end_iso"),
        duration_hours=payload.get("duration_hours"),
        flow_rate_lph=payload.get("flow_rate_lph"),
        volume_liters=payload.get("volume_liters"),
        energy_kwh=payload.get("energy_kwh"),
        fuel_liters=payload.get("fuel_liters"),
        note=payload.get("note"),
        metadata=payload.get("metadata")
    )
    if res.get("error"):
        raise HTTPException(status_code=404, detail=res)
    return res

@router.get("/pump/{pump_id}/usage")
def api_list_usage(pump_id: str, limit: int = Query(200)):
    return list_usage(pump_id, limit=limit)

# Analytics
@router.get("/pump/{pump_id}/efficiency")
def api_efficiency(pump_id: str):
    res = compute_efficiency_metrics(pump_id)
    if res.get("error"):
        raise HTTPException(status_code=404, detail=res)
    return res

@router.get("/pump/{pump_id}/estimate-energy")
def api_estimate_energy(pump_id: str, target_volume_liters: float = Query(...), use: str = Query("electric"), head_m: Optional[float] = Query(None)):
    res = estimate_energy_for_volume(pump_id=pump_id, target_volume_liters=target_volume_liters, use=use, head_m=head_m)
    if res.get("error"):
        raise HTTPException(status_code=404, detail=res)
    return res

@router.get("/pump/{pump_id}/maintenance")
def api_predict_maintenance(pump_id: str, maintenance_interval_hours: Optional[float] = Query(None)):
    res = predict_maintenance_due(pump_id, maintenance_interval_hours=maintenance_interval_hours)
    if res.get("error"):
        raise HTTPException(status_code=404, detail=res)
    return res

@router.get("/pumps/{farmer_id}/overview")
def api_pump_overview(farmer_id: str):
    return pump_overview(farmer_id)
