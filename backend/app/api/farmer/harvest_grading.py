# backend/app/api/farmer/harvest_grading.py

from fastapi import APIRouter, Body, HTTPException, Query
from typing import Dict, Any, Optional

from app.services.farmer.harvest_grading_service import (
    compute_moisture_score,
    auto_grade_lot,
    moisture_trend,
    recommend_drying_action,
    grade_summary_for_farmer
)

router = APIRouter()


@router.get("/harvest/lot/{lot_id}/moisture-score")
def api_moisture_score(lot_id: str):
    res = compute_moisture_score(lot_id)
    if res.get("score") is None and res.get("reason"):
        raise HTTPException(status_code=404, detail=res)
    return res


@router.post("/harvest/lot/{lot_id}/auto-grade")
def api_auto_grade(lot_id: str):
    res = auto_grade_lot(lot_id)
    if res.get("error"):
        raise HTTPException(status_code=404, detail=res)
    return res


@router.get("/harvest/lot/{lot_id}/moisture-trend")
def api_moisture_trend(lot_id: str):
    return moisture_trend(lot_id)


@router.get("/harvest/lot/{lot_id}/drying-recommendation")
def api_drying_recommendation(lot_id: str, ambient_temp_c: Optional[float] = Query(None), ambient_humidity_pct: Optional[float] = Query(None)):
    res = recommend_drying_action(lot_id, ambient_temp_c=ambient_temp_c, ambient_humidity_pct=ambient_humidity_pct)
    if res.get("error"):
        raise HTTPException(status_code=404, detail=res)
    return res


@router.get("/harvest/farmer/{farmer_id}/grade-summary")
def api_grade_summary(farmer_id: str):
    return grade_summary_for_farmer(farmer_id)
