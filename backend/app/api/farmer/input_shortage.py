# backend/app/api/farmer/input_shortage.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.services.farmer.input_shortage_service import (
    add_inventory_item,
    update_inventory_quantity,
    get_inventory,
    check_shortages_for_unit,
    check_shortages_for_farm,
    list_shortage_alerts,
    acknowledge_shortage,
    create_procurement_suggestion_po
)

router = APIRouter()


class InventoryItemPayload(BaseModel):
    item_id: str
    name: str
    quantity: float
    unit: Optional[str] = "kg"
    min_threshold: Optional[float] = None


class InventoryDeltaPayload(BaseModel):
    item_id: str
    delta: float


class ProcureLine(BaseModel):
    item_id: str
    qty: float


@router.post("/inventory/add")
def api_add_inventory(req: InventoryItemPayload):
    return add_inventory_item(req.item_id, req.name, req.quantity, unit=req.unit, min_threshold=req.min_threshold)


@router.post("/inventory/update")
def api_update_inventory(req: InventoryDeltaPayload):
    res = update_inventory_quantity(req.item_id, req.delta)
    if res is None:
        raise HTTPException(status_code=404, detail="item_not_found")
    return res


@router.get("/inventory")
def api_get_inventory(item_id: Optional[str] = None):
    return get_inventory(item_id=item_id)


@router.get("/shortages/check/{unit_id}")
def api_check_unit_shortage(unit_id: str, lookahead_days: int = 30, safety_margin_pct: float = 0.10):
    res = check_shortages_for_unit(unit_id, lookahead_days=lookahead_days, safety_margin_pct=safety_margin_pct)
    if res.get("status") == "unit_not_found":
        raise HTTPException(status_code=404, detail="unit_not_found")
    return res


@router.get("/shortages/check/farm")
def api_check_farm_shortages(lookahead_days: int = 30, safety_margin_pct: float = 0.10):
    return check_shortages_for_farm(lookahead_days=lookahead_days, safety_margin_pct=safety_margin_pct)


@router.get("/shortages")
def api_list_shortage_alerts(unit_id: Optional[str] = None, status: Optional[str] = None):
    return list_shortage_alerts(unit_id=unit_id, status=status)


@router.post("/shortages/{alert_id}/ack")
def api_ack_shortage(alert_id: str, acknowledged_by: Optional[str] = None):
    res = acknowledge_shortage(alert_id, acknowledged_by=acknowledged_by)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res


@router.post("/procurement/suggest/{unit_id}")
def api_create_procurement_po(unit_id: str, lines: List[ProcureLine], created_by: Optional[str] = None):
    sugests = [{"item_id": l.item_id, "qty": l.qty} for l in lines]
    res = create_procurement_suggestion_po(unit_id, sugests, created_by=created_by)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res
