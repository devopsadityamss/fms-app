# backend/app/services/farmer/health_service.py

from datetime import datetime
from typing import Dict, Any


# NOTE:
# This service evaluates mock crop health by combining:
# - weather stress indicators
# - stage-based expected growth
# - missed task impact
# - pest/disease risks (from alert_service)
#
# Later this will integrate with:
# - satellite/sensor data
# - ML health scoring models
# - real yield estimators
# - soil data
#
# Right now: clean mock logic for UI + API testing.


def compute_weather_stress(weather: Dict[str, Any]) -> Dict[str, Any]:
    """
    Returns a weather stress score (0–30 points).
    Higher the stress → lower the health score.
    """

    temp = weather.get("temperature", 28)
    humidity = weather.get("humidity", 60)

    stress = 0
    reasons = []

    if temp > 34:
        stress += 12
        reasons.append("High temperature causing heat stress")

    if temp < 15:
        stress += 10
        reasons.append("Low temperature causing growth slowdown")

    if humidity > 85:
        stress += 8
        reasons.append("High humidity increasing fungal risk")

    return {"stress": stress, "reasons": reasons}


def compute_stage_health(stage_name: str) -> Dict[str, Any]:
    """
    Stage-based health baseline.
    Some stages are naturally more sensitive.
    """

    stage_name = stage_name.lower()

    stage_weights = {
        "sowing": 20,
        "vegetative": 10,
        "flowering": 15,
        "fruiting": 10,
        "harvest": 5,
    }

    # Higher weight means more sensitivity (more penalty)
    sensitivity = stage_weights.get(stage_name, 10)

    return {"stress": sensitivity, "stage_sensitivity": sensitivity}


def compute_task_impact(overdue_tasks: int) -> Dict[str, Any]:
    """
    Overdue tasks reduce health because missed irrigation, fertilization, or spraying
    has immediate & measurable impact.
    """

    penalty = min(overdue_tasks * 5, 25)  # cap penalty at 25

    return {
        "stress": penalty,
        "overdue_tasks": overdue_tasks,
        "reason": "Some critical tasks are overdue" if overdue_tasks > 0 else None,
    }


def compute_pest_disease_impact(pest_disease_alerts: int) -> Dict[str, Any]:
    """
    Each pest/disease alert adds risk/stress to crop health.
    """

    stress = min(pest_disease_alerts * 7, 30)

    return {
        "stress": stress,
        "alert_count": pest_disease_alerts,
    }


def get_crop_health_score(
    unit_id: int,
    stage_name: str,
    weather: Dict[str, Any],
    overdue_tasks: int = 0,
    pest_disease_alerts: int = 0
) -> Dict[str, Any]:
    """
    Unified crop health score (0–100)
    Higher score → healthier crop.
    """

    weather_stress = compute_weather_stress(weather)
    stage_stress = compute_stage_health(stage_name)
    task_stress = compute_task_impact(overdue_tasks)
    pest_stress = compute_pest_disease_impact(pest_disease_alerts)

    # Total stress = sum
    total_stress = (
        weather_stress["stress"]
        + stage_stress["stress"]
        + task_stress["stress"]
        + pest_stress["stress"]
    )

    # Convert to score
    health_score = max(0, 100 - total_stress)  # Ensure not negative

    health_status = (
        "Excellent" if health_score > 85 else
        "Good" if health_score > 70 else
        "Moderate" if health_score > 50 else
        "Poor"
    )

    return {
        "unit_id": unit_id,
        "timestamp": datetime.utcnow(),
        "score": health_score,
        "status": health_status,

        # Breakdown
        "weather_stress": weather_stress,
        "stage_stress": stage_stress,
        "task_stress": task_stress,
        "pest_stress": pest_stress,

        # Summary
        "total_stress": total_stress,
        "summary": [
            *weather_stress["reasons"],
            task_stress.get("reason"),
        ]
    }
