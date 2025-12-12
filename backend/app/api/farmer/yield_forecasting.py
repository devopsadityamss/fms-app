# backend/app/api/farmer/yield_forecasting.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.services.farmer.yield_forecasting_service import (
    forecast_yield_for_unit
)

router = APIRouter()


class WeatherPayload(BaseModel):
    rain_mm: Optional[float] = None
    temp_c: Optional[float] = None
    humidity: Optional[float] = None


class SoilPayload(BaseModel):
    ph: Optional[float] = None
    organic_carbon: Optional[float] = None
    ec: Optional[float] = None


class YieldForecastRequest(BaseModel):
    crop_price_per_quintal: Optional[float] = None
    weather: Optional[WeatherPayload] = None
    soil_quality: Optional[SoilPayload] = None


@router.post("/yield/forecast/{unit_id}")
def api_yield_forecast(unit_id: str, req: YieldForecastRequest):
    result = forecast_yield_for_unit(
        unit_id,
        crop_price_per_quintal=req.crop_price_per_quintal,
        weather=req.weather.dict() if req.weather else None,
        soil_quality=req.soil_quality.dict() if req.soil_quality else None
    )

    if result.get("status") == "unit_not_found":
        raise HTTPException(status_code=404, detail="unit_not_found")

    return result
