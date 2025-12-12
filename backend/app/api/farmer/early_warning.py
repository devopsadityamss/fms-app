# backend/app/api/farmer/early_warning.py

from fastapi import APIRouter, Query, Body, HTTPException
from typing import Optional, Dict, Any

from app.services.farmer.early_warning_service import (
    run_check,
    get_last_warnings,
    get_history
)

router = APIRouter()

@router.get("/early-warning/{unit_id}")
def api_get_warnings(unit_id: int, crop: Optional[str] = Query(None), stage: Optional[str] = Query(None), auto_notify: Optional[bool] = Query(False)):
    """
    Returns consolidated early warnings for the unit (runs a fresh check).
    Query params:
      - crop, stage: optional contextual info
      - auto_notify: if true, send high severity notifications via notification_service (best-effort)
    """
    res = run_check(str(unit_id), crop=crop, stage=stage, auto_notify=bool(auto_notify))
    return res

@router.post("/early-warning/{unit_id}/run")
def api_run_warnings(unit_id: int, payload: Optional[Dict[str, Any]] = Body(None)):
    """
    Run a check with optional overrides in payload:
      {
        "crop": "rice",
        "stage": "flowering",
        "health_score": 45.2,
        "symptom_text": "white powdery spots",
        "weather_override": {...},
        "auto_notify": true
      }
    """
    payload = payload or {}
    try:
        res = run_check(str(unit_id),
                        crop=payload.get("crop"),
                        stage=payload.get("stage"),
                        health_score_override=payload.get("health_score"),
                        symptom_text=payload.get("symptom_text"),
                        weather_override=payload.get("weather_override"),
                        auto_notify=bool(payload.get("auto_notify", False)))
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/early-warning/{unit_id}/last")
def api_last_warnings(unit_id: int):
    return {"unit_id": unit_id, "warnings": get_last_warnings(str(unit_id))}

@router.get("/early-warning/{unit_id}/history")
def api_history(unit_id: int):
    return {"unit_id": unit_id, "history": get_history(str(unit_id))}
