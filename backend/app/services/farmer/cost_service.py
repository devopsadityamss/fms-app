# backend/app/services/farmer/cost_service.py

from datetime import datetime
from typing import Dict, List, Any


# NOTE:
# This service provides mock cost estimations for:
# - current stage cost
# - upcoming stage cost
# - full season projected cost
# - operation/material cost breakdown
#
# Later this will integrate with:
# - inventory consumption
# - actual material prices
# - labor logs
# - machine rental data
# - farmer-specific cost histories
#
# For now: lightweight logic to support UI and API development.


# -------------------------------------------------------------------
# Mock cost templates for each crop stage
# -------------------------------------------------------------------

STAGE_COST_TEMPLATES = {
    "sowing": {
        "operations": [
            {"name": "Land Preparation", "cost": 800},
            {"name": "Sowing Labor", "cost": 500},
            {"name": "Seed Treatment", "cost": 200},
        ],
        "materials": [
            {"name": "Seeds", "cost": 400},
            {"name": "Basal Fertilizer", "cost": 300},
        ]
    },
    "vegetative": {
        "operations": [
            {"name": "Irrigation", "cost": 300},
            {"name": "Weeding", "cost": 600},
        ],
        "materials": [
            {"name": "Nitrogen Fertilizer", "cost": 700},
            {"name": "Pesticide A", "cost": 350},
        ]
    },
    "flowering": {
        "operations": [
            {"name": "Spraying", "cost": 400},
        ],
        "materials": [
            {"name": "Potassium Fertilizer", "cost": 650},
            {"name": "Pesticide B", "cost": 500},
        ]
    },
    "fruiting": {
        "operations": [
            {"name": "Flower to Fruit Care", "cost": 500},
            {"name": "Nutrient Spray", "cost": 300},
        ],
        "materials": [
            {"name": "Micronutrients Spray", "cost": 450},
        ]
    },
    "harvest": {
        "operations": [
            {"name": "Harvesting Labor", "cost": 1200},
            {"name": "Packaging", "cost": 500},
        ],
        "materials": [
            {"name": "Harvest Bags", "cost": 250},
        ]
    }
}


def calculate_stage_cost(stage_name: str) -> Dict[str, Any]:
    """
    Returns total cost for the given stage.
    """

    stage_data = STAGE_COST_TEMPLATES.get(stage_name.lower(), None)

    if not stage_data:
        return {
            "stage": stage_name,
            "operations": [],
            "materials": [],
            "stage_total_cost": 0
        }

    op_cost = sum(item["cost"] for item in stage_data["operations"])
    mat_cost = sum(item["cost"] for item in stage_data["materials"])

    return {
        "stage": stage_name,
        "operations": stage_data["operations"],
        "materials": stage_data["materials"],
        "operation_cost_total": op_cost,
        "material_cost_total": mat_cost,
        "stage_total_cost": op_cost + mat_cost,
    }


def calculate_season_projection(current_stage: str) -> Dict[str, Any]:
    """
    Projects full season cost from the current stage.
    """

    total_cost = 0
    stage_breakdown = []

    stage_order = ["sowing", "vegetative", "flowering", "fruiting", "harvest"]

    if current_stage.lower() not in stage_order:
        return {"total_cost_projection": 0, "stage_breakdown": []}

    start_index = stage_order.index(current_stage.lower())

    for stage in stage_order[start_index:]:
        cost_info = calculate_stage_cost(stage)
        total_cost += cost_info["stage_total_cost"]
        stage_breakdown.append(cost_info)

    return {
        "from_stage": current_stage,
        "projected_total_cost_remaining": total_cost,
        "stage_cost_breakdown": stage_breakdown
    }


def detect_cost_overrun(stage_name: str, actual_cost: float) -> Dict[str, Any]:
    """
    Compares actual cost spent vs expected cost for the stage.
    """

    expected_cost = calculate_stage_cost(stage_name)["stage_total_cost"]
    deviation = actual_cost - expected_cost

    status = (
        "under_budget" if deviation < -100 else
        "on_track" if abs(deviation) <= 100 else
        "over_budget"
    )

    return {
        "stage": stage_name,
        "expected_cost": expected_cost,
        "actual_cost": actual_cost,
        "deviation": deviation,
        "status": status,
    }


def get_cost_analysis(unit_id: int, stage_name: str, actual_cost_spent: float = 0) -> Dict[str, Any]:
    """
    Combines multiple cost-related insights for the farmer.
    """

    stage_cost_info = calculate_stage_cost(stage_name)
    season_projection = calculate_season_projection(stage_name)
    overrun_info = detect_cost_overrun(stage_name, actual_cost_spent)

    return {
        "unit_id": unit_id,
        "timestamp": datetime.utcnow(),
        "stage_cost": stage_cost_info,
        "season_projection": season_projection,
        "cost_overrun_analysis": overrun_info,
    }
