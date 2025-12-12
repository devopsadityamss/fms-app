# backend/app/api/farmer/historical.py

from fastapi import APIRouter
from typing import Optional
from app.services.farmer.historical_service import (
    generate_historical_yield,
    generate_historical_weather,
    generate_historical_costs,
    generate_task_completion_history,
    get_historical_bundle,
)

router = APIRouter()


@router.get("/historical/{unit_id}/yield")
def historical_yield(unit_id: int, crop: Optional[str] = "generic", days: int = 365):
    return generate_historical_yield(unit_id, crop, days)


@router.get("/historical/{unit_id}/weather")
def historical_weather(unit_id: int, days: int = 90):
    return generate_historical_weather(unit_id, days)


@router.get("/historical/{unit_id}/costs")
def historical_costs(unit_id: int, days: int = 365):
    return generate_historical_costs(unit_id, days)


@router.get("/historical/{unit_id}/tasks")
def historical_tasks(unit_id: int, days: int = 90):
    return generate_task_completion_history(unit_id, days)


@router.get("/historical/{unit_id}/bundle")
def historical_bundle(unit_id: int, crop: Optional[str] = "generic"):
    """
    Returns a full bundle of historical series for dashboards/backtesting.
    """
    return get_historical_bundle(unit_id, crop)
