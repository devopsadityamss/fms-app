"""
Activity & Operation Calendar Service (stub-ready)
-------------------------------------------------

Purpose:
 - Store calendar-friendly activities for a farmer's units.
 - Each event may represent:
     - operation (pruning, irrigation, spraying...)
     - advisory (fertilizer, protection, predictions...)
     - logbook entry (water, document, roster...)
     - system-generated alerts
 - Supports date range filtering
 - Outputs calendar-style records

Fields:
 - id
 - unit_id
 - title
 - event_type: operation | advisory | alert | logbook | misc
 - start_time (ISO)
 - end_time (ISO, optional)
 - meta (dict)
 - notes
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid


_calendar_store: Dict[str, Dict[str, Any]] = {}


def _new_id() -> str:
    return str(uuid.uuid4())


def _now() -> str:
    return datetime.utcnow().isoformat()


# Convert string → datetime safely
def _parse_iso(dt: Optional[str]) -> Optional[datetime]:
    if not dt:
        return None
    try:
        return datetime.fromisoformat(dt)
    except Exception:
        return None


# ---------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------
def create_event(payload: Dict[str, Any]) -> Dict[str, Any]:
    event_id = _new_id()

    record = {
        "id": event_id,
        "unit_id": payload.get("unit_id"),
        "title": payload.get("title"),
        "event_type": payload.get("event_type", "misc"),
        "start_time": payload.get("start_time"),  # ISO string
        "end_time": payload.get("end_time"),
        "notes": payload.get("notes"),
        "meta": payload.get("meta", {}),
        "created_at": _now(),
        "updated_at": _now()
    }

    _calendar_store[event_id] = record
    return record


def get_event(event_id: str) -> Optional[Dict[str, Any]]:
    return _calendar_store.get(event_id)


def update_event(event_id: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    rec = _calendar_store.get(event_id)
    if not rec:
        return None

    for key in ("title", "unit_id", "event_type", "start_time", "end_time", "notes", "meta"):
        if key in payload:
            rec[key] = payload[key]

    rec["updated_at"] = _now()
    _calendar_store[event_id] = rec
    return rec


def delete_event(event_id: str) -> bool:
    if event_id in _calendar_store:
        del _calendar_store[event_id]
        return True
    return False


# ---------------------------------------------------------------------
# Calendar Listing / Filters
# ---------------------------------------------------------------------
def list_events(
    unit_id: Optional[str] = None,
    event_type: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
) -> Dict[str, Any]:

    items = list(_calendar_store.values())

    if unit_id:
        items = [i for i in items if i.get("unit_id") == unit_id]

    if event_type:
        items = [i for i in items if i.get("event_type") == event_type]

    start = _parse_iso(date_from)
    end = _parse_iso(date_to)

    if start or end:
        filtered = []
        for rec in items:
            s = _parse_iso(rec.get("start_time"))
            if not s:
                continue
            if start and s < start:
                continue
            if end and s > end:
                continue
            filtered.append(rec)
        items = filtered

    return {"count": len(items), "items": items}


# ---------------------------------------------------------------------
# Calendar Feed / Agenda Style
# ---------------------------------------------------------------------
def agenda_for_day(unit_id: Optional[str], day_iso: str) -> Dict[str, Any]:
    try:
        day = datetime.fromisoformat(day_iso).date()
    except Exception:
        return {"date": day_iso, "items": []}

    items = []
    for rec in _calendar_store.values():
        if unit_id and rec.get("unit_id") != unit_id:
            continue
        st = _parse_iso(rec.get("start_time"))
        if st and st.date() == day:
            items.append(rec)

    return {"date": day_iso, "items": items}


def _clear_store():
    _calendar_store.clear()
