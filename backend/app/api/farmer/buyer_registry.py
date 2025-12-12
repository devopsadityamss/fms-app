"""
API Routes — Buyer Registry
---------------------------

Endpoints:
 - POST   /farmer/buyers
 - GET    /farmer/buyers/{buyer_id}
 - PUT    /farmer/buyers/{buyer_id}
 - DELETE /farmer/buyers/{buyer_id}
 - GET    /farmer/buyers
 - GET    /farmer/buyers/{buyer_id}/score
"""

from fastapi import APIRouter, HTTPException, Query, Body
from typing import Optional, Any, Dict

from app.services.farmer import buyer_registry_service as svc

router = APIRouter()


@router.post("/farmer/buyers")
async def api_create_buyer(payload: Dict[str, Any] = Body(...)):
    if "name" not in payload:
        raise HTTPException(status_code=400, detail="buyer name is required")
    return svc.create_buyer(payload)


@router.get("/farmer/buyers/{buyer_id}")
def api_get_buyer(buyer_id: str):
    rec = svc.get_buyer(buyer_id)
    if not rec:
        raise HTTPException(status_code=404, detail="buyer_not_found")
    return rec


@router.put("/farmer/buyers/{buyer_id}")
async def api_update_buyer(buyer_id: str, payload: Dict[str, Any] = Body(...)):
    rec = svc.update_buyer(buyer_id, payload)
    if not rec:
        raise HTTPException(status_code=404, detail="buyer_not_found")
    return rec


@router.delete("/farmer/buyers/{buyer_id}")
def api_delete_buyer(buyer_id: str):
    ok = svc.delete_buyer(buyer_id)
    if not ok:
        raise HTTPException(status_code=404, detail="buyer_not_found")
    return {"success": True}


@router.get("/farmer/buyers")
def api_list_buyers(
    region: Optional[str] = Query(None),
    buyer_type: Optional[str] = Query(None),
    min_rating: Optional[float] = Query(None)
):
    return svc.list_buyers(region=region, buyer_type=buyer_type, min_rating=min_rating)


@router.get("/farmer/buyers/{buyer_id}/score")
def api_compute_buyer_score(buyer_id: str):
    res = svc.compute_buyer_score(buyer_id)
    if not res:
        raise HTTPException(status_code=404, detail="buyer_not_found")
    return res
