# backend/app/api/farmer/health.py

from fastapi import APIRouter
from app.services.farmer.health_service import get_crop_health_score
from app.services.farmer.weather_service import get_current_weather
from app.services.farmer.alert_service import get_disease_and_pest_alerts

router = APIRouter()


@router.get("/health/{unit_id}")
def health_overview(
    unit_id: int,
    stage: str,
    overdue_tasks: int = 0
):
    """
    Returns full crop health evaluation including:
    - health score (0–100)
    - status (Excellent/Good/Moderate/Poor)
    - breakdown of stress factors:
        • weather stress
        • stage sensitivity
        • task delays
        • pest & disease alerts
    """

    weather = get_current_weather(unit_id)

    # Mock pest/disease count
    pest_alerts = len(get_disease_and_pest_alerts(unit_id, stage))

    return get_crop_health_score(
        unit_id=unit_id,
        stage_name=stage,
        weather=weather,
        overdue_tasks=overdue_tasks,
        pest_disease_alerts=pest_alerts
    )


@router.get("/health/{unit_id}/score")
def health_score(unit_id: int, stage: str):
    """
    Returns only the health score value.
    """

    weather = get_current_weather(unit_id)
    pest_alerts = len(get_disease_and_pest_alerts(unit_id, stage))

    return {
        "score": get_crop_health_score(
            unit_id, stage, weather, 0, pest_alerts
        )["score"]
    }
