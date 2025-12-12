from fastapi import APIRouter
from app.services.farmer.water_budget_service import water_budget_summary

router = APIRouter()

@router.get("/water/{unit_id}/budget")
def api_water_budget(
    unit_id: str,
    crop: str,
    area_acres: float,
    season_days: int,
    avg_et0_mm: float = 4.0,
    kc: float = 1.0,
    expected_rain_mm: float = 250
):
    return water_budget_summary(
        unit_id, crop, area_acres, season_days,
        avg_et0_mm, kc, expected_rain_mm
    )
