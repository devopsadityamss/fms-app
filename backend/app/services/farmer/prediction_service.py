# backend/app/services/farmer/prediction_service.py

from datetime import datetime, timedelta
from typing import Dict, Any


# NOTE:
# This service provides mock predictions for:
# - yield
# - harvest date
# - water requirement
# - nutrient requirement
# - cost estimation
#
# Later this will integrate with:
# - machine learning models
# - crop-specific growth models
# - soil data, weather patterns
# - stage-based nutrient curves
# - historical production data
#
# For now: clean, mock logic to support UI/API development.


def predict_yield(stage_name: str, health_score: int) -> Dict[str, Any]:
    """
    Predicts mock yield (percentage of ideal yield).
    """

    stage_penalty = {
        "sowing": 0.6,
        "vegetative": 0.8,
        "flowering": 0.9,
        "fruiting": 1.0,
        "harvest": 1.0,
    }

    base_factor = stage_penalty.get(stage_name.lower(), 0.9)

    predicted_percentage = max(40, min(100, int(health_score * base_factor)))

    return {
        "predicted_yield_percent": predicted_percentage,
        "ideal_yield_kg_per_acre": 1000,  # mock assumption
        "predicted_yield_kg_per_acre": int(10 * predicted_percentage),
    }


def predict_harvest_date(stage_name: str) -> Dict[str, Any]:
    """
    Predicts harvest date based on stage.
    """

    stage_remaining_days = {
        "sowing": 80,
        "vegetative": 60,
        "flowering": 40,
        "fruiting": 20,
        "harvest": 0,
    }

    remaining = stage_remaining_days.get(stage_name.lower(), 45)

    harvest_date = datetime.utcnow() + timedelta(days=remaining)

    return {
        "expected_harvest_date": harvest_date,
        "days_remaining": remaining,
    }


def predict_water_requirement(stage_name: str, weather: Dict[str, Any]) -> Dict[str, Any]:
    """
    Predicts water requirement for the next 7 days (mock).
    """

    base_stage_water = {
        "sowing": 10,
        "vegetative": 30,
        "flowering": 40,
        "fruiting": 35,
        "harvest": 15,
    }

    rainfall = weather.get("rainfall_mm", 0)
    stage_need = base_stage_water.get(stage_name.lower(), 25)

    # reduce irrigation need if rainfall is expected
    predicted_need = max(5, stage_need - int(rainfall * 0.3))

    return {
        "weekly_water_requirement_liters": predicted_need * 100,
        "rainfall_adjustment": rainfall,
    }


def predict_fertilizer_need(stage_name: str) -> Dict[str, Any]:
    """
    Simple fertilizer demand prediction.
    """

    stage_nutrient_map = {
        "sowing": {"N": 5, "P": 5, "K": 5},
        "vegetative": {"N": 20, "P": 10, "K": 10},
        "flowering": {"N": 15, "P": 20, "K": 20},
        "fruiting": {"N": 10, "P": 15, "K": 25},
        "harvest": {"N": 0, "P": 0, "K": 0},
    }

    return {
        "stage": stage_name,
        "nutrient_need_kg_per_acre": stage_nutrient_map.get(stage_name.lower(), {"N": 10, "P": 10, "K": 10}),
    }


def predict_cost_estimate(stage_name: str) -> Dict[str, Any]:
    """
    Mock cost estimation: based on stage workload.
    """

    stage_cost_factor = {
        "sowing": 1500,
        "vegetative": 2000,
        "flowering": 2500,
        "fruiting": 3000,
        "harvest": 5000,
    }

    cost = stage_cost_factor.get(stage_name.lower(), 2000)

    return {
        "estimated_cost_next_stage": cost,
        "stage": stage_name,
    }


def get_all_predictions(stage_name: str, health_score: int, weather: Dict[str, Any]) -> Dict[str, Any]:
    """
    Combines all prediction modules.
    """

    return {
        "timestamp": datetime.utcnow(),
        "yield_prediction": predict_yield(stage_name, health_score),
        "harvest_prediction": predict_harvest_date(stage_name),
        "water_prediction": predict_water_requirement(stage_name, weather),
        "fertilizer_prediction": predict_fertilizer_need(stage_name),
        "cost_prediction": predict_cost_estimate(stage_name),
    }
