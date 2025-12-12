"""
Water Logbook Service (stub-ready)
----------------------------------

Tracks all irrigation / watering events for a farmer’s production units.

Each log entry contains:
 - unit_id
 - method: drip | flood | sprinkler | manual | other
 - quantity_liters
 - start_time
 - end_time
 - water_source: borewell | canal | tank | rainwater | other
 - notes

Stored in-memory for now. Replace with DB models later.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid


_water_store: Dict[str, Dict[str, Any]] = {}


def _new_id() -> str:
    return str(uuid.uuid4())


def _now() -> str:
    return datetime.utcnow().isoformat()


# ---------------------------------------------------------------------
# Helper: compute duration (minutes)
# ---------------------------------------------------------------------
def _calc_duration_minutes(start: Optional[str], end: Optional[str]) -> Optional[int]:
    try:
        if not start or not end:
            return None
        s = datetime.fromisoformat(start)
        e = datetime.fromisoformat(end)
        delta = e - s
        return int(delta.total_seconds() // 60)
    except Exception:
        return None


# ---------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------
def create_water_log(payload: Dict[str, Any]) -> Dict[str, Any]:
    log_id = _new_id()

    record = {
        "id": log_id,
        "unit_id": payload.get("unit_id"),
        "method": payload.get("method", "other"),
        "quantity_liters": float(payload.get("quantity_liters", 0)),
        "start_time": payload.get("start_time"),
        "end_time": payload.get("end_time"),
        "water_source": payload.get("water_source", "other"),
        "notes": payload.get("notes"),
        "created_at": _now(),
        "updated_at": _now(),
    }

    duration = _calc_duration_minutes(record["start_time"], record["end_time"])
    record["duration_minutes"] = duration

    _water_store[log_id] = record
    return record


def get_water_log(log_id: str) -> Optional[Dict[str, Any]]:
    return _water_store.get(log_id)


def update_water_log(log_id: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    rec = _water_store.get(log_id)
    if not rec:
        return None

    for key in ("unit_id", "method", "quantity_liters", "start_time", "end_time", "water_source", "notes"):
        if key in payload:
            rec[key] = payload[key]

    rec["updated_at"] = _now()
    rec["duration_minutes"] = _calc_duration_minutes(rec.get("start_time"), rec.get("end_time"))

    _water_store[log_id] = rec
    return rec


def delete_water_log(log_id: str) -> bool:
    if log_id in _water_store:
        del _water_store[log_id]
        return True
    return False


# ---------------------------------------------------------------------
# Listing & Filtering
# ---------------------------------------------------------------------
def list_water_logs(
    unit_id: Optional[str] = None,
    method: Optional[str] = None,
    water_source: Optional[str] = None
) -> Dict[str, Any]:

    items = list(_water_store.values())

    if unit_id:
        items = [i for i in items if i.get("unit_id") == unit_id]

    if method:
        items = [i for i in items if i.get("method") == method]

    if water_source:
        items = [i for i in items if i.get("water_source") == water_source]

    return {"count": len(items), "items": items}


# ---------------------------------------------------------------------
# Analytics Stub
# ---------------------------------------------------------------------
def total_water_usage(unit_id: Optional[str] = None) -> Dict[str, Any]:
    items = list(_water_store.values())
    if unit_id:
        items = [i for i in items if i.get("unit_id") == unit_id]

    total_qty = sum(i.get("quantity_liters", 0) for i in items)
    total_time = sum(i.get("duration_minutes", 0) or 0 for i in items)

    return {
        "unit_id": unit_id,
        "total_liters": round(total_qty, 2),
        "total_minutes": total_time,
        "session_count": len(items),
    }


def _clear_store():
    _water_store.clear()
