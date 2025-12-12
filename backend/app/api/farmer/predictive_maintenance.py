# backend/app/api/farmer/predictive_maintenance.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from app.services.farmer.predictive_maintenance_service import (
    propose_maintenance_for_equipment,
    batch_propose_maintenance,
    confirm_maintenance_order,
    list_maintenance_orders,
    cancel_maintenance_order,
    register_technician,
    block_technician_period
)

router = APIRouter()


class ProposeRequest(BaseModel):
    equipment_ids: Optional[List[str]] = None
    horizon_days: Optional[int] = 30


class ConfirmRequest(BaseModel):
    proposal: Dict[str, Any]


class TechRegister(BaseModel):
    tech_id: str
    name: str
    skills: Optional[List[str]] = None


class TechBlock(BaseModel):
    tech_id: str
    start_iso: str
    end_iso: str


@router.post("/maintenance/propose")
def api_batch_propose(req: ProposeRequest):
    res = batch_propose_maintenance(equipment_ids=req.equipment_ids, horizon_days=req.horizon_days or 30)
    return res


@router.get("/maintenance/propose/{equipment_id}")
def api_propose_single(equipment_id: str, horizon_days: int = 30):
    res = propose_maintenance_for_equipment(equipment_id, horizon_days=horizon_days)
    if not res:
        raise HTTPException(status_code=404, detail="equipment_not_found")
    return res


@router.post("/maintenance/confirm")
def api_confirm(req: ConfirmRequest):
    try:
        order = confirm_maintenance_order(req.proposal)
        return order
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/maintenance/orders")
def api_list_orders(status: Optional[str] = None):
    return list_maintenance_orders(status=status)


@router.post("/maintenance/orders/{order_id}/cancel")
def api_cancel(order_id: str, reason: Optional[str] = None):
    res = cancel_maintenance_order(order_id, reason=reason)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res


@router.post("/maintenance/technician/register")
def api_register_tech(req: TechRegister):
    return register_technician(req.tech_id, req.name, skills=req.skills)


@router.post("/maintenance/technician/block")
def api_block_tech(req: TechBlock):
    return block_technician_period(req.tech_id, req.start_iso, req.end_iso)
