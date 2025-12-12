"""
API Routes — Contract Farming Planner
-------------------------------------

Endpoints:
 - POST   /farmer/contracts
 - GET    /farmer/contracts/{contract_id}
 - PUT    /farmer/contracts/{contract_id}
 - DELETE /farmer/contracts/{contract_id}
 - GET    /farmer/contracts
 - GET    /farmer/contracts/{contract_id}/summary
"""

from fastapi import APIRouter, HTTPException, Body, Query
from typing import Optional, Dict, Any

from app.services.farmer import contract_farming_service as svc

router = APIRouter()


@router.post("/farmer/contracts")
async def api_create_contract(payload: Dict[str, Any] = Body(...)):
    if "buyer_id" not in payload or "start_date" not in payload or "end_date" not in payload:
        raise HTTPException(status_code=400, detail="buyer_id, start_date and end_date are required")
    return svc.create_contract(payload)


@router.get("/farmer/contracts/{contract_id}")
def api_get_contract(contract_id: str):
    rec = svc.get_contract(contract_id)
    if not rec:
        raise HTTPException(status_code=404, detail="contract_not_found")
    return rec


@router.put("/farmer/contracts/{contract_id}")
async def api_update_contract(contract_id: str, payload: Dict[str, Any] = Body(...)):
    rec = svc.update_contract(contract_id, payload)
    if not rec:
        raise HTTPException(status_code=404, detail="contract_not_found")
    return rec


@router.delete("/farmer/contracts/{contract_id}")
def api_delete_contract(contract_id: str):
    ok = svc.delete_contract(contract_id)
    if not ok:
        raise HTTPException(status_code=404, detail="contract_not_found")
    return {"success": True}


@router.get("/farmer/contracts")
def api_list_contracts(
    buyer_id: Optional[str] = Query(None),
    unit_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None)
):
    return svc.list_contracts(buyer_id=buyer_id, unit_id=unit_id, status=status)


@router.get("/farmer/contracts/{contract_id}/summary")
def api_contract_summary(contract_id: str):
    summ = svc.contract_summary(contract_id)
    if not summ:
        raise HTTPException(status_code=404, detail="contract_not_found")
    return summ
