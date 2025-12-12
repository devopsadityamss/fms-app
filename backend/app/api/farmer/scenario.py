# backend/app/api/farmer/scenario.py

from fastapi import APIRouter, Body, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.services.farmer.scenario_service import compare_scenarios, run_single_scenario, commit_scenario_as_schedule_and_executions

router = APIRouter()

class ActionModel(BaseModel):
    action: str
    category: Optional[str] = None
    priority: Optional[int] = 50
    details: Optional[Dict[str,Any]] = None

class ScenarioModel(BaseModel):
    id: Optional[str] = None
    label: Optional[str] = None
    actions: Optional[List[ActionModel]] = []
    schedule_override: Optional[Dict[str,Any]] = None
    assume_execute: Optional[bool] = False
    note: Optional[str] = None

class CompareRequest(BaseModel):
    unit_id: Optional[int] = None
    farmer_id: Optional[str] = None
    crop: Optional[str] = None
    stage: Optional[str] = None
    days: Optional[int] = 7
    weather_forecast_override: Optional[List[Dict[str,Any]]] = None
    scenarios: List[ScenarioModel]

@router.post("/scenario/compare")
def api_compare(request: CompareRequest = Body(...)):
    body = request.dict()
    try:
        scenarios = [s for s in body.get("scenarios", [])]
        res = compare_scenarios(
            unit_id=body.get("unit_id"),
            farmer_id=body.get("farmer_id"),
            scenarios=scenarios,
            days=int(body.get("days", 7)),
            crop=body.get("crop"),
            stage=body.get("stage"),
            weather_forecast_override=body.get("weather_forecast_override")
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/scenario/run")
def api_run_single(unit_id: Optional[int] = Body(None), farmer_id: Optional[str] = Body(None), scenario: ScenarioModel = Body(...), days: int = Body(7), crop: Optional[str] = Body(None), stage: Optional[str] = Body(None), weather_forecast_override: Optional[List[Dict[str,Any]]] = Body(None)):
    try:
        res = run_single_scenario(unit_id=unit_id, farmer_id=farmer_id, scenario=scenario.dict(), days=days, crop=crop, stage=stage, weather_forecast_override=weather_forecast_override)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class CommitRequest(BaseModel):
    unit_id: Optional[int] = None
    farmer_id: Optional[str] = None
    scenario: ScenarioModel
    scheduled_at_iso: Optional[str] = None
    window_hours: Optional[int] = None

@router.post("/scenario/commit")
def api_commit(payload: CommitRequest = Body(...)):
    body = payload.dict()
    try:
        res = commit_scenario_as_schedule_and_executions(unit_id=body.get("unit_id"), farmer_id=body.get("farmer_id"), scenario=body.get("scenario"), scheduled_at_iso=body.get("scheduled_at_iso"), window_hours=body.get("window_hours"))
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
