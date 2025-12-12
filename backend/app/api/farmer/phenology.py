"""
API — Phenology Progress Estimator
----------------------------------

Endpoints:
 - POST /farmer/phenology/analyze
 - GET  /farmer/phenology/{id}
 - GET  /farmer/phenology
"""

from fastapi import APIRouter, HTTPException, Body, Query
from typing import Dict, Any, Optional

from app.services.farmer import phenology_service as svc

router = APIRouter()


@router.post("/farmer/phenology/analyze")
async def api_analyze_phenology(payload: Dict[str, Any] = Body(...)):
    required = ["unit_id", "crop_type", "sowing_date"]
    for r in required:
        if r not in payload:
            raise HTTPException(status_code=400, detail=f"{r} is required")

    return svc.analyze_phenology(
        unit_id=payload["unit_id"],
        crop_type=payload["crop_type"],
        sowing_date=payload["sowing_date"],
        canopy_photo_id=payload.get("canopy_photo_id"),
        field_notes=payload.get("field_notes")
    )


@router.get("/farmer/phenology/{phenology_id}")
def api_get_phenology(phenology_id: str):
    rec = svc.get_record(phenology_id)
    if "error" in rec:
        raise HTTPException(status_code=404, detail="not_found")
    return rec


@router.get("/farmer/phenology")
def api_list_phenology(unit_id: Optional[str] = Query(None)):
    return svc.list_records(unit_id)
