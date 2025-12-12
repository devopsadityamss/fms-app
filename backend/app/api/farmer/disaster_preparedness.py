"""
API Routes — Disaster Preparedness Index (Farmer POV)
-----------------------------------------------------

Endpoints:
 - POST /farmer/disaster/evaluate
 - GET  /farmer/disaster/{eval_id}
 - GET  /farmer/disaster
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional

from app.services.farmer import disaster_preparedness_service as svc

router = APIRouter()


@router.post("/farmer/disaster/evaluate")
async def api_evaluate_disaster(
    unit_id: Optional[str] = Query(None),
    rainfall_mm: Optional[float] = Query(None),
    temperature_c: Optional[float] = Query(None),
    wind_speed_kmh: Optional[float] = Query(None),
    soil_moisture: Optional[float] = Query(None),
    flood_zone: Optional[bool] = Query(None),
    drought_zone: Optional[bool] = Query(None),
    hazard_level: Optional[str] = Query(None),
    notes: Optional[str] = Query(None)
):
    return svc.evaluate_disaster_preparedness(
        unit_id=unit_id,
        rainfall_mm=rainfall_mm,
        temperature_c=temperature_c,
        wind_speed_kmh=wind_speed_kmh,
        soil_moisture=soil_moisture,
        flood_zone=flood_zone,
        drought_zone=drought_zone,
        hazard_level=hazard_level,
        notes=notes,
    )


@router.get("/farmer/disaster/{eval_id}")
def api_get_disaster(eval_id: str):
    rec = svc.get_preparedness_record(eval_id)
    if not rec:
        raise HTTPException(status_code=404, detail="disaster_record_not_found")
    return rec


@router.get("/farmer/disaster")
def api_list_disaster(unit_id: Optional[str] = Query(None)):
    return svc.list_preparedness(unit_id=unit_id)
