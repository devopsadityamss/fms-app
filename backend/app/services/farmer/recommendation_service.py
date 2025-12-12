# backend/app/services/farmer/recommendation_service.py

"""
Advanced Recommendation Engine

Provides:
- Next-best-action engine
- Priority scoring
- Smart task suggestions
- Scenario simulations (irrigation / fertilization / pest control)
- Unified recommendation report

Pure mock logic (no DB). Easily extendable in future.
"""

from datetime import datetime
from typing import Dict, Any, List


# ------------------------------------------
# 1. Priority Scoring
# ------------------------------------------

def compute_priority_score(
    risk_score: int,
    health_score: int,
    soil: Dict[str, Any],
    weather: Dict[str, Any],
) -> int:
    """
    Returns a score 0–100 indicating importance of taking action now.
    Higher risk + lower health + low moisture → higher priority.
    """
    risk_weight = risk_score * 0.5
    health_weight = (100 - health_score) * 0.3
    moisture = soil.get("soil_snapshot", {}).get("moisture_percent", 30)
    moisture_weight = max(0, (25 - moisture) * 1.2)  # lower moisture → higher urgency

    temp = weather.get("temperature", 28)
    temp_weight = 10 if temp > 35 else 0

    total = risk_weight + health_weight + moisture_weight + temp_weight
    return min(100, int(total))


# ------------------------------------------
# 2. Next-Best-Action Engine
# ------------------------------------------

def generate_next_best_actions(
    unit_id: int,
    stage: str,
    risk_score: int,
    soil: Dict[str, Any],
    weather: Dict[str, Any],
    pest_intel: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Returns suggested next actions in priority order.
    """
    moisture = soil.get("soil_snapshot", {}).get("moisture_percent", 30)
    actions: List[Dict[str, Any]] = []

    if moisture < 20:
        actions.append({
            "action": "Irrigate immediately",
            "reason": "Very low soil moisture",
            "priority": "high"
        })

    if len(pest_intel.get("risks", [])) > 0:
        actions.append({
            "action": "Inspect for pests / apply recommended control",
            "reason": "Detected pest/disease indicators",
            "priority": "high"
        })

    if weather.get("temperature", 28) > 35:
        actions.append({
            "action": "Shade / reduce heat stress",
            "reason": "High temperature forecast",
            "priority": "medium"
        })

    if stage.lower() == "vegetative":
        actions.append({
            "action": "Apply nitrogen fertilizer (light dose)",
            "reason": "Stage-specific growth boost",
            "priority": "medium"
        })

    if risk_score < 40:
        actions.append({
            "action": "Monitor crop, no urgent action",
            "reason": "Low unified risk",
            "priority": "low"
        })

    return actions


# ------------------------------------------
# 3. Scenario Simulation
# ------------------------------------------

def simulate_irrigation_scenario(soil: Dict[str, Any], liters: int) -> Dict[str, Any]:
    """
    Estimate soil moisture improvement from irrigation.
    """
    current = soil.get("soil_snapshot", {}).get("moisture_percent", 30)
    expected = min(60, current + liters * 0.05)
    return {
        "before_moisture": current,
        "after_moisture": expected,
        "impact": expected - current,
    }


def simulate_fertilizer_scenario(stage: str) -> Dict[str, Any]:
    """
    Dummy fertilizer impact simulation based on stage.
    """
    if stage.lower() == "vegetative":
        expected_boost = 8
    elif stage.lower() == "flowering":
        expected_boost = 5
    else:
        expected_boost = 3

    return {
        "stage": stage,
        "expected_health_boost": expected_boost,
        "message": f"Expected improvement of {expected_boost} points in health score.",
    }


def simulate_pest_control_scenario(pest_intel: Dict[str, Any]) -> Dict[str, Any]:
    count = len(pest_intel.get("risks", []))
    reduction = min(100, count * 15)
    return {
        "expected_pest_reduction_percent": reduction,
        "message": "Expected reduction in pest pressure after treatment."
    }


# ------------------------------------------
# 4. Unified Recommendation Engine Response
# ------------------------------------------

def get_recommendation_report(
    unit_id: int,
    stage: str,
    risk: Dict[str, Any],
    health: Dict[str, Any],
    soil: Dict[str, Any],
    weather: Dict[str, Any],
    pest_intel: Dict[str, Any],
) -> Dict[str, Any]:

    priority_score = compute_priority_score(
        risk_score=risk.get("unified_score", 60),
        health_score=health.get("score", 80),
        soil=soil,
        weather=weather,
    )

    next_actions = generate_next_best_actions(
        unit_id=unit_id,
        stage=stage,
        risk_score=risk.get("unified_score", 60),
        soil=soil,
        weather=weather,
        pest_intel=pest_intel,
    )

    return {
        "unit_id": unit_id,
        "timestamp": datetime.utcnow(),
        "priority_score": priority_score,
        "next_best_actions": next_actions,
        "scenario_simulation": {
            "irrigation": simulate_irrigation_scenario(soil, liters=200),
            "fertilizer": simulate_fertilizer_scenario(stage),
            "pest_control": simulate_pest_control_scenario(pest_intel),
        },
    }
