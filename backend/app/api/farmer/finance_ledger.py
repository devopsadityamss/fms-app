"""
API Routes — Finance Ledger (Receivables & Payables)
----------------------------------------------------

Endpoints:
 - POST /farmer/finance/ledger
 - GET  /farmer/finance/ledger/{entry_id}
 - GET  /farmer/finance/ledger
 - PUT  /farmer/finance/ledger/{entry_id}
 - DELETE /farmer/finance/ledger/{entry_id}

 - GET  /farmer/finance/ledger/summary
"""

from fastapi import APIRouter, Query, HTTPException, Body
from typing import Optional, Dict, Any

from app.services.farmer import finance_ledger_service as svc

router = APIRouter()


@router.post("/farmer/finance/ledger")
async def api_create_entry(payload: Dict[str, Any] = Body(...)):
    return svc.create_entry(payload)


@router.get("/farmer/finance/ledger/{entry_id}")
def api_get_entry(entry_id: str):
    entry = svc.get_entry(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="ledger_entry_not_found")
    return entry


@router.get("/farmer/finance/ledger")
def api_list_entries(
    entry_type: Optional[str] = Query(None),
    unit_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None)
):
    return svc.list_entries(entry_type=entry_type, unit_id=unit_id, status=status)


@router.put("/farmer/finance/ledger/{entry_id}")
async def api_update_entry(entry_id: str, payload: Dict[str, Any] = Body(...)):
    updated = svc.update_entry(entry_id, payload)
    if not updated:
        raise HTTPException(status_code=404, detail="ledger_entry_not_found")
    return updated


@router.delete("/farmer/finance/ledger/{entry_id}")
def api_delete_entry(entry_id: str):
    ok = svc.delete_entry(entry_id)
    if not ok:
        raise HTTPException(status_code=404, detail="ledger_entry_not_found")
    return {"success": True}


@router.get("/farmer/finance/ledger/summary")
def api_ledger_summary(unit_id: Optional[str] = Query(None)):
    return svc.ledger_summary(unit_id=unit_id)
