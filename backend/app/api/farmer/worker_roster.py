"""
API Routes — Worker Roster (Farmer POV)

Endpoints:
 - POST   /farmer/roster               -> create roster entry
 - GET    /farmer/roster               -> list entries (filters)
 - GET    /farmer/roster/{entry_id}    -> get single entry
 - PUT    /farmer/roster/{entry_id}    -> update entry
 - DELETE /farmer/roster/{entry_id}    -> delete entry
 - POST   /farmer/roster/check_conflict -> check conflicts for a proposed shift
 - GET    /farmer/roster/day/{date_iso} -> roster for a specific day
"""

from fastapi import APIRouter, HTTPException, Query, Body
from typing import Optional, Dict, Any

from app.services.farmer import worker_roster_service as svc

router = APIRouter()

@router.post("/farmer/roster")
async def api_create_roster_entry(payload: Dict[str, Any] = Body(...)):
    # optional: basic validation
    if not payload.get("worker_id") or not payload.get("shift_start") or not payload.get("shift_end"):
        raise HTTPException(status_code=400, detail="worker_id_and_shift_times_required")
    # check conflicts
    conflicts = svc.check_conflicts_for_worker(payload.get("worker_id"), payload.get("shift_start"), payload.get("shift_end"))
    if conflicts:
        return {"warning": "conflicts_detected", "conflicts": conflicts}
    rec = svc.create_roster_entry(payload)
    return rec

@router.get("/farmer/roster")
def api_list_roster_entries(
    unit_id: Optional[str] = Query(None),
    worker_id: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None)
):
    return svc.list_roster_entries(unit_id=unit_id, worker_id=worker_id, date_from=date_from, date_to=date_to)

@router.get("/farmer/roster/{entry_id}")
def api_get_roster_entry(entry_id: str):
    rec = svc.get_roster_entry(entry_id)
    if not rec:
        raise HTTPException(status_code=404, detail="roster_entry_not_found")
    return rec

@router.put("/farmer/roster/{entry_id}")
async def api_update_roster_entry(entry_id: str, payload: Dict[str, Any] = Body(...)):
    rec = svc.update_roster_entry(entry_id, payload)
    if not rec:
        raise HTTPException(status_code=404, detail="roster_entry_not_found")
    return rec

@router.delete("/farmer/roster/{entry_id}")
def api_delete_roster_entry(entry_id: str):
    ok = svc.delete_roster_entry(entry_id)
    if not ok:
        raise HTTPException(status_code=404, detail="roster_entry_not_found")
    return {"success": True}

@router.post("/farmer/roster/check_conflict")
async def api_check_conflict(payload: Dict[str, Any] = Body(...)):
    """
    payload: { worker_id, shift_start, shift_end }
    returns list of conflicting entries (if any)
    """
    worker_id = payload.get("worker_id")
    shift_start = payload.get("shift_start")
    shift_end = payload.get("shift_end")
    if not worker_id or not shift_start or not shift_end:
        raise HTTPException(status_code=400, detail="worker_id_and_shift_times_required")
    conflicts = svc.check_conflicts_for_worker(worker_id, shift_start, shift_end)
    return {"conflicts": conflicts}

@router.get("/farmer/roster/day/{date_iso}")
def api_roster_for_day(date_iso: str, unit_id: Optional[str] = Query(None)):
    return svc.roster_for_day(unit_id=unit_id, day_iso=date_iso)
