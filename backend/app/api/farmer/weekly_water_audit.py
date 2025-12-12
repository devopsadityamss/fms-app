# backend/app/api/farmer/weekly_water_audit.py

from fastapi import APIRouter, Query
from typing import Optional
from app.services.farmer.weekly_water_audit_service import run_weekly_audit

router = APIRouter()

@router.get("/water/{unit_id}/weekly-audit")
def api_weekly_audit(unit_id: str, week_iso: Optional[str] = Query(None, description="YYYY-MM-DD or YYYY-WW"), events: int = Query(20)):
    """
    Returns a weekly audit report for the unit.
    - week_iso: optional date within week (YYYY-MM-DD) or ISO week (YYYY-WW). If omitted, current week is used.
    - events: number of recent audit events to include.
    """
    return run_weekly_audit(unit_id=unit_id, week_iso=week_iso, include_events_limit=events)
