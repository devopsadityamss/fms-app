from fastapi import APIRouter
from app.services.farmer.water_deficit_service import (
    calculate_daily_deficit,
    weekly_water_deficit_summary,
    list_water_deficit_alerts
)

router = APIRouter()


@router.get("/water/{unit_id}/deficit/daily")
def api_daily_deficit(unit_id: str, crop: str, area_acres: float, kc: float):
    return calculate_daily_deficit(unit_id, crop, area_acres, kc)


@router.get("/water/{unit_id}/deficit/weekly")
def api_weekly_deficit(unit_id: str, crop: str, area_acres: float, kc: float):
    return weekly_water_deficit_summary(unit_id, crop, area_acres, kc)


@router.get("/water/{unit_id}/deficit/alerts")
def api_list_deficit_alerts(unit_id: str):
    return list_water_deficit_alerts(unit_id)
