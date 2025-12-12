# backend/app/services/farmer/water_service.py

"""
Water Service — Feature: Water Tank Level Tracking

Provides:
 - Tank CRUD (add/get/list/update/delete)
 - Sensor reading ingestion (level percent or level_mm)
 - Level estimation (latest reading, smoothing)
 - Consumption estimate over a time window (based on successive readings)
 - Low-level alerts (threshold-based) via notification_service.immediate_send if present

Design notes:
 - In-memory stores with thread locking (consistent with other services)
 - Records keep created_at timestamps
 - Readings are stored per-tank; the service exposes simple analytics useful for UI
 - Later: replace in-memory with DB models and add sensor adapters
"""

from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, Any, List, Optional
import uuid
import statistics

# best-effort integration with notification service
try:
    from app.services.farmer.notification_service import immediate_send
except Exception:
    immediate_send = None

_lock = Lock()

# stores
_tanks: Dict[str, Dict[str, Any]] = {}            # tank_id -> tank record
_tanks_by_farmer: Dict[str, List[str]] = {}       # farmer_id -> [tank_ids]
_readings: Dict[str, List[Dict[str, Any]]] = {}   # tank_id -> list of readings (ordered by time)

# defaults
LOW_LEVEL_THRESHOLD_PCT = 20.0  # percent below which we alert
SMOOTHING_WINDOW = 3            # number of latest readings to average for smoothing

def _now_iso() -> str:
    return datetime.utcnow().isoformat()

def _uid(prefix: str = "wt") -> str:
    return f"{prefix}_{uuid.uuid4()}"

# -------------------------
# Tank CRUD / registration
# -------------------------
def add_tank(
    farmer_id: str,
    name: str,
    capacity_liters: float,
    location: Optional[str] = None,
    tank_type: Optional[str] = None,  # e.g., "underground", "overhead", "borewell-tank"
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    tid = _uid("tank")
    rec = {
        "tank_id": tid,
        "farmer_id": farmer_id,
        "name": name,
        "capacity_liters": float(capacity_liters),
        "location": location or "",
        "tank_type": tank_type or "generic",
        "metadata": metadata or {},
        "created_at": _now_iso(),
        "updated_at": None
    }
    with _lock:
        _tanks[tid] = rec
        _tanks_by_farmer.setdefault(farmer_id, []).append(tid)
    return rec

def get_tank(tank_id: str) -> Dict[str, Any]:
    with _lock:
        return _tanks.get(tank_id, {}).copy()

def list_tanks(farmer_id: str) -> List[Dict[str, Any]]:
    with _lock:
        ids = _tanks_by_farmer.get(farmer_id, [])
        return [ _tanks[i].copy() for i in ids ]

def update_tank(tank_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    with _lock:
        rec = _tanks.get(tank_id)
        if not rec:
            return {"error": "not_found"}
        rec.update(updates)
        rec["updated_at"] = _now_iso()
        _tanks[tank_id] = rec
        return rec.copy()

def delete_tank(tank_id: str) -> Dict[str, Any]:
    with _lock:
        rec = _tanks.pop(tank_id, None)
        if not rec:
            return {"error": "not_found"}
        farmer_id = rec.get("farmer_id")
        if farmer_id and farmer_id in _tanks_by_farmer:
            _tanks_by_farmer[farmer_id] = [tid for tid in _tanks_by_farmer[farmer_id] if tid != tank_id]
        _readings.pop(tank_id, None)
    return {"status": "deleted", "tank_id": tank_id}

# -------------------------
# Sensor readings ingestion
# -------------------------
def record_reading(
    tank_id: str,
    timestamp_iso: Optional[str] = None,
    level_pct: Optional[float] = None,
    level_mm: Optional[float] = None,
    note: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Record a sensor reading for a tank. Prefer level_pct (0..100). level_mm accepted if caller converts.
    Will attempt to compute both percent and mm if capacity known.
    """
    with _lock:
        if tank_id not in _tanks:
            return {"error": "tank_not_found"}

    ts = None
    if timestamp_iso:
        try:
            ts = datetime.fromisoformat(timestamp_iso)
        except Exception:
            ts = datetime.utcnow()
    else:
        ts = datetime.utcnow()

    # compute percent if only mm is provided and capacity is known
    pct = None
    mm = None
    with _lock:
        capacity = _tanks[tank_id].get("capacity_liters") or 0.0

    if level_pct is not None:
        try:
            pct = max(0.0, min(100.0, float(level_pct)))
        except Exception:
            pct = None

    if level_mm is not None:
        try:
            mm = float(level_mm)
        except Exception:
            mm = None

    # If we have mm and capacity, convert heuristically to percent using metadata.height_mm if present
    if pct is None and mm is not None:
        # if tank metadata contains 'height_mm' or 'max_depth_mm', use it
        with _lock:
            tank_meta = _tanks[tank_id].get("metadata", {}) or {}
        height_mm = tank_meta.get("height_mm") or tank_meta.get("max_depth_mm")
        if height_mm:
            try:
                pct = max(0.0, min(100.0, (mm / float(height_mm)) * 100.0))
            except Exception:
                pct = None

    # If we have percent but want mm and height exists, calculate mm
    if mm is None and pct is not None:
        with _lock:
            tank_meta = _tanks[tank_id].get("metadata", {}) or {}
        height_mm = tank_meta.get("height_mm") or tank_meta.get("max_depth_mm")
        if height_mm:
            try:
                mm = (float(pct) / 100.0) * float(height_mm)
            except Exception:
                mm = None

    rec = {
        "reading_id": _uid("r"),
        "tank_id": tank_id,
        "timestamp": ts.isoformat(),
        "level_pct": round(pct, 2) if pct is not None else None,
        "level_mm": round(mm, 2) if mm is not None else None,
        "note": note or "",
        "metadata": metadata or {}
    }

    with _lock:
        _readings.setdefault(tank_id, []).append(rec)

    # check low-level alert
    try:
        if pct is not None and pct <= LOW_LEVEL_THRESHOLD_PCT:
            _maybe_alert_low_level(tank_id, pct)
    except Exception:
        pass

    return rec

def get_readings(tank_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    with _lock:
        items = list(_readings.get(tank_id, []))
    # most recent last, but present newest first
    items_sorted = sorted(items, key=lambda x: x.get("timestamp",""), reverse=True)[:limit]
    return items_sorted

# -------------------------
# Estimation & analytics
# -------------------------
def estimate_current_level(tank_id: str) -> Dict[str, Any]:
    """
    Estimate current percent level using last N readings (smoothing).
    Returns: { tank_id, estimated_pct, estimated_mm, latest_timestamp, status }
    """
    with _lock:
        tank = _tanks.get(tank_id)
        if not tank:
            return {"error": "tank_not_found"}

        readings = list(_readings.get(tank_id, []))

    if not readings:
        return {"tank_id": tank_id, "estimated_pct": None, "estimated_mm": None, "latest_timestamp": None, "status": "unknown"}

    # take the last SMOOTHING_WINDOW readings (by timestamp)
    sorted_readings = sorted(readings, key=lambda r: r.get("timestamp",""), reverse=True)
    recent = sorted_readings[:SMOOTHING_WINDOW]

    pct_vals = [r.get("level_pct") for r in recent if r.get("level_pct") is not None]
    mm_vals = [r.get("level_mm") for r in recent if r.get("level_mm") is not None]

    est_pct = None
    est_mm = None
    if pct_vals:
        try:
            est_pct = round(statistics.mean(pct_vals), 2)
        except Exception:
            est_pct = pct_vals[0]
    if mm_vals:
        try:
            est_mm = round(statistics.mean(mm_vals), 2)
        except Exception:
            est_mm = mm_vals[0]

    latest_ts = recent[0].get("timestamp")
    status = "ok"
    if est_pct is not None and est_pct <= LOW_LEVEL_THRESHOLD_PCT:
        status = "low"

    return {
        "tank_id": tank_id,
        "estimated_pct": est_pct,
        "estimated_mm": est_mm,
        "latest_timestamp": latest_ts,
        "status": status
    }

def estimate_consumption(tank_id: str, since_iso: Optional[str] = None, until_iso: Optional[str] = None) -> Dict[str, Any]:
    """
    Rough consumption estimate based on level changes between time window.
    Returns liters consumed approximated by capacity * delta_pct/100.
    """
    with _lock:
        tank = _tanks.get(tank_id)
        if not tank:
            return {"error": "tank_not_found"}
        capacity = float(tank.get("capacity_liters", 0.0))
        readings = list(_readings.get(tank_id, []))

    if not readings:
        return {"tank_id": tank_id, "consumed_liters": 0.0, "notes": "no_readings"}

    # filter by time window if provided
    def _in_window(r):
        try:
            ts = datetime.fromisoformat(r.get("timestamp"))
        except Exception:
            return False
        if since_iso:
            try:
                since = datetime.fromisoformat(since_iso)
                if ts < since:
                    return False
            except Exception:
                pass
        if until_iso:
            try:
                until = datetime.fromisoformat(until_iso)
                if ts > until:
                    return False
            except Exception:
                pass
        return True

    window_readings = [r for r in readings if _in_window(r)]
    if len(window_readings) < 2:
        return {"tank_id": tank_id, "consumed_liters": 0.0, "notes": "insufficient_readings"}

    sorted_r = sorted(window_readings, key=lambda r: r.get("timestamp",""))
    start = sorted_r[0]
    end = sorted_r[-1]
    start_pct = start.get("level_pct")
    end_pct = end.get("level_pct")

    if start_pct is None or end_pct is None:
        # try mm -> pct using tank height
        # fallback: cannot estimate
        return {"tank_id": tank_id, "consumed_liters": 0.0, "notes": "missing_level_pct"}

    delta_pct = max(0.0, (start_pct - end_pct))
    consumed_liters = round((delta_pct / 100.0) * capacity, 2)
    interval_hours = None
    try:
        interval_hours = (datetime.fromisoformat(end.get("timestamp")) - datetime.fromisoformat(start.get("timestamp"))).total_seconds() / 3600.0
    except Exception:
        interval_hours = None

    return {"tank_id": tank_id, "consumed_liters": consumed_liters, "start_pct": start_pct, "end_pct": end_pct, "interval_hours": interval_hours}

# -------------------------
# Alerts & notifications
# -------------------------
def _maybe_alert_low_level(tank_id: str, pct: float):
    """
    Sends a low-level alert via notification_service.immediate_send (best-effort).
    Debounce: do not spam — only send once per low reading per tank (simple approach).
    """
    # store last alerted pct in tank metadata
    with _lock:
        tank = _tanks.get(tank_id)
        if not tank:
            return
        meta = tank.setdefault("metadata", {})
        last_alert = meta.get("_last_low_alert_pct")
        # alert only if new reading is lower than last alerted or no alert before
        if last_alert is not None and pct >= last_alert:
            return
        meta["_last_low_alert_pct"] = pct
        tank["metadata"] = meta
        _tanks[tank_id] = tank

    # attempt to notify
    try:
        farmer_id = tank.get("farmer_id")
        if immediate_send and farmer_id:
            title = f"Water tank '{tank.get('name')}' low: {pct}%"
            body = f"Estimated water level for tank '{tank.get('name')}' is {pct}%. Please refill or plan irrigation accordingly."
            immediate_send(str(farmer_id), title, body, channels=["in_app"])
    except Exception:
        pass

# -------------------------
# Utility / health
# -------------------------
def tank_status_overview(farmer_id: str) -> Dict[str, Any]:
    """
    For a farmer, provide a short summary of tanks and their estimated levels and statuses.
    """
    tanks = list_tanks(farmer_id)
    out = []
    for t in tanks:
        est = estimate_current_level(t.get("tank_id"))
        out.append({
            "tank": t,
            "estimated_level": est
        })
    return {"farmer_id": farmer_id, "count": len(out), "tanks": out, "generated_at": _now_iso()}
