"""
API Routes — Worker Attendance
------------------------------

Endpoints:
 - POST   /farmer/attendance
 - GET    /farmer/attendance/{attendance_id}
 - PUT    /farmer/attendance/{attendance_id}
 - DELETE /farmer/attendance/{attendance_id}
 - GET    /farmer/attendance
 - GET    /farmer/attendance/summary/worker/{worker_id}
 - GET    /farmer/attendance/summary/unit/{unit_id}
"""

from fastapi import APIRouter, HTTPException, Body, Query
from typing import Dict, Any, Optional

from app.services.farmer import worker_attendance_service as svc

router = APIRouter()


@router.post("/farmer/attendance")
async def api_record_attendance(payload: Dict[str, Any] = Body(...)):
    required = ["worker_id", "date", "status"]
    for r in required:
        if r not in payload:
            raise HTTPException(status_code=400, detail=f"{r} is required")

    return svc.record_attendance(
        worker_id=payload["worker_id"],
        attendance_date=payload["date"],
        status=payload["status"],
        hours=payload.get("hours", 0),
        unit_id=payload.get("unit_id"),
        tasks=payload.get("tasks"),
        notes=payload.get("notes")
    )


@router.get("/farmer/attendance/{attendance_id}")
def api_get_attendance(attendance_id: str):
    rec = svc.get_attendance(attendance_id)
    if not rec:
        raise HTTPException(status_code=404, detail="attendance_not_found")
    return rec


@router.put("/farmer/attendance/{attendance_id}")
async def api_update_attendance(attendance_id: str, payload: Dict[str, Any] = Body(...)):
    rec = svc.update_attendance(attendance_id, payload)
    if not rec:
        raise HTTPException(status_code=404, detail="attendance_not_found")
    return rec


@router.delete("/farmer/attendance/{attendance_id}")
def api_delete_attendance(attendance_id: str):
    ok = svc.delete_attendance(attendance_id)
    if not ok:
        raise HTTPException(status_code=404, detail="attendance_not_found")
    return {"success": True}


@router.get("/farmer/attendance")
def api_list_attendance(
    worker_id: Optional[str] = Query(None),
    unit_id: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None)
):
    return svc.list_attendance(worker_id=worker_id, unit_id=unit_id, date_from=date_from, date_to=date_to)


@router.get("/farmer/attendance/summary/worker/{worker_id}")
def api_worker_summary(
    worker_id: str,
    month: int = Query(...),
    year: int = Query(...)
):
    return svc.monthly_summary(worker_id, month, year)


@router.get("/farmer/attendance/summary/unit/{unit_id}")
def api_unit_summary(
    unit_id: str,
    month: Optional[int] = Query(None),
    year: Optional[int] = Query(None)
):
    return svc.unit_summary(unit_id, month, year)
