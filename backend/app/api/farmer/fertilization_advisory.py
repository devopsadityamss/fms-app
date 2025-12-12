"""
API Routes — Fertilization Advisory (Farmer POV)

Endpoints:
 - POST /farmer/fertilization/advice
 - GET  /farmer/fertilization/advice/{advisory_id}
 - GET  /farmer/fertilization/advice
"""

from fastapi import APIRouter, HTTPException, Body, Query
from typing import Optional, Dict, Any

from app.services.farmer import fertilization_advisory_service as svc

router = APIRouter()

@router.post("/farmer/fertilization/advice")
async def api_generate_fertilization_advice(
    unit_id: Optional[str] = Query(None),
    crop_stage: Optional[str] = Query(None),
    soil_n: Optional[float] = Query(None),
    soil_p: Optional[float] = Query(None),
    soil_k: Optional[float] = Query(None),
    notes: Optional[str] = Query(None)
):
    result = svc.generate_fertilization_advice(
        unit_id=unit_id,
        crop_stage=crop_stage,
        soil_n=soil_n,
        soil_p=soil_p,
        soil_k=soil_k,
        notes=notes,
    )
    return result


@router.get("/farmer/fertilization/advice/{advisory_id}")
def api_get_advice(advisory_id: str):
    rec = svc.get_advisory(advisory_id)
    if not rec:
        raise HTTPException(status_code=404, detail="advisory_not_found")
    return rec


@router.get("/farmer/fertilization/advice")
def api_list_advice(unit_id: Optional[str] = Query(None)):
    return svc.list_advisories(unit_id=unit_id)
