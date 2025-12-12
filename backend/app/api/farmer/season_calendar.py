# backend/app/api/farmer/season_calendar.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.services.farmer.season_calendar_service import (
    generate_season_calendar_for_unit,
    get_calendar_for_unit,
    export_calendar_csv,
    list_all_calendars,
    regenerate_calendar
)

router = APIRouter()


class CalendarGenerateRequest(BaseModel):
    season_start_date_iso: Optional[str] = None
    use_working_days_per_week: Optional[int] = None
    skip_rainy_windows: Optional[List[Dict[str, str]]] = None
    stage_gap_days: Optional[int] = None


@router.post("/calendar/generate/{unit_id}")
def api_generate_calendar(unit_id: str, req: CalendarGenerateRequest):
    cal = generate_season_calendar_for_unit(
        unit_id,
        season_start_date_iso=req.season_start_date_iso,
        use_working_days_per_week=(req.use_working_days_per_week or 6),
        skip_rainy_windows=req.skip_rainy_windows,
        stage_gap_days=(req.stage_gap_days or 2)
    )
    if not cal:
        raise HTTPException(status_code=404, detail="unit_not_found")
    return cal


@router.get("/calendar/{unit_id}")
def api_get_calendar(unit_id: str):
    cal = get_calendar_for_unit(unit_id)
    if not cal:
        raise HTTPException(status_code=404, detail="calendar_not_found")
    return cal


@router.get("/calendar")
def api_list_calendars():
    return list_all_calendars()


@router.get("/calendar/{unit_id}/export")
def api_export_calendar_csv(unit_id: str):
    csv_str = export_calendar_csv(unit_id)
    if csv_str is None:
        raise HTTPException(status_code=404, detail="calendar_not_found")
    # return CSV string as plain text; frontend can save as file
    return {"unit_id": unit_id, "csv": csv_str}


@router.post("/calendar/regenerate/{unit_id}")
def api_regenerate_calendar(unit_id: str, req: CalendarGenerateRequest):
    cal = regenerate_calendar(
        unit_id,
        season_start_date_iso=req.season_start_date_iso,
        use_working_days_per_week=(req.use_working_days_per_week or 6),
        skip_rainy_windows=req.skip_rainy_windows,
        stage_gap_days=(req.stage_gap_days or 2)
    )
    if not cal:
        raise HTTPException(status_code=404, detail="unit_not_found")
    return cal
