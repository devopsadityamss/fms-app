# backend/app/api/farmer/cost.py

from fastapi import APIRouter
from app.services.farmer.cost_service import (
    calculate_stage_cost,
    calculate_season_projection,
    detect_cost_overrun,
    get_cost_analysis,
)

router = APIRouter()


@router.get("/cost/{unit_id}")
def cost_overview(unit_id: int, stage: str, actual_cost: float = 0):
    """
    Full cost intelligence for a production unit:
    - stage cost breakdown
    - projected season cost
    - cost overrun analysis
    """

    return get_cost_analysis(
        unit_id=unit_id,
        stage_name=stage,
        actual_cost_spent=actual_cost
    )


@router.get("/cost/{unit_id}/stage")
def cost_stage(unit_id: int, stage: str):
    """
    Returns cost breakdown of the selected stage:
    - operations cost
    - materials cost
    - total stage cost
    """
    return calculate_stage_cost(stage)


@router.get("/cost/{unit_id}/projection")
def cost_projection(unit_id: int, stage: str):
    """
    Returns projected total cost from this stage to harvest.
    """
    return calculate_season_projection(stage)


@router.get("/cost/{unit_id}/overrun")
def cost_overrun(unit_id: int, stage: str, actual_cost: float):
    """
    Compares actual spending vs expected cost.
    """
    return detect_cost_overrun(stage, actual_cost)
