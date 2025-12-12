# backend/app/api/farmer/spare_parts.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from typing import List



from app.services.farmer.spare_parts_service import (
    add_part,
    update_part,
    delete_part,
    get_part,
    list_parts,
    assign_part_to_equipment,
    get_parts_for_equipment,
    consume_part,
    check_low_stock,
    log_part_usage,
    list_part_usage,
    list_all_usage,
    generate_restock_recommendation,
    forecast_parts_consumption,
    forecast_parts_for_equipment,
    list_low_stock_parts,
    record_part_consumption,
)

router = APIRouter()


class AddPartRequest(BaseModel):
    name: str
    sku: Optional[str] = ""
    manufacturer: Optional[str] = ""
    unit_price: Optional[float] = 0.0
    quantity: Optional[int] = 0
    min_stock_threshold: Optional[int] = 1
    metadata: Optional[Dict[str, Any]] = {}


@router.post("/spare-parts/add")
def api_add_part(req: AddPartRequest):
    rec = add_part(
        name=req.name,
        sku=req.sku,
        manufacturer=req.manufacturer,
        unit_price=req.unit_price,
        quantity=req.quantity,
        min_stock_threshold=req.min_stock_threshold,
        metadata=req.metadata,
    )
    return {"success": True, "part": rec}


class UpdatePartRequest(BaseModel):
    name: Optional[str] = None
    sku: Optional[str] = None
    manufacturer: Optional[str] = None
    unit_price: Optional[float] = None
    quantity: Optional[int] = None
    min_stock_threshold: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


@router.put("/spare-parts/update/{part_id}")
def api_update_part(part_id: str, req: UpdatePartRequest):
    rec = update_part(
        part_id=part_id,
        name=req.name,
        sku=req.sku,
        manufacturer=req.manufacturer,
        unit_price=req.unit_price,
        quantity=req.quantity,
        min_stock_threshold=req.min_stock_threshold,
        metadata=req.metadata,
    )
    if not rec:
        raise HTTPException(status_code=404, detail="part_not_found")
    return {"success": True, "part": rec}


@router.delete("/spare-parts/delete/{part_id}")
def api_delete_part(part_id: str):
    ok = delete_part(part_id)
    if not ok:
        raise HTTPException(status_code=404, detail="part_not_found")
    return {"success": True, "deleted": True}


@router.get("/spare-parts/{part_id}")
def api_get_part(part_id: str):
    rec = get_part(part_id)
    if not rec:
        raise HTTPException(status_code=404, detail="part_not_found")
    return rec


@router.get("/spare-parts/list")
def api_list_parts():
    return list_parts()


@router.post("/spare-parts/{part_id}/assign/{equipment_id}")
def api_assign_part(part_id: str, equipment_id: str, quantity: int = 1):
    assign = assign_part_to_equipment(part_id, equipment_id, quantity)
    if not assign:
        raise HTTPException(status_code=404, detail="part_not_found")
    return {"success": True, "assignment": assign}


@router.get("/spare-parts/equipment/{equipment_id}")
def api_get_parts_for_equipment(equipment_id: str):
    return get_parts_for_equipment(equipment_id)


class ConsumePartRequest(BaseModel):
    quantity: int


@router.post("/spare-parts/{part_id}/consume")
def api_consume_part(part_id: str, req: ConsumePartRequest):
    res = consume_part(part_id, req.quantity)
    if res is None:
        raise HTTPException(status_code=404, detail="part_not_found")
    if "error" in res:
        raise HTTPException(status_code=400, detail=res)
    return {"success": True, "part": res}


@router.get("/spare-parts/low-stock")
def api_low_stock(threshold: Optional[int] = None):
    return check_low_stock(threshold)


class PartUsageRequest(BaseModel):
    equipment_id: str
    quantity: int
    reason: Optional[str] = "maintenance"
    worker_id: Optional[str] = None


@router.post("/spare-parts/{part_id}/use")
def api_log_part_usage(part_id: str, req: PartUsageRequest):
    entry = log_part_usage(
        part_id=part_id,
        equipment_id=req.equipment_id,
        quantity=req.quantity,
        reason=req.reason,
        worker_id=req.worker_id,
    )

    if entry is None:
        raise HTTPException(status_code=404, detail="part_not_found")

    if "error" in entry:
        raise HTTPException(status_code=400, detail=entry)

    return {"success": True, "usage": entry}


@router.get("/spare-parts/{part_id}/usage")
def api_list_part_usage(part_id: str):
    logs = list_part_usage(part_id)
    if logs is None:
        raise HTTPException(status_code=404, detail="part_not_found")
    return logs


@router.get("/spare-parts/usage/all")
def api_list_all_usage():
    return list_all_usage()


@router.get("/spare-parts/{part_id}/restock")
def api_restock_recommendation(part_id: str):
    rec = generate_restock_recommendation(part_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="part_not_found")
    return rec




class PartsForecastRequest(BaseModel):
    equipment_ids: Optional[List[str]] = None
    horizon_months: Optional[int] = 6
    lookback_days: Optional[int] = 180
    safety_buffer_pct: Optional[float] = 0.20


@router.post("/parts/forecast")
def api_parts_forecast(req: PartsForecastRequest):
    res = forecast_parts_consumption(
        equipment_ids=req.equipment_ids,
        horizon_months=req.horizon_months,
        lookback_days=req.lookback_days,
        safety_buffer_pct=req.safety_buffer_pct
    )
    return res


@router.get("/parts/forecast/equipment/{equipment_id}")
def api_parts_forecast_equipment(equipment_id: str, horizon_months: int = 6, lookback_days: int = 180, safety_buffer_pct: float = 0.20):
    res = forecast_parts_for_equipment(
        equipment_id=equipment_id,
        horizon_months=horizon_months,
        lookback_days=lookback_days,
        safety_buffer_pct=safety_buffer_pct
    )
    if res is None:
        raise HTTPException(status_code=404, detail="equipment_or_parts_not_found")
    return res


@router.get("/parts/low-stock")
def api_low_stock_parts(within_months: int = 6, lookback_days: int = 180, safety_buffer_pct: float = 0.20):
    return list_low_stock_parts(within_months=within_months, lookback_days=lookback_days, safety_buffer_pct=safety_buffer_pct)


class RecordConsumptionRequest(BaseModel):
    part_id: str
    equipment_id: str
    qty: float
    used_at: Optional[str] = None


@router.post("/parts/consume")
def api_record_consumption(req: RecordConsumptionRequest):
    entry = record_part_consumption(req.part_id, req.equipment_id, req.qty, req.used_at)
    return {"success": True, "consumption": entry}


@router.post("/parts/add")
def api_add_part(item: dict):
    # Accept dict to be flexible with fields
    p = add_part(
        part_id=item.get("part_id") or str(datetime.utcnow().timestamp()),
        name=item.get("name", "unknown"),
        unit_price=float(item.get("unit_price", 0.0)),
        quantity=int(item.get("quantity", 0)),
        min_stock_threshold=int(item.get("min_stock_threshold", 1))
    )
    return {"success": True, "part": p}


@router.get("/parts")
def api_list_parts():
    return list_parts()
