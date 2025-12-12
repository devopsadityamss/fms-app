"""
API Routes — Growth Deviation Analysis (Farmer POV)

Endpoints:
 - POST /farmer/growth/deviation/analyze
 - GET  /farmer/growth/deviation/{advisory_id}
 - GET  /farmer/growth/deviation
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional

from app.services.farmer import growth_deviation_service as svc

router = APIRouter()


@router.post("/farmer/growth/deviation/analyze")
async def api_analyze_growth(
    unit_id: Optional[str] = Query(None),
    expected_height: Optional[float] = Query(None),
    observed_height: Optional[float] = Query(None),
    canopy_coverage: Optional[float] = Query(None),
    ndvi_score: Optional[float] = Query(None),
    crop_stage: Optional[str] = Query(None),
    notes: Optional[str] = Query(None)
):
    result = svc.analyze_growth(
        unit_id=unit_id,
        expected_height=expected_height,
        observed_height=observed_height,
        canopy_coverage=canopy_coverage,
        ndvi_score=ndvi_score,
        crop_stage=crop_stage,
        notes=notes,
    )
    return result


@router.get("/farmer/growth/deviation/{advisory_id}")
def api_get_growth_deviation(advisory_id: str):
    rec = svc.get_growth_analysis(advisory_id)
    if not rec:
        raise HTTPException(status_code=404, detail="growth_deviation_not_found")
    return rec


@router.get("/farmer/growth/deviation")
def api_list_growth_deviation(unit_id: Optional[str] = Query(None)):
    return svc.list_growth_analyses(unit_id=unit_id)
