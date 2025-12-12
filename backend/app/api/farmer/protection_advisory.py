"""
API Routes — Protection Advisory (Farmer POV)

Endpoints:
 - POST /farmer/protection/advice
 - GET  /farmer/protection/advice/{advisory_id}
 - GET  /farmer/protection/advice
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from app.services.farmer import protection_advisory_service as svc

router = APIRouter()


@router.post("/farmer/protection/advice")
async def api_generate_protection_advice(
    unit_id: Optional[str] = Query(None),
    crop_stage: Optional[str] = Query(None),
    humidity: Optional[float] = Query(None),
    temperature: Optional[float] = Query(None),
    notes: Optional[str] = Query(None)
):
    result = svc.generate_protection_advice(
        unit_id=unit_id,
        crop_stage=crop_stage,
        humidity=humidity,
        temperature=temperature,
        notes=notes,
    )
    return result


@router.get("/farmer/protection/advice/{advisory_id}")
def api_get_protection_advice(advisory_id: str):
    rec = svc.get_advice(advisory_id)
    if not rec:
        raise HTTPException(status_code=404, detail="advisory_not_found")
    return rec


@router.get("/farmer/protection/advice")
def api_list_protection_advice(unit_id: Optional[str] = Query(None)):
    return svc.list_advice(unit_id=unit_id)
