# backend/app/api/farmer/timeline.py

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List

from app.services.farmer.timeline_service import (
    get_timeline_for_unit,
    get_timeline_for_farm
)

router = APIRouter()


@router.get("/timeline/unit/{unit_id}")
def api_timeline_unit(
    unit_id: str,
    start_iso: Optional[str] = Query(None, description="ISO start datetime filter"),
    end_iso: Optional[str] = Query(None, description="ISO end datetime filter"),
    types: Optional[str] = Query(None, description="Comma-separated kinds e.g. task,alert,irrigation,ledger,notification,recommendation"),
    limit: Optional[int] = Query(100, description="Max items to return"),
    cursor: Optional[str] = Query(None, description="Cursor ISO timestamp for pagination (returns items older than this)")
):
    types_list = [t.strip() for t in types.split(",")] if types else None
    res = get_timeline_for_unit(unit_id, start_iso=start_iso, end_iso=end_iso, types=types_list, limit=limit or 100, cursor=cursor)
    if res.get("status") == "unit_not_found":
        raise HTTPException(status_code=404, detail="unit_not_found")
    return res


@router.get("/timeline/farm")
def api_timeline_farm(
    start_iso: Optional[str] = Query(None),
    end_iso: Optional[str] = Query(None),
    types: Optional[str] = Query(None),
    limit: Optional[int] = Query(200),
    cursor: Optional[str] = Query(None)
):
    types_list = [t.strip() for t in types.split(",")] if types else None
    res = get_timeline_for_farm(start_iso=start_iso, end_iso=end_iso, types=types_list, limit=limit or 200, cursor=cursor)
    return res
