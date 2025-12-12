"""
API Routes — Microclimate Generator
----------------------------------

Endpoints:
 - POST /farmer/microclimate/generate
 - GET  /farmer/microclimate/{id}
 - GET  /farmer/microclimate
"""

from fastapi import APIRouter, HTTPException, Body, Query
from typing import Optional, Dict, Any

from app.services.farmer import microclimate_service as svc

router = APIRouter()


@router.post("/farmer/microclimate/generate")
async def api_generate_microclimate(payload: Dict[str, Any] = Body(...)):
    """
    Payload example:
    {
      "unit_id": "unit-12",
      "location": {"lat": 12.34, "lon": 78.9, "elevation_m": 450},
      "canopy_percent": 62.5,
      "irrigation_on": true,
      "use_weather_service": true
    }
    """
    # unit_id is optional but recommended
    return svc.generate_microclimate(
        unit_id=payload.get("unit_id"),
        location=payload.get("location"),
        canopy_percent=payload.get("canopy_percent"),
        irrigation_on=payload.get("irrigation_on", False),
        use_weather_service=payload.get("use_weather_service", True)
    )


@router.get("/farmer/microclimate/{rec_id}")
def api_get_microclimate(rec_id: str):
    rec = svc.get_microclimate(rec_id)
    if "error" in rec:
        raise HTTPException(status_code=404, detail="not_found")
    return rec


@router.get("/farmer/microclimate")
def api_list_microclimates(unit_id: Optional[str] = Query(None)):
    return svc.list_microclimates(unit_id=unit_id)
