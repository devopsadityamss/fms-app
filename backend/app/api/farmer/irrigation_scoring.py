# backend/app/api/farmer/irrigation_scoring.py

from fastapi import APIRouter, Body, HTTPException, Query
from typing import Dict, Any, List, Optional

from app.services.farmer.irrigation_scoring_service import (
    score_irrigation_log,
    get_score_by_log,
    list_scores_for_unit,
    top_scores_for_unit
)

router = APIRouter()


@router.post("/irrigation/score")
def api_score_irrigation(payload: Dict[str, Any] = Body(...)):
    """
    Score a single irrigation log.
    Payload should contain the irrigation_log dict, and optionally predicted_liters and channels list.
    """
    irrigation_log = payload.get("irrigation_log")
    if not irrigation_log:
        raise HTTPException(status_code=400, detail="missing irrigation_log")
    predicted = payload.get("predicted_liters")
    channels = payload.get("channels")
    return score_irrigation_log(irrigation_log, predicted_liters=predicted, channels=channels)


@router.get("/irrigation/score/log/{log_id}")
def api_get_score_for_log(log_id: str):
    res = get_score_by_log(log_id)
    if not res:
        raise HTTPException(status_code=404, detail="score_not_found")
    return res


@router.get("/irrigation/scores/unit/{unit_id}")
def api_list_scores(unit_id: str, limit: int = Query(200)):
    return {"unit_id": unit_id, "scores": list_scores_for_unit(unit_id, limit=limit)}


@router.get("/irrigation/scores/unit/{unit_id}/top")
def api_top_scores(unit_id: str, n: int = Query(10, ge=1, le=100)):
    return {"unit_id": unit_id, "top_scores": top_scores_for_unit(unit_id, top_n=n)}
