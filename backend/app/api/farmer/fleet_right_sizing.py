# backend/app/api/farmer/fleet_right_sizing.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional

from app.services.farmer.fleet_right_sizing_service import (
    analyze_right_sizing,
    fetch_last_rightsizing
)

router = APIRouter()


class RightsizeRequest(BaseModel):
    unit_plans: List[Dict]
    season_months: Optional[int] = 6
    target_utilization_pct: Optional[int] = 65
    max_purchase_unit_cost: Optional[Dict[str, float]] = None


@router.post("/fleet/right-sizing")
def api_right_sizing(req: RightsizeRequest):
    if not req.unit_plans:
        raise HTTPException(status_code=400, detail="unit_plans_required")
    res = analyze_right_sizing(
        unit_plans=req.unit_plans,
        season_months=req.season_months or 6,
        target_utilization_pct=req.target_utilization_pct or 65,
        max_purchase_unit_cost=req.max_purchase_unit_cost or None
    )
    return res


@router.get("/fleet/right-sizing/last")
def api_last_rightsizing():
    items = fetch_last_rightsizing(recent_n=1)
    return {"count": len(items), "last": items[0] if items else None}
