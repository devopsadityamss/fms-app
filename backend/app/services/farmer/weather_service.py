# backend/app/services/farmer/weather_service.py

from datetime import datetime, timedelta
from typing import Dict, Any

# NOTE:
# This file intentionally avoids database usage.
# All values are mock responses to allow UI + API development
# before finalizing database design.


def get_current_weather(unit_id: int) -> Dict[str, Any]:
    """
    Returns mock current weather for a production unit.
    Later this will call external APIs (OpenWeather, NASA, IMD, etc.)
    """

    return {
        "unit_id": unit_id,
        "timestamp": datetime.utcnow(),
        "temperature": 28.4,
        "humidity": 62,
        "wind_speed": 5.2,
        "rainfall_mm": 0,
        "condition": "Sunny",
        "risk_level": "low",
        "risk_reason": None,
    }


def get_hourly_forecast(unit_id: int):
    """
    Mock 12-hour forecast data.
    """

    now = datetime.utcnow()
    return [
        {
            "time": now + timedelta(hours=i),
            "temperature": 27.5 + (i * 0.2),
            "rain_chance": max(0, (i - 6) * 5),
            "condition": "Clear" if i < 6 else "Cloudy",
        }
        for i in range(12)
    ]


def get_daily_forecast(unit_id: int):
    """
    Mock 7-day forecast data.
    """

    base_temp = 28
    return [
        {
            "day": (datetime.utcnow() + timedelta(days=i)).date(),
            "temperature": base_temp + (i * 0.3),
            "rain_chance": 20 if i % 2 == 0 else 40,
            "condition": "Sunny" if i % 2 == 0 else "Partly Cloudy",
        }
        for i in range(7)
    ]


def get_weather_risk_analysis(unit_id: int):
    """
    Generates basic mock risk analysis based on forecast.
    """

    daily = get_daily_forecast(unit_id)
    today = daily[0]

    risk = "low"
    reason = None

    if today["rain_chance"] > 50:
        risk = "medium"
        reason = "High chance of rain — monitor irrigation and field conditions"

    if today["temperature"] > 34:
        risk = "medium"
        reason = "High temperature — risk of crop heat stress"

    return {
        "risk_level": risk,
        "reason": reason,
        "today": today,
        "unit_id": unit_id,
    }
