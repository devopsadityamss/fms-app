"""
API Routes — Supplier Payment Scheduler
---------------------------------------

Endpoints:
 - POST   /farmer/supplier-payments
 - GET    /farmer/supplier-payments/{pay_id}
 - PUT    /farmer/supplier-payments/{pay_id}
 - DELETE /farmer/supplier-payments/{pay_id}
 - GET    /farmer/supplier-payments
 - GET    /farmer/supplier-payments/summary
"""

from fastapi import APIRouter, HTTPException, Query, Body
from typing import Optional, Dict, Any

from app.services.farmer import supplier_payment_service as svc

router = APIRouter()


@router.post("/farmer/supplier-payments")
async def api_create_payment(payload: Dict[str, Any] = Body(...)):
    if "supplier_name" not in payload or "amount" not in payload:
        raise HTTPException(status_code=400, detail="supplier_name and amount required")
    return svc.create_payment(payload)


@router.get("/farmer/supplier-payments/{pay_id}")
def api_get_payment(pay_id: str):
    rec = svc.get_payment(pay_id)
    if not rec:
        raise HTTPException(status_code=404, detail="payment_not_found")
    return rec


@router.put("/farmer/supplier-payments/{pay_id}")
async def api_update_payment(pay_id: str, payload: Dict[str, Any] = Body(...)):
    rec = svc.update_payment(pay_id, payload)
    if not rec:
        raise HTTPException(status_code=404, detail="payment_not_found")
    return rec


@router.delete("/farmer/supplier-payments/{pay_id}")
def api_delete_payment(pay_id: str):
    ok = svc.delete_payment(pay_id)
    if not ok:
        raise HTTPException(status_code=404, detail="payment_not_found")
    return {"success": True}


@router.get("/farmer/supplier-payments")
def api_list_payments(
    supplier_id: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None)
):
    return svc.list_payments(
        supplier_id=supplier_id,
        category=category,
        status=status
    )


@router.get("/farmer/supplier-payments/summary")
def api_payment_summary():
    return svc.payment_summary()
