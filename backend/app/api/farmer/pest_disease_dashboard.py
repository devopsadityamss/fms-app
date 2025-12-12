"""
API Routes — Pest & Disease Risk Dashboard (Farmer POV)
--------------------------------------------------------

Endpoints:
 - POST /farmer/pest-disease/dashboard
 - GET  /farmer/pest-disease/dashboard/{dash_id}
 - GET  /farmer/pest-disease/dashboard
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional

from app.services.farmer import pest_disease_dashboard_service as svc

router = APIRouter()


@router.post("/farmer/pest-disease/dashboard")
async def api_build_dashboard(
    unit_id: str = Query(...),

    protection_pest: Optional[float] = Query(None),
    protection_disease: Optional[float] = Query(None),

    prediction_pest: Optional[float] = Query(None),
    prediction_disease: Optional[float] = Query(None),

    weather_humidity_risk: Optional[float] = Query(None),
    weather_rainfall_risk: Optional[float] = Query(None),

    vision_pest_indicator: Optional[float] = Query(None),
    vision_leaf_stress: Optional[float] = Query(None),

    farmer_pest_sightings: Optional[float] = Query(None),
    farmer_leaf_damage: Optional[float] = Query(None),

    notes: Optional[str] = Query(None)
):
    return svc.build_risk_dashboard(
        unit_id=unit_id,
        protection_pest=protection_pest,
        protection_disease=protection_disease,
        prediction_pest=prediction_pest,
        prediction_disease=prediction_disease,
        weather_humidity_risk=weather_humidity_risk,
        weather_rainfall_risk=weather_rainfall_risk,
        vision_pest_indicator=vision_pest_indicator,
        vision_leaf_stress=vision_leaf_stress,
        farmer_pest_sightings=farmer_pest_sightings,
        farmer_leaf_damage=farmer_leaf_damage,
        notes=notes,
    )


@router.get("/farmer/pest-disease/dashboard/{dash_id}")
def api_get_dashboard(dash_id: str):
    rec = svc.get_dashboard_record(dash_id)
    if not rec:
        raise HTTPException(status_code=404, detail="dashboard_not_found")
    return rec


@router.get("/farmer/pest-disease/dashboard")
def api_list_dashboards(unit_id: Optional[str] = Query(None)):
    return svc.list_dashboards(unit_id=unit_id)
