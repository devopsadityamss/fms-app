# backend/app/api/farmer/prediction.py

from fastapi import APIRouter
from app.services.farmer.prediction_service import (
    predict_yield,
    predict_harvest_date,
    predict_water_requirement,
    predict_fertilizer_need,
    predict_cost_estimate,
    get_all_predictions,
)
from app.services.farmer.weather_service import get_current_weather
from app.services.farmer.health_service import get_crop_health_score

router = APIRouter()


@router.get("/predictions/{unit_id}")
def predictions_overview(unit_id: int, stage: str):
    """
    Returns all predictions:
    - yield % and expected yield
    - expected harvest date
    - water requirement
    - fertilizer requirement
    - cost prediction
    """

    weather = get_current_weather(unit_id)

    # Estimate health score for better accuracy
    health = get_crop_health_score(unit_id, stage, weather)
    health_score = health["score"]

    return get_all_predictions(
        stage_name=stage,
        health_score=health_score,
        weather=weather
    )


@router.get("/predictions/{unit_id}/yield")
def prediction_yield(unit_id: int, stage: str):
    weather = get_current_weather(unit_id)
    health = get_crop_health_score(unit_id, stage, weather)
    return predict_yield(stage, health["score"])


@router.get("/predictions/{unit_id}/harvest")
def prediction_harvest(unit_id: int, stage: str):
    return predict_harvest_date(stage)


@router.get("/predictions/{unit_id}/water")
def prediction_water(unit_id: int, stage: str):
    weather = get_current_weather(unit_id)
    return predict_water_requirement(stage, weather)


@router.get("/predictions/{unit_id}/fertilizer")
def prediction_fertilizer(unit_id: int, stage: str):
    return predict_fertilizer_need(stage)


@router.get("/predictions/{unit_id}/cost")
def prediction_cost(unit_id: int, stage: str):
    return predict_cost_estimate(stage)
