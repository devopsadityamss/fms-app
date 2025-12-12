"""
Worker Attendance Service (stub-ready)
--------------------------------------

Tracks daily attendance for workers:
 - Present / Absent / Half-day / Leave
 - Hours worked
 - Tasks performed
 - Unit reference (optional)
 - Notes

Provides:
 - CRUD for attendance
 - Monthly summaries
 - Worker-level summaries
 - Unit-level summaries
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, date
import uuid

# attendance_id => record
_attendance_store: Dict[str, Dict[str, Any]] = {}


def _now() -> str:
    return datetime.utcnow().isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


# -------------------------------------------------------------
# CREATE
# -------------------------------------------------------------
def record_attendance(
    worker_id: str,
    attendance_date: str,      # YYYY-MM-DD
    status: str,               # present | absent | half-day | leave
    hours: float = 0.0,
    unit_id: Optional[str] = None,
    tasks: Optional[List[str]] = None,
    notes: Optional[str] = None
) -> Dict[str, Any]:
    aid = _new_id()

    record = {
        "id": aid,
        "worker_id": worker_id,
        "date": attendance_date,
        "status": status,
        "hours": hours,
        "unit_id": unit_id,
        "tasks": tasks or [],
        "notes": notes,
        "created_at": _now(),
        "updated_at": _now()
    }

    _attendance_store[aid] = record
    return record


# -------------------------------------------------------------
# GET
# -------------------------------------------------------------
def get_attendance(attendance_id: str) -> Optional[Dict[str, Any]]:
    return _attendance_store.get(attendance_id)


# -------------------------------------------------------------
# UPDATE
# -------------------------------------------------------------
def update_attendance(attendance_id: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    rec = _attendance_store.get(attendance_id)
    if not rec:
        return None

    for key in ("status", "hours", "tasks", "notes", "unit_id", "date"):
        if key in payload:
            rec[key] = payload[key]

    rec["updated_at"] = _now()
    _attendance_store[attendance_id] = rec
    return rec


# -------------------------------------------------------------
# DELETE
# -------------------------------------------------------------
def delete_attendance(attendance_id: str) -> bool:
    if attendance_id in _attendance_store:
        del _attendance_store[attendance_id]
        return True
    return False


# -------------------------------------------------------------
# LIST & FILTER
# -------------------------------------------------------------
def list_attendance(
    worker_id: Optional[str] = None,
    unit_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
) -> Dict[str, Any]:

    items = list(_attendance_store.values())

    if worker_id:
        items = [i for i in items if i.get("worker_id") == worker_id]

    if unit_id:
        items = [i for i in items if i.get("unit_id") == unit_id]

    try:
        df = datetime.fromisoformat(date_from).date() if date_from else None
    except:
        df = None

    try:
        dt = datetime.fromisoformat(date_to).date() if date_to else None
    except:
        dt = None

    if df or dt:
        filtered = []
        for i in items:
            try:
                d = date.fromisoformat(i.get("date"))
            except:
                continue
            if df and d < df:
                continue
            if dt and d > dt:
                continue
            filtered.append(i)
        items = filtered

    return {"count": len(items), "items": items}


# -------------------------------------------------------------
# MONTHLY SUMMARY
# -------------------------------------------------------------
def monthly_summary(worker_id: str, month: int, year: int) -> Dict[str, Any]:
    items = list_attendance(worker_id=worker_id)["items"]

    p = a = h = l = 0
    total_hours = 0.0

    for rec in items:
        try:
            d = date.fromisoformat(rec["date"])
        except:
            continue

        if d.month != month or d.year != year:
            continue

        if rec["status"] == "present":
            p += 1
        elif rec["status"] == "absent":
            a += 1
        elif rec["status"] == "half-day":
            h += 1
        elif rec["status"] == "leave":
            l += 1

        total_hours += rec.get("hours", 0)

    return {
        "worker_id": worker_id,
        "month": month,
        "year": year,
        "days_present": p,
        "days_absent": a,
        "half_days": h,
        "leave_days": l,
        "total_hours": total_hours
    }


# -------------------------------------------------------------
# UNIT SUMMARY
# -------------------------------------------------------------
def unit_summary(unit_id: str, month: Optional[int] = None, year: Optional[int] = None) -> Dict[str, Any]:
    items = list_attendance(unit_id=unit_id)["items"]

    filtered = []
    if month and year:
        for rec in items:
            try:
                d = date.fromisoformat(rec["date"])
            except:
                continue
            if d.month == month and d.year == year:
                filtered.append(rec)
    else:
        filtered = items

    total_workers = len({x["worker_id"] for x in filtered})
    present_days = sum(1 for x in filtered if x["status"] == "present")

    return {
        "unit_id": unit_id,
        "attendance_records": len(filtered),
        "unique_workers": total_workers,
        "present_marks": present_days
    }


def _clear_store():
    _attendance_store.clear()
