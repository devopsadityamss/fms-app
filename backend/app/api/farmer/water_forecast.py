# backend/app/api/farmer/water_forecast.py

from fastapi import APIRouter
from typing import List, Dict, Any

from app.services.farmer.water_forecast_service import predict_water_demand
from app.services.farmer.weather_service import get_forecast_weather

router = APIRouter()

@router.get("/water-forecast/{unit_id}")
def api_water_forecast(unit_id: str, stage: str, method: str = "flood"):
    """
    Feature 319 — Water demand forecasting (7-day)
    """

    weather = get_forecast_weather(unit_id)

    et0_list = weather.get("et0_forecast", [])
    rain_list = weather.get("rain_forecast", [])

    return predict_water_demand(
        unit_id=unit_id,
        stage=stage,
        et0_forecast=et0_list,
        rainfall_forecast=rain_list,
        method=method,
        soil_moisture_pct=weather.get("soil_moisture_pct")
    )
