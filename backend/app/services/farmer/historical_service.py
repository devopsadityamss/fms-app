# backend/app/services/farmer/historical_service.py

"""
Historical data mock generator for:
- historical yields
- historical weather series
- historical cost & expense history
- historical task completion rates

All outputs are mock-only (no DB). Useful for frontend charts,
backtesting, and validating UI components before real data is available.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List
import random

random.seed(42)


def _date_series(days: int) -> List[datetime]:
    today = datetime.utcnow().date()
    return [today - timedelta(days=(days - i - 1)) for i in range(days)]


def generate_historical_yield(unit_id: int, crop: str = "generic", days: int = 365) -> Dict[str, Any]:
    """
    Returns a mock daily yield series (kg/day) aggregated per day for the past 'days'.
    For simplicity we produce a seasonal sinusoidal-like pattern with noise.
    """
    dates = _date_series(days)
    base = 50  # base kg/day
    series = []
    for i, d in enumerate(dates):
        seasonal = base + (10 * (1 + random.uniform(-0.2, 0.2)) * (1 + (i % 90) / 90.0))
        noise = random.uniform(-5, 5)
        series.append({"date": d, "kg": max(0, round(seasonal + noise, 2))})
    return {"unit_id": unit_id, "crop": crop, "series": series}


def generate_historical_weather(unit_id: int, days: int = 90) -> Dict[str, Any]:
    """
    Returns mock historical daily weather metrics for the last 'days' days.
    """
    dates = _date_series(days)
    series = []
    for i, d in enumerate(dates):
        temp = round(25 + 6 * ((i % 30) / 30.0) + random.uniform(-3, 3), 1)
        rain = round(max(0, random.gauss(3, 5)), 1)  # mm
        humidity = int(50 + random.uniform(-15, 20))
        series.append({"date": d, "temperature": temp, "rainfall_mm": rain, "humidity": humidity})
    return {"unit_id": unit_id, "series": series}


def generate_historical_costs(unit_id: int, days: int = 365) -> Dict[str, Any]:
    """
    Returns mock historical daily cost/spend series.
    """
    dates = _date_series(days)
    series = []
    for i, d in enumerate(dates):
        op_cost = round(max(0, random.gauss(50, 20)), 2)
        mat_cost = round(max(0, random.gauss(30, 15)), 2)
        series.append({"date": d, "operation_cost": op_cost, "material_cost": mat_cost, "total": round(op_cost + mat_cost, 2)})
    return {"unit_id": unit_id, "series": series}


def generate_task_completion_history(unit_id: int, days: int = 90) -> Dict[str, Any]:
    """
    Returns mock daily task completion % (0-100) to simulate operational adherence.
    """
    dates = _date_series(days)
    series = []
    for i, d in enumerate(dates):
        completion = int(max(40, min(100, random.gauss(80, 12))))
        series.append({"date": d, "completion_percent": completion})
    return {"unit_id": unit_id, "series": series}


def get_historical_bundle(unit_id: int, crop: str = "generic") -> Dict[str, Any]:
    """
    Return a unified bundle of historical datasets useful for dashboards and backtests.
    """
    return {
        "unit_id": unit_id,
        "timestamp": datetime.utcnow(),
        "yield": generate_historical_yield(unit_id, crop, days=365),
        "weather": generate_historical_weather(unit_id, days=90),
        "costs": generate_historical_costs(unit_id, days=365),
        "tasks": generate_task_completion_history(unit_id, days=90),
    }
