"""
API Routes — Government Scheme Optimization
-------------------------------------------

Endpoints:
 - POST   /farmer/gov-schemes              → Add new scheme
 - PUT    /farmer/gov-schemes/{id}         → Update scheme
 - DELETE /farmer/gov-schemes/{id}         → Remove scheme
 - GET    /farmer/gov-schemes              → List schemes
 - POST   /farmer/gov-schemes/match        → Get scheme recommendations for a farmer
"""

from fastapi import APIRouter, HTTPException, Body, Query
from typing import Optional, Dict, Any

from app.services.farmer import gov_scheme_optimizer_service as svc

router = APIRouter()


@router.post("/farmer/gov-schemes")
async def api_add_scheme(payload: Dict[str, Any] = Body(...)):
    if "name" not in payload:
        raise HTTPException(status_code=400, detail="name is required")
    return svc.add_scheme(payload)


@router.put("/farmer/gov-schemes/{scheme_id}")
async def api_update_scheme(scheme_id: str, payload: Dict[str, Any] = Body(...)):
    rec = svc.update_scheme(scheme_id, payload)
    if not rec:
        raise HTTPException(status_code=404, detail="scheme_not_found")
    return rec


@router.delete("/farmer/gov-schemes/{scheme_id}")
def api_delete_scheme(scheme_id: str):
    ok = svc.delete_scheme(scheme_id)
    if not ok:
        raise HTTPException(status_code=404, detail="scheme_not_found")
    return {"success": True}


@router.get("/farmer/gov-schemes")
def api_list_schemes(
    category: Optional[str] = Query(None),
    region: Optional[str] = Query(None)
):
    return svc.list_schemes(category=category, region=region)


@router.post("/farmer/gov-schemes/match")
async def api_match_schemes(farmer_profile: Dict[str, Any] = Body(...)):
    """
    farmer_profile example:
    {
        "crop_type": "paddy",
        "region": "South Zone",
        "land_holding_ha": 1.2,
        "irrigation": "drip",
        "organic_certified": false
    }
    """
    return svc.match_schemes(farmer_profile)
