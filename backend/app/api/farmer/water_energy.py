# backend/app/api/farmer/water_energy.py

from fastapi import APIRouter, Body, HTTPException, Query
from typing import Optional, Dict, Any

from app.services.farmer.water_energy_service import (
    register_pump,
    get_pump_record,
    list_pumps,
    update_pump,
    delete_pump,
    estimate_energy_from_flow_and_duration,
    estimate_energy_for_irrigation_log,
    summarize_unit_energy_usage,
    record_energy_cost_to_ledger
)

router = APIRouter()


# Pump management
@router.post("/pump")
def api_register_pump(payload: Dict[str, Any] = Body(...)):
    required = ["farmer_id", "name"]
    for r in required:
        if r not in payload:
            raise HTTPException(status_code=400, detail=f"missing {r}")
    return register_pump(
        farmer_id=payload["farmer_id"],
        name=payload["name"],
        power_kW=payload.get("power_kW"),
        avg_flow_lph=payload.get("avg_flow_lph"),
        efficiency_pct=payload.get("efficiency_pct"),
        metadata=payload.get("metadata")
    )

@router.get("/pump/{pump_id}")
def api_get_pump(pump_id: str):
    res = get_pump_record(pump_id)
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


# Estimations
@router.post("/estimate/flow-duration")
def api_estimate_flow_duration(payload: Dict[str, Any] = Body(...)):
    res = estimate_energy_from_flow_and_duration(
        flow_lph=payload.get("flow_lph"),
        duration_minutes=payload.get("duration_minutes"),
        liters=payload.get("liters"),
        pump_power_kW=payload.get("pump_power_kW"),
        pump_efficiency_pct=payload.get("pump_efficiency_pct"),
        tariff_per_kwh=payload.get("tariff_per_kwh")
    )
    if res.get("error"):
        raise HTTPException(status_code=400, detail=res)
    return res

@router.post("/estimate/from-log")
def api_estimate_from_log(payload: Dict[str, Any] = Body(...)):
    # expects irrigation_log dict
    log = payload.get("irrigation_log") or {}
    pump_id = payload.get("pump_id")
    tariff = payload.get("tariff_per_kwh")
    res = estimate_energy_for_irrigation_log(log, pump_id=pump_id, tariff_per_kwh=tariff)
    if res.get("error"):
        raise HTTPException(status_code=400, detail=res)
    return res

@router.get("/unit/{unit_id}/energy-summary")
def api_unit_energy_summary(unit_id: str, pump_id: Optional[str] = Query(None), tariff_per_kwh: Optional[float] = Query(None)):
    return summarize_unit_energy_usage(unit_id, pump_id=pump_id, tariff_per_kwh=tariff_per_kwh)

# Record cost to ledger (best-effort)
@router.post("/record-cost")
def api_record_cost(payload: Dict[str, Any] = Body(...)):
    farmer_id = payload.get("farmer_id")
    unit_id = payload.get("unit_id")
    amount = payload.get("amount")
    if not farmer_id or amount is None:
        raise HTTPException(status_code=400, detail="missing farmer_id or amount")
    res = record_energy_cost_to_ledger(farmer_id, unit_id, amount, description=payload.get("description"), tags=payload.get("tags"))
    if res.get("error"):
        raise HTTPException(status_code=400, detail=res)
    return res
