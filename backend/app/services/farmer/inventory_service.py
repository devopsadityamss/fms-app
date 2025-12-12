# backend/app/services/farmer/inventory_service.py

from datetime import datetime
from typing import Dict, List, Any


# NOTE:
# This service forecasts inventory consumption & requirements based on:
# - crop stage
# - typical usage patterns
# - upcoming tasks
# - predicted yield
#
# Later this will integrate with:
# - actual inventory tables
# - operations & materials mapping
# - task logs
# - purchase orders
#
# For now: mock logic for UI and API development.


# -------------------------------------------------------------------
# Mock material consumption rules based on crop stages
# -------------------------------------------------------------------

STAGE_MATERIAL_MAP = {
    "sowing": [
        {"material": "Seeds", "quantity_kg": 2},
        {"material": "Basal Fertilizer", "quantity_kg": 10},
    ],
    "vegetative": [
        {"material": "Nitrogen Fertilizer", "quantity_kg": 15},
        {"material": "Pesticide A", "quantity_l": 1},
    ],
    "flowering": [
        {"material": "Potassium Fertilizer", "quantity_kg": 12},
        {"material": "Pesticide B", "quantity_l": 1.5},
    ],
    "fruiting": [
        {"material": "Micronutrients Spray", "quantity_l": 2},
        {"material": "Organic Booster", "quantity_l": 1},
    ],
    "harvest": [
        {"material": "Harvest Bags", "quantity_units": 50},
        {"material": "Storage Sheets", "quantity_units": 10},
    ],
}


def get_stage_material_requirements(stage_name: str) -> List[Dict[str, Any]]:
    """
    Returns a mock material requirement list for the given stage.
    """

    return STAGE_MATERIAL_MAP.get(stage_name.lower(), [])


# -------------------------------------------------------------------
# Shortage Detection & Reorder Suggestions
# -------------------------------------------------------------------

def detect_shortages(
    current_stock: Dict[str, float],
    required_materials: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Compares stock vs requirements and identifies shortages.
    
    current_stock format:
        { "Seeds": 1, "Nitrogen Fertilizer": 5 }

    required_materials format:
        [ { "material": "Seeds", "quantity_kg": 2 }, ... ]
    """

    shortages = []

    for item in required_materials:
        material = item["material"]

        # quantity field may vary (kg / l / units)
        quantity_key = [k for k in item.keys() if k.startswith("quantity")][0]
        required_qty = item[quantity_key]
        available_qty = current_stock.get(material, 0)

        if available_qty < required_qty:
            shortages.append({
                "material": material,
                "required_qty": required_qty,
                "available_qty": available_qty,
                "shortage_qty": required_qty - available_qty,
                "status": "shortage",
                "suggestion": f"Reorder {required_qty - available_qty} units"
            })

    return shortages


def generate_reorder_list(shortages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Generates a clean reorder list for procurement planning.
    """

    reorder_items = []

    for s in shortages:
        reorder_items.append({
            "material": s["material"],
            "quantity_to_order": s["shortage_qty"],
            "priority": "high" if s["shortage_qty"] > 5 else "medium"
        })

    return reorder_items


# -------------------------------------------------------------------
# Forecasting for next 7 days
# -------------------------------------------------------------------

def forecast_weekly_consumption(stage_name: str) -> List[Dict[str, Any]]:
    """
    Mock forecast of materials needed for upcoming days.
    """

    stage_materials = get_stage_material_requirements(stage_name)

    weekly_forecast = []

    for item in stage_materials:
        # Assume equal distribution over 7 days
        quantity_key = [k for k in item.keys() if k.startswith("quantity")][0]
        per_day = item[quantity_key] / 7

        weekly_forecast.append({
            "material": item["material"],
            "daily_usage_estimate": round(per_day, 2),
            "weekly_usage_estimate": item[quantity_key],
        })

    return weekly_forecast


# -------------------------------------------------------------------
# Unified Inventory Intelligence Output
# -------------------------------------------------------------------

def get_inventory_plan(
    unit_id: int,
    stage_name: str,
    current_stock: Dict[str, float]
) -> Dict[str, Any]:
    """
    Combines:
    - stage requirements
    - shortage detection
    - reorder suggestions
    - weekly consumption forecast
    """

    required_materials = get_stage_material_requirements(stage_name)
    shortages = detect_shortages(current_stock, required_materials)
    reorder_list = generate_reorder_list(shortages)
    weekly_forecast = forecast_weekly_consumption(stage_name)

    return {
        "unit_id": unit_id,
        "timestamp": datetime.utcnow(),
        "stage": stage_name,
        "required_materials": required_materials,
        "shortages": shortages,
        "reorder_list": reorder_list,
        "weekly_forecast": weekly_forecast
    }
