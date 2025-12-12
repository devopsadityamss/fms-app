# backend/app/api/farmer/weather.py

from fastapi import APIRouter
from app.services.farmer.weather_service import (
    get_current_weather,
    get_hourly_forecast,
    get_daily_forecast,
    get_weather_risk_analysis,
)

router = APIRouter()


@router.get("/weather/{unit_id}")
def weather_overview(unit_id: int):
    """
    Returns combined weather overview for a production unit.
    """
    current = get_current_weather(unit_id)
    hourly = get_hourly_forecast(unit_id)
    daily = get_daily_forecast(unit_id)
    risk = get_weather_risk_analysis(unit_id)

    return {
        "unit_id": unit_id,
        "current": current,
        "hourly": hourly,
        "daily": daily,
        "risk": risk,
    }


@router.get("/weather/{unit_id}/current")
def weather_current(unit_id: int):
    return get_current_weather(unit_id)


@router.get("/weather/{unit_id}/hourly")
def weather_hourly(unit_id: int):
    return get_hourly_forecast(unit_id)


@router.get("/weather/{unit_id}/daily")
def weather_daily(unit_id: int):
    return get_daily_forecast(unit_id)


@router.get("/weather/{unit_id}/risk")
def weather_risk(unit_id: int):
    return get_weather_risk_analysis(unit_id)
