"""
API Routes — Weather Impact Analyzer (Farmer POV)
-------------------------------------------------

Endpoints:
 - POST /farmer/weather/impact
 - GET  /farmer/weather/impact/{eval_id}
 - GET  /farmer/weather/impact
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional

from app.services.farmer import weather_impact_service as svc

router = APIRouter()


@router.post("/farmer/weather/impact")
async def api_evaluate_weather(
    unit_id: Optional[str] = Query(None),
    temperature_c: Optional[float] = Query(None),
    humidity: Optional[float] = Query(None),
    rainfall_mm: Optional[float] = Query(None),
    wind_speed_kmh: Optional[float] = Query(None),
    heatwave_warning: Optional[bool] = Query(None),
    coldwave_warning: Optional[bool] = Query(None),
    notes: Optional[str] = Query(None)
):
    return svc.evaluate_weather_impact(
        unit_id=unit_id,
        temperature_c=temperature_c,
        humidity=humidity,
        rainfall_mm=rainfall_mm,
        wind_speed_kmh=wind_speed_kmh,
        heatwave_warning=heatwave_warning,
        coldwave_warning=coldwave_warning,
        notes=notes,
    )


@router.get("/farmer/weather/impact/{eval_id}")
def api_get_weather(eval_id: str):
    rec = svc.get_weather_impact(eval_id)
    if not rec:
        raise HTTPException(status_code=404, detail="weather_impact_not_found")
    return rec


@router.get("/farmer/weather/impact")
def api_list_weather(unit_id: Optional[str] = Query(None)):
    return svc.list_weather_impacts(unit_id=unit_id)
