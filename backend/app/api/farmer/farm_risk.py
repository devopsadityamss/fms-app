# backend/app/api/farmer/farm_risk.py

from fastapi import APIRouter, Query
from typing import Optional, Dict, Any

from app.services.farmer.farm_risk_service import compute_risk_score

router = APIRouter()

@router.get("/farm-risk/{unit_id}")
def api_farm_risk(
    unit_id: int,
    farmer_id: Optional[str] = Query(None),
    health_score: Optional[float] = Query(None),
    pest_alerts_count: Optional[int] = Query(None),
    crop: Optional[str] = Query(None),
    stage: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """
    Return unified farm risk summary. Accepts optional overrides:
      - health_score (0..100)
      - pest_alerts_count (int)
      - crop, stage (for stage vulnerability)
    """
    res = compute_risk_score(
        unit_id=unit_id,
        farmer_id=farmer_id,
        pest_alerts_count=pest_alerts_count,
        health_score=health_score,
        crop=crop,
        stage=stage
    )
    return res

@router.get("/farm-risk/{unit_id}/components")
def api_farm_risk_components(unit_id: int, farmer_id: Optional[str] = Query(None)):
    """
    Return raw components used in risk computation for debugging / UI dashboards.
    """
    res = compute_risk_score(unit_id=unit_id, farmer_id=farmer_id)
    return {"unit_id": unit_id, "components": res.get("components", {}), "generated_at": res.get("generated_at")}
