# backend/app/services/farmer/water_audit_service.py

"""
Water Audit Log Service (Feature 314)

Tracks ALL water-related actions:
 - irrigation logs
 - soil moisture updates
 - weather updates
 - smart schedule events
 - water deficit alerts
 - manual overrides (placeholders)

Each audit entry:
 {
   "audit_id": "...",
   "unit_id": "...",
   "event_type": "irrigation|weather|moisture|schedule|deficit|manual",
   "payload": {...},
   "created_at": ISO
 }
"""

from datetime import datetime
from typing import Dict, Any, List
import uuid

# Internal in-memory audit store
_water_audit_store: Dict[str, List[Dict[str, Any]]] = {}   # unit_id -> [events]


def _now():
    return datetime.utcnow().isoformat()


def _make_audit(unit_id: str, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    rec = {
        "audit_id": str(uuid.uuid4()),
        "unit_id": unit_id,
        "event_type": event_type,
        "payload": payload,
        "created_at": _now()
    }
    _water_audit_store.setdefault(unit_id, []).append(rec)
    return rec


# ----------------------------------------------------------
# RECORDERS (called by other services)
# ----------------------------------------------------------

def record_irrigation_event(unit_id: str, log_record: Dict[str, Any]):
    """
    Called from irrigation_service.log_irrigation (we will update IR service later)
    """
    return _make_audit(unit_id, "irrigation", log_record)


def record_weather_event(unit_id: str, weather_record: Dict[str, Any]):
    """
    Called whenever weather is updated.
    """
    return _make_audit(unit_id, "weather", weather_record)


def record_moisture_event(unit_id: str, moisture_record: Dict[str, Any]):
    """
    Called whenever soil moisture is updated.
    """
    return _make_audit(unit_id, "moisture", moisture_record)


def record_schedule_event(unit_id: str, schedule_event: Dict[str, Any]):
    """
    Called by irrigation scheduler when new schedule events are computed.
    """
    return _make_audit(unit_id, "schedule", schedule_event)


def record_deficit_alert(unit_id: str, deficit_record: Dict[str, Any]):
    """
    Called by water_deficit_service daily or weekly.
    """
    return _make_audit(unit_id, "deficit", deficit_record)


def record_manual_override(unit_id: str, description: str, metadata: Dict[str, Any] = None):
    """
    Placeholder for future: manual changes in irrigation schedule.
    """
    payload = {"description": description, "metadata": metadata or {}}
    return _make_audit(unit_id, "manual", payload)


# ----------------------------------------------------------
# READERS
# ----------------------------------------------------------

def list_audit(unit_id: str, limit: int = 200) -> Dict[str, Any]:
    events = _water_audit_store.get(unit_id, [])
    events_sorted = sorted(events, key=lambda x: x["created_at"], reverse=True)
    return {
        "unit_id": unit_id,
        "count": len(events),
        "items": events_sorted[:limit]
    }


def list_audit_by_type(unit_id: str, event_type: str, limit: int = 200) -> Dict[str, Any]:
    events = [
        e for e in _water_audit_store.get(unit_id, [])
        if e["event_type"] == event_type
    ]
    events_sorted = sorted(events, key=lambda x: x["created_at"], reverse=True)
    return {
        "unit_id": unit_id,
        "event_type": event_type,
        "count": len(events),
        "items": events_sorted[:limit]
    }
