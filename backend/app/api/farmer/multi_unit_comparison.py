"""
API Routes — Multi-Unit Comparison Engine
-----------------------------------------

Endpoints:
 - POST /farmer/comparison/units
 - GET  /farmer/comparison/{comp_id}
 - GET  /farmer/comparison
"""

from fastapi import APIRouter, HTTPException, Body
from typing import List, Dict, Any, Optional

from app.services.farmer import multi_unit_comparison_service as svc

router = APIRouter()


@router.post("/farmer/comparison/units")
async def api_compare_units(
    units: List[Dict[str, Any]] = Body(...),
    notes: Optional[str] = Body(None)
):
    """
    Example payload:
    [
      {
        "unit_id": "u1",
        "yield_kg": 5200,
        "ndvi": 0.58,
        "canopy": 0.55,
        "pest_risk": 0.22,
        "disease_risk": 0.18,
        "water_usage_liters": 12000,
        "profit_estimate": 85000,
        "growth_delta": 5
      },
      {
        "unit_id": "u2",
        "yield_kg": 4700,
        "ndvi": 0.62,
        "canopy": 0.58,
        "pest_risk": 0.35,
        "disease_risk": 0.25,
        "water_usage_liters": 13500,
        "profit_estimate": 78000,
        "growth_delta": -2
      }
    ]
    """
    return svc.compare_units(units, notes=notes)


@router.get("/farmer/comparison/{comp_id}")
def api_get_comparison(comp_id: str):
    rec = svc.get_comparison(comp_id)
    if not rec:
        raise HTTPException(status_code=404, detail="comparison_not_found")
    return rec


@router.get("/farmer/comparison")
def api_list_comparisons():
    return svc.list_comparisons()
