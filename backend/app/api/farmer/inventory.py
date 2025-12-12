# backend/app/api/farmer/inventory.py

from fastapi import APIRouter
from typing import Dict, Any
from app.services.farmer.inventory_service import (
    get_stage_material_requirements,
    detect_shortages,
    generate_reorder_list,
    forecast_weekly_consumption,
    get_inventory_plan,
)

router = APIRouter()


@router.get("/inventory/{unit_id}")
def inventory_overview(unit_id: int, stage: str):
    """
    Full inventory intelligence:
    - required materials for stage
    - shortages
    - reorder list
    - weekly forecast
    """

    # Mock current stock until DB is ready
    mock_current_stock = {
        "Seeds": 1,
        "Basal Fertilizer": 5,
        "Nitrogen Fertilizer": 4,
        "Pesticide A": 0.5,
        "Potassium Fertilizer": 3,
    }

    return get_inventory_plan(
        unit_id=unit_id,
        stage_name=stage,
        current_stock=mock_current_stock
    )


@router.get("/inventory/{unit_id}/requirements")
def inventory_requirements(unit_id: int, stage: str):
    """
    Returns only material requirements for the stage.
    """
    return get_stage_material_requirements(stage)


@router.get("/inventory/{unit_id}/shortages")
def inventory_shortages(unit_id: int, stage: str):
    """
    Shows only shortages based on mock current stock.
    """

    mock_current_stock = {
        "Seeds": 1,
        "Basal Fertilizer": 5,
        "Nitrogen Fertilizer": 4,
        "Pesticide A": 0.5,
    }

    required = get_stage_material_requirements(stage)
    return detect_shortages(mock_current_stock, required)


@router.get("/inventory/{unit_id}/reorder")
def inventory_reorder(unit_id: int, stage: str):
    """
    Returns reorder suggestions only.
    """

    mock_current_stock = {
        "Seeds": 1,
        "Basal Fertilizer": 5,
        "Nitrogen Fertilizer": 4,
    }

    required = get_stage_material_requirements(stage)
    shortages = detect_shortages(mock_current_stock, required)
    return generate_reorder_list(shortages)


@router.get("/inventory/{unit_id}/weekly")
def inventory_weekly(unit_id: int, stage: str):
    """
    Shows predicted weekly material usage.
    """
    return forecast_weekly_consumption(stage)
