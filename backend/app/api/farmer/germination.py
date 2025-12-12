# backend/app/api/farmer/germination.py

from fastapi import APIRouter, Body, HTTPException, Query
from typing import Dict, Any, List, Optional

from app.services.farmer.germination_service import (
    predict_germination,
    train_linear_model,
    predict_with_model,
    rule_based_predict,
    list_trained_models
)

router = APIRouter()


@router.post("/germination/predict/{batch_id}")
def api_predict(batch_id: str, payload: Dict[str, Any] = Body(None), prefer_model: bool = Query(True)):
    """
    Predict germination for a batch. Optional context in payload:
      { sample_moisture_pct, storage_days, temperature_c_avg, seed_age_days, treatment_present }
    """
    ctx = payload or {}
    res = predict_germination(batch_id, context=ctx, prefer_model=prefer_model)
    return res

@router.post("/germination/train/{batch_id}")
def api_train(batch_id: str):
    """
    Train a small linear model for the batch using historic germination tests (if enough).
    """
    res = train_linear_model(batch_id)
    if res.get("error"):
        raise HTTPException(status_code=400, detail=res)
    return res

@router.post("/germination/predict-with-model/{batch_id}")
def api_predict_model(batch_id: str, payload: Dict[str, Any] = Body(None)):
    ctx = payload or {}
    res = predict_with_model(batch_id, context=ctx)
    if res.get("error"):
        raise HTTPException(status_code=404, detail=res)
    return res

@router.get("/germination/models")
def api_list_models():
    return list_trained_models()

@router.get("/germination/rule/{batch_id}")
def api_rule_predict(batch_id: str, sample_moisture_pct: Optional[float] = Query(None), storage_days: Optional[int] = Query(None), treatment_present: Optional[bool] = Query(None)):
    ctx = {"sample_moisture_pct": sample_moisture_pct, "storage_days": storage_days, "treatment_present": treatment_present}
    return rule_based_predict(batch_id, ctx)
