# backend/app/api/farmer/alert.py

from fastapi import APIRouter
from app.services.farmer.alert_service import (
    get_weather_alerts,
    get_disease_and_pest_alerts,
    get_task_alerts,
    get_growth_anomaly_alerts,
    get_all_alerts,
)
from app.services.farmer.weather_service import get_current_weather

router = APIRouter()


@router.get("/alerts/{unit_id}")
def alert_overview(unit_id: int, stage: str, overdue_tasks: int = 0):
    """
    Full alert package combining:
    - weather alerts
    - pest/disease alerts
    - task alerts
    - growth anomaly alerts
    """

    weather = get_current_weather(unit_id)

    return get_all_alerts(
        unit_id=unit_id,
        stage_name=stage,
        weather=weather,
        overdue_tasks=overdue_tasks
    )


@router.get("/alerts/{unit_id}/weather")
def alert_weather(unit_id: int):
    weather = get_current_weather(unit_id)
    return get_weather_alerts(unit_id, weather)


@router.get("/alerts/{unit_id}/pest-disease")
def alert_pest_disease(unit_id: int, stage: str):
    return get_disease_and_pest_alerts(unit_id, stage)


@router.get("/alerts/{unit_id}/tasks")
def alert_tasks(unit_id: int, overdue_tasks: int = 0):
    return get_task_alerts(unit_id, overdue_tasks)


@router.get("/alerts/{unit_id}/growth")
def alert_growth(unit_id: int):
    return get_growth_anomaly_alerts(unit_id)
