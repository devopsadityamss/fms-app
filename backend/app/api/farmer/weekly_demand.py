# backend/app/api/farmer/weekly_demand.py

from fastapi import APIRouter, Query
from typing import Optional
from app.services.farmer.weekly_demand_service import weekly_aggregated_demand

router = APIRouter()

@router.get("/water/{unit_id}/weekly-demand")
def api_weekly_demand(unit_id: str, weeks: int = Query(12, ge=1, le=52), start_date_iso: Optional[str] = Query(None)):
    """
    Returns weekly aggregated predicted vs actual water demand for `weeks` past weeks.
    Query params:
      - weeks (int): number of weeks to return (default 12)
      - start_date_iso (YYYY-MM-DD): end-date for the window (optional)
    """
    return weekly_aggregated_demand(unit_id=unit_id, weeks=weeks, start_date_iso=start_date_iso)
