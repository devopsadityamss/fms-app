# backend/app/api/farmer/action_recommendation.py

from fastapi import APIRouter, Body, Query, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.services.farmer.action_recommendation_service import generate_actions

router = APIRouter()

class ActionRequest(BaseModel):
    unit_id: Optional[int] = None
    farmer_id: Optional[str] = None
    crop: Optional[str] = None
    stage: Optional[str] = None
    area_ha: Optional[float] = None
    expected_yield_t_per_ha: Optional[float] = None
    max_actions: Optional[int] = 10
    include_opportunities: Optional[bool] = True
    include_warnings: Optional[bool] = True

@router.get("/action-recommendations/{unit_id}")
def api_get_actions(unit_id: int, farmer_id: Optional[str] = Query(None), crop: Optional[str] = Query(None), stage: Optional[str] = Query(None), area_ha: Optional[float] = Query(None), expected_yield_t_per_ha: Optional[float] = Query(None), max_actions: int = Query(10), include_opportunities: bool = Query(True), include_warnings: bool = Query(True)):
    """
    Returns recommended actions for given unit.
    """
    res = generate_actions(unit_id=unit_id, farmer_id=farmer_id, crop=crop, stage=stage, area_ha=area_ha, expected_yield_t_per_ha=expected_yield_t_per_ha, max_actions=max_actions, include_opportunities=include_opportunities, include_warnings=include_warnings)
    return res

@router.post("/action-recommendations/{unit_id}/evaluate")
def api_evaluate_actions(unit_id: int, payload: ActionRequest = Body(...)):
    body = payload.dict()
    # ensure path unit_id overrides body
    body["unit_id"] = unit_id
    res = generate_actions(
        unit_id=body.get("unit_id"),
        farmer_id=body.get("farmer_id"),
        crop=body.get("crop"),
        stage=body.get("stage"),
        area_ha=body.get("area_ha"),
        expected_yield_t_per_ha=body.get("expected_yield_t_per_ha"),
        max_actions=body.get("max_actions", 10),
        include_opportunities=body.get("include_opportunities", True),
        include_warnings=body.get("include_warnings", True)
    )
    return res
