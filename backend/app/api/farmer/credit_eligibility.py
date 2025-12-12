# backend/app/api/farmer/credit_eligibility.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.services.farmer.credit_eligibility_service import (
    compute_credit_score,
    fetch_recent_applications
)

router = APIRouter()


class CreditScoreRequest(BaseModel):
    farmer_id: Optional[str] = None
    unit_id: Optional[str] = None
    market_price_per_quintal: Optional[float] = None
    weights: Optional[Dict[str, float]] = None


@router.post("/credit/score")
def api_compute_credit(req: CreditScoreRequest):
    res = compute_credit_score(
        farmer_id=req.farmer_id,
        unit_id=req.unit_id,
        market_price_per_quintal=req.market_price_per_quintal,
        weights=req.weights
    )
    return res


@router.get("/credit/applications")
def api_recent_apps(limit: int = 10):
    return {"applications": fetch_recent_applications(limit)}
