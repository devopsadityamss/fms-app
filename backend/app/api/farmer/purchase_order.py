# backend/app/api/farmer/purchase_order.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from app.services.farmer.purchase_order_service import (
    create_po_from_parts_request,
    create_po_from_maintenance_orders,
    approve_po,
    confirm_po_delivery,
    cancel_po,
    list_pos,
    register_parts_vendor,
    list_parts_vendors
)

router = APIRouter()


# ----------------------
# Payloads
# ----------------------
class POItem(BaseModel):
    part_id: str
    qty: int


class CreatePORequest(BaseModel):
    parts: List[POItem]
    related_maintenance_id: Optional[str] = None
    preferred_vendor_id: Optional[str] = None
    created_by: Optional[str] = None


class CreatePOFromMaintenanceRequest(BaseModel):
    maintenance_order_ids: List[str]
    created_by: Optional[str] = None


class ApprovePORequest(BaseModel):
    po_id: str
    approver: str


class DeliveryLine(BaseModel):
    part_id: str
    qty_received: int
    unit_price_paid: float


class ConfirmDeliveryRequest(BaseModel):
    po_id: str
    delivered_lines: Optional[List[DeliveryLine]] = None
    received_by: Optional[str] = None


class VendorCreate(BaseModel):
    vendor_id: str
    name: str
    lead_time_days: Optional[int] = 7
    price_map: Optional[Dict[str, float]] = None


# ----------------------
# Routes
# ----------------------
@router.post("/po/create")
def api_create_po(req: CreatePORequest):
    parts = [{"part_id": p.part_id, "qty": p.qty} for p in req.parts]
    po = create_po_from_parts_request(parts, related_maintenance_id=req.related_maintenance_id, preferred_vendor_id=req.preferred_vendor_id, created_by=req.created_by)
    return po


@router.post("/po/create/from-maintenance")
def api_create_po_from_maintenance(req: CreatePOFromMaintenanceRequest):
    po = create_po_from_maintenance_orders(req.maintenance_order_ids, created_by=req.created_by)
    return po


@router.post("/po/approve")
def api_approve_po(req: ApprovePORequest):
    res = approve_po(req.po_id, req.approver)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res


@router.post("/po/confirm-delivery")
def api_confirm_delivery(req: ConfirmDeliveryRequest):
    delivered = None
    if req.delivered_lines:
        delivered = [{"part_id": d.part_id, "qty_received": d.qty_received, "unit_price_paid": d.unit_price_paid} for d in req.delivered_lines]
    res = confirm_po_delivery(req.po_id, delivered_lines=delivered, received_by=req.received_by)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res


@router.post("/po/{po_id}/cancel")
def api_cancel_po(po_id: str, reason: Optional[str] = None):
    res = cancel_po(po_id, reason=reason)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res


@router.get("/po/list")
def api_list_pos(status: Optional[str] = None):
    return list_pos(status=status)


# vendor endpoints
@router.post("/parts/vendor/register")
def api_register_vendor(req: VendorCreate):
    v = register_parts_vendor(req.vendor_id, req.name, lead_time_days=req.lead_time_days or 7, price_map=req.price_map)
    return v


@router.get("/parts/vendor/list")
def api_list_vendors():
    return list_parts_vendors()
