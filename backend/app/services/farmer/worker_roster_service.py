"""
Worker Roster Service (stub-ready)
----------------------------------

Purpose:
 - Manage shift assignments for workers tied to production units
 - Basic conflict detection (same worker double-booked same time)
 - Query roster by unit / worker / date-range
 - CRUD operations and a helper to generate simple daily schedule views

Notes:
 - In-memory store for now. Replace with DB + calendar service later.
 - Times are ISO datetimes (strings). Basic validation only.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import uuid

_roster_store: Dict[str, Dict[str, Any]] = {}  # roster_id -> record

def _now_iso() -> str:
    return datetime.utcnow().isoformat()

def _new_id() -> str:
    return str(uuid.uuid4())


# -------------------------
# Core CRUD
# -------------------------
def create_roster_entry(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Expected payload keys:
      - unit_id: optional (production unit)
      - worker_id: required
      - shift_start: ISO datetime string
      - shift_end: ISO datetime string
      - role: optional (harvester, pruner, sprayer, etc.)
      - notes: optional
    """
    entry_id = _new_id()
    entry = {
        "id": entry_id,
        "unit_id": payload.get("unit_id"),
        "worker_id": payload.get("worker_id"),
        "shift_start": payload.get("shift_start"),
        "shift_end": payload.get("shift_end"),
        "role": payload.get("role"),
        "notes": payload.get("notes"),
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    _roster_store[entry_id] = entry
    return entry

def get_roster_entry(entry_id: str) -> Optional[Dict[str, Any]]:
    return _roster_store.get(entry_id)

def update_roster_entry(entry_id: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    rec = _roster_store.get(entry_id)
    if not rec:
        return None
    for k in ("unit_id", "worker_id", "shift_start", "shift_end", "role", "notes"):
        if k in payload:
            rec[k] = payload[k]
    rec["updated_at"] = _now_iso()
    _roster_store[entry_id] = rec
    return rec

def delete_roster_entry(entry_id: str) -> bool:
    if entry_id in _roster_store:
        del _roster_store[entry_id]
        return True
    return False


# -------------------------
# Listing / querying
# -------------------------
def _parse_iso(dt: Optional[str]) -> Optional[datetime]:
    if not dt:
        return None
    try:
        return datetime.fromisoformat(dt)
    except Exception:
        return None

def list_roster_entries(
    unit_id: Optional[str] = None,
    worker_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
) -> Dict[str, Any]:
    items = list(_roster_store.values())
    if unit_id:
        items = [i for i in items if i.get("unit_id") == unit_id]
    if worker_id:
        items = [i for i in items if i.get("worker_id") == worker_id]

    start = _parse_iso(date_from)
    end = _parse_iso(date_to)
    if start or end:
        filtered = []
        for i in items:
            s = _parse_iso(i.get("shift_start"))
            e = _parse_iso(i.get("shift_end"))
            if not s or not e:
                continue
            # include if overlap with range
            if start and e < start:
                continue
            if end and s > end:
                continue
            filtered.append(i)
        items = filtered

    return {"count": len(items), "items": items}


# -------------------------
# Domain helpers
# -------------------------
def check_conflicts_for_worker(worker_id: str, shift_start: str, shift_end: str) -> List[Dict[str, Any]]:
    """
    Return list of existing roster entries that overlap the given shift for the worker.
    """
    s = _parse_iso(shift_start)
    e = _parse_iso(shift_end)
    if not s or not e:
        return []

    conflicts = []
    for rec in _roster_store.values():
        if rec.get("worker_id") != worker_id:
            continue
        rs = _parse_iso(rec.get("shift_start"))
        re_ = _parse_iso(rec.get("shift_end"))
        if not rs or not re_:
            continue
        # overlap check
        if not (e <= rs or s >= re_):
            conflicts.append(rec)
    return conflicts

def roster_for_day(unit_id: Optional[str], day_iso: str) -> Dict[str, Any]:
    """
    Return a simple daily view grouped by worker for a given ISO date (YYYY-MM-DD or datetime).
    """
    try:
        day = datetime.fromisoformat(day_iso).date()
    except Exception:
        # try date-only
        day = datetime.fromisoformat(day_iso + "T00:00:00").date() if day_iso else None

    if not day:
        return {"date": day_iso, "workers": {}, "count": 0}

    items = [i for i in _roster_store.values() if (not unit_id or i.get("unit_id") == unit_id)]
    workers = {}
    for rec in items:
        s = _parse_iso(rec.get("shift_start"))
        if not s:
            continue
        if s.date() == day:
            wid = rec.get("worker_id")
            workers.setdefault(wid, []).append(rec)
    return {"date": day.isoformat(), "workers": workers, "count": sum(len(v) for v in workers.values())}


# -------------------------
# Test helper
# -------------------------
def _clear_store():
    _roster_store.clear()
