"""
API Routes — Buyer Preference Modelling
--------------------------------------

Endpoints:
 - POST   /farmer/buyer-preferences
 - GET    /farmer/buyer-preferences/{pref_id}
 - PUT    /farmer/buyer-preferences/{pref_id}
 - DELETE /farmer/buyer-preferences/{pref_id}
 - GET    /farmer/buyer-preferences
 - POST   /farmer/buyer-preferences/recommend
"""

from fastapi import APIRouter, HTTPException, Body, Query
from typing import Optional, Dict, Any, List

from app.services.farmer import buyer_preference_service as svc

router = APIRouter()


@router.post("/farmer/buyer-preferences")
async def api_create_preference(payload: Dict[str, Any] = Body(...)):
    if "buyer_id" not in payload:
        raise HTTPException(status_code=400, detail="buyer_id is required")
    return svc.create_preference(payload)


@router.get("/farmer/buyer-preferences/{pref_id}")
def api_get_preference(pref_id: str):
    rec = svc.get_preference(pref_id)
    if not rec:
        raise HTTPException(status_code=404, detail="preference_not_found")
    return rec


@router.put("/farmer/buyer-preferences/{pref_id}")
async def api_update_preference(pref_id: str, payload: Dict[str, Any] = Body(...)):
    rec = svc.update_preference(pref_id, payload)
    if not rec:
        raise HTTPException(status_code=404, detail="preference_not_found")
    return rec


@router.delete("/farmer/buyer-preferences/{pref_id}")
def api_delete_preference(pref_id: str):
    ok = svc.delete_preference(pref_id)
    if not ok:
        raise HTTPException(status_code=404, detail="preference_not_found")
    return {"success": True}


@router.get("/farmer/buyer-preferences")
def api_list_preferences(buyer_id: Optional[str] = Query(None)):
    return svc.list_preferences(buyer_id=buyer_id)


@router.post("/farmer/buyer-preferences/recommend")
async def api_recommend_buyers(
    unit_profile: Dict[str, Any] = Body(...),
    top_n: Optional[int] = Query(5)
):
    """
    unit_profile example:
    {
      "grade": "A",
      "packaging": "crate",
      "delivery_window": "morning",
      "region": "North Zone",
      "expected_price": 28.5,
      "quality_metric": 0.8
    }
    """
    return svc.recommend_buyers_for_unit(unit_profile, top_n=top_n)
