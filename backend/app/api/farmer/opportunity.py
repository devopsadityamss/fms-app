# backend/app/api/farmer/opportunity.py

from fastapi import APIRouter, Body, Query, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.services.farmer.opportunity_service import compute_opportunities

router = APIRouter()

class OpportunityRequest(BaseModel):
    unit_id: Optional[int] = None
    farmer_id: Optional[str] = None
    crop: Optional[str] = None
    stage: Optional[str] = None
    area_ha: Optional[float] = None
    expected_yield_t_per_ha: Optional[float] = None
    weather_override: Optional[Dict[str,Any]] = None
    max_results: Optional[int] = 10

@router.get("/opportunities/{unit_id}")
def api_get_opportunities(unit_id: int, farmer_id: Optional[str] = Query(None), crop: Optional[str] = Query(None), stage: Optional[str] = Query(None), area_ha: Optional[float] = Query(None), expected_yield_t_per_ha: Optional[float] = Query(None), max_results: int = Query(10)):
    res = compute_opportunities(unit_id=unit_id, farmer_id=farmer_id, crop=crop, stage=stage, area_ha=area_ha, expected_yield_t_per_ha=expected_yield_t_per_ha, max_results=max_results)
    return res

@router.post("/opportunities/{unit_id}/evaluate")
def api_evaluate_opportunities(unit_id: int, payload: OpportunityRequest = Body(...)):
    body = payload.dict()
    # allow unit_id in path to override body
    body["unit_id"] = unit_id
    res = compute_opportunities(
        unit_id=body.get("unit_id"),
        farmer_id=body.get("farmer_id"),
        crop=body.get("crop"),
        stage=body.get("stage"),
        area_ha=body.get("area_ha"),
        expected_yield_t_per_ha=body.get("expected_yield_t_per_ha"),
        weather_override=body.get("weather_override"),
        max_results=body.get("max_results", 10)
    )
    return res

@router.get("/opportunities/{unit_id}/raw")
def api_opportunities_raw(unit_id: int, farmer_id: Optional[str] = Query(None)):
    # same as compute_opportunities but includes a larger max_results for diagnostics
    res = compute_opportunities(unit_id=unit_id, farmer_id=farmer_id, max_results=50)
    return res
