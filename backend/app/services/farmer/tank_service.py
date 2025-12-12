# backend/app/services/farmer/tank_service.py

"""
Water Tank Level Tracking Service (Feature 316)

- Register tanks (rectangular or cylindrical)
- Record level readings (height_m or percent)
- Estimate volume (liters) from geometry + reading
- Provide latest level, history, and simple low-level alerts
- Best-effort integration with pump_service to estimate refill time
"""

from datetime import datetime
from threading import Lock
from typing import Dict, Any, List, Optional
import uuid
import math

# best-effort integration
try:
    from app.services.farmer.pump_service import compute_efficiency_metrics
except Exception:
    compute_efficiency_metrics = None

_lock = Lock()

_tanks: Dict[str, Dict[str, Any]] = {}           # tank_id -> tank record
_tanks_by_farmer: Dict[str, List[str]] = {}      # farmer_id -> [tank_id]
_level_readings: Dict[str, List[Dict[str, Any]]] = {}  # tank_id -> [reading]

DEFAULT_LOW_LEVEL_PCT = 20.0  # warn if below this percent
DEFAULT_HIGH_LEVEL_PCT = 95.0

def _now_iso() -> str:
    return datetime.utcnow().isoformat()


def _uid(prefix: str = "tank") -> str:
    return f"{prefix}_{uuid.uuid4()}"


# -------------------------------------------------------------------
# Tank registry
# geometry:
#  - shape: "cylinder" or "rectangular"
#  - for cylinder: { "diameter_m": .., "height_m": .. }
#  - for rectangular: { "length_m": .., "width_m": .., "height_m": .. }
# optional: capacity_liters to override geometry-based capacity
# -------------------------------------------------------------------
def add_tank(
    farmer_id: str,
    name: str,
    shape: str,
    geometry: Dict[str, float],
    capacity_liters: Optional[float] = None,
    warning_level_pct: Optional[float] = None,
    critical_level_pct: Optional[float] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    tid = _uid("tank")
    rec = {
        "tank_id": tid,
        "farmer_id": farmer_id,
        "name": name,
        "shape": shape.lower(),
        "geometry": geometry.copy(),
        "capacity_liters": float(capacity_liters) if capacity_liters is not None else None,
        "warning_level_pct": float(warning_level_pct) if warning_level_pct is not None else DEFAULT_LOW_LEVEL_PCT,
        "critical_level_pct": float(critical_level_pct) if critical_level_pct is not None else 5.0,
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
        rec = _tanks.get(tank_id)
        return rec.copy() if rec else {}


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
            _tanks_by_farmer[farmer_id] = [i for i in _tanks_by_farmer[farmer_id] if i != tank_id]
        _level_readings.pop(tank_id, None)
        return {"status": "deleted", "tank_id": tank_id}


# -------------------------------------------------------------------
# Geometry helpers
# -------------------------------------------------------------------
def _geometry_capacity_liters(shape: str, geometry: Dict[str, Any]) -> Optional[float]:
    try:
        if shape == "cylinder":
            d = float(geometry.get("diameter_m"))
            h = float(geometry.get("height_m"))
            r = d / 2.0
            vol_m3 = math.pi * (r ** 2) * h
            return vol_m3 * 1000.0
        elif shape == "rectangular" or shape == "box":
            l = float(geometry.get("length_m"))
            w = float(geometry.get("width_m"))
            h = float(geometry.get("height_m"))
            vol_m3 = l * w * h
            return vol_m3 * 1000.0
        else:
            # unknown shape: try simple height*area if provided
            area = geometry.get("area_m2")
            h = geometry.get("height_m") or geometry.get("max_height_m")
            if area and h:
                return float(area) * float(h) * 1000.0
    except Exception:
        pass
    return None


def estimate_capacity_liters(tank_id: str) -> Optional[float]:
    t = get_tank(tank_id)
    if not t:
        return None
    if t.get("capacity_liters"):
        return float(t.get("capacity_liters"))
    return _geometry_capacity_liters(t.get("shape"), t.get("geometry", {}))


# -------------------------------------------------------------------
# Level readings
# - reading can provide either height_m (meters) or percent (0-100)
# - if height_m provided, percent computed using tank height from geometry
# -------------------------------------------------------------------
def record_level_reading(
    tank_id: str,
    timestamp_iso: Optional[str] = None,
    height_m: Optional[float] = None,
    percent: Optional[float] = None,
    note: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    with _lock:
        tank = _tanks.get(tank_id)
        if not tank:
            return {"error": "tank_not_found"}

    ts = timestamp_iso or _now_iso()
    # compute percent if height provided
    computed_percent = None
    try:
        if height_m is not None:
            # determine max height from geometry or capacity
            geom_h = None
            if tank.get("shape") == "cylinder" or tank.get("shape") in ("rectangular", "box"):
                geom_h = tank.get("geometry", {}).get("height_m")
            if geom_h is not None and geom_h > 0:
                computed_percent = max(0.0, min(100.0, (float(height_m) / float(geom_h)) * 100.0))
            else:
                # if capacity known and volume-height mapping not available, leave percent None
                computed_percent = None
        elif percent is not None:
            computed_percent = max(0.0, min(100.0, float(percent)))
    except Exception:
        computed_percent = None

    rec = {
        "reading_id": f"tlr_{uuid.uuid4()}",
        "tank_id": tank_id,
        "timestamp": ts,
        "height_m": float(height_m) if height_m is not None else None,
        "percent": float(percent) if percent is not None else computed_percent,
        "note": note or "",
        "metadata": metadata or {}
    }
    with _lock:
        _level_readings.setdefault(tank_id, []).append(rec)
    return rec


def list_level_readings(tank_id: str, limit: int = 200) -> List[Dict[str, Any]]:
    with _lock:
        items = list(_level_readings.get(tank_id, []))
    items_sorted = sorted(items, key=lambda r: r.get("timestamp", ""), reverse=True)[:limit]
    return items_sorted


def get_latest_reading(tank_id: str) -> Optional[Dict[str, Any]]:
    readings = list_level_readings(tank_id, limit=1)
    return readings[0] if readings else None


# -------------------------------------------------------------------
# Estimate volume from latest reading
# -------------------------------------------------------------------
def estimate_volume_from_reading(tank_id: str, reading: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    tank = get_tank(tank_id)
    if not tank:
        return {"error": "tank_not_found"}
    capacity = estimate_capacity_liters(tank_id)
    if capacity is None:
        return {"error": "capacity_unknown"}

    if reading is None:
        reading = get_latest_reading(tank_id)
    if not reading:
        return {"error": "no_readings"}

    # prefer percent if available
    pct = reading.get("percent")
    height_m = reading.get("height_m")
    # if percent missing but height present and geometry height known, compute percent
    if pct is None and height_m is not None:
        geom_h = tank.get("geometry", {}).get("height_m")
        if geom_h:
            try:
                pct = max(0.0, min(100.0, (float(height_m) / float(geom_h)) * 100.0))
            except Exception:
                pct = None

    if pct is None:
        # fallback: cannot compute
        return {"error": "insufficient_reading_for_volume", "reading": reading}

    available_liters = round((float(pct) / 100.0) * float(capacity), 2)
    return {
        "tank_id": tank_id,
        "capacity_liters": round(float(capacity), 2),
        "reading": reading,
        "percent": round(float(pct), 2),
        "available_liters": available_liters,
        "generated_at": _now_iso()
    }


# -------------------------------------------------------------------
# Low-level alerts & overview
# -------------------------------------------------------------------
def check_low_level_alert(tank_id: str) -> Optional[Dict[str, Any]]:
    tank = get_tank(tank_id)
    if not tank:
        return None
    latest = get_latest_reading(tank_id)
    if not latest:
        return None
    info = estimate_volume_from_reading(tank_id, latest)
    if info.get("error"):
        return None
    pct = info.get("percent", 100.0)
    warn_pct = tank.get("warning_level_pct", DEFAULT_LOW_LEVEL_PCT)
    critical_pct = tank.get("critical_level_pct", 5.0)
    severity = None
    if pct <= critical_pct:
        severity = "critical"
    elif pct <= warn_pct:
        severity = "warning"

    if severity:
        return {
            "tank_id": tank_id,
            "severity": severity,
            "percent": pct,
            "available_liters": info.get("available_liters"),
            "message": f"Tank '{tank.get('name')}' level {pct}% ({info.get('available_liters')} L) - {severity.upper()}",
            "generated_at": _now_iso()
        }
    return None


def tank_overview(farmer_id: str) -> Dict[str, Any]:
    tanks = list_tanks(farmer_id)
    out = []
    for t in tanks:
        latest = get_latest_reading(t["tank_id"])
        vol_info = None
        try:
            vol_info = estimate_volume_from_reading(t["tank_id"], latest)
        except Exception:
            vol_info = {"error": "could_not_compute_volume"}
        alert = check_low_level_alert(t["tank_id"])
        out.append({
            "tank": t,
            "latest_reading": latest,
            "volume_info": vol_info,
            "alert": alert
        })
    return {"farmer_id": farmer_id, "count": len(out), "tanks": out, "generated_at": _now_iso()}


# -------------------------------------------------------------------
# Refill estimator (best-effort)
# Given a pump_id and target liters, estimate hours using pump observed L/kWh or L/hr if available.
# If pump_service present, try to use pump's avg_flow_lph (if recorded in usage) or fallback to user supplied pump_rate_lph
# -------------------------------------------------------------------
def estimate_refill_time(tank_id: str, target_liters: float, pump_id: Optional[str] = None, pump_rate_lph: Optional[float] = None) -> Dict[str, Any]:
    rate_lph = None
    if pump_id and compute_efficiency_metrics:
        try:
            metrics = compute_efficiency_metrics(pump_id)
            # compute avg_flow_lph from metrics if present
            rate_lph = metrics.get("avg_flow_lph")
        except Exception:
            rate_lph = None

    if not rate_lph and pump_rate_lph:
        rate_lph = float(pump_rate_lph)

    if not rate_lph or rate_lph <= 0:
        return {"error": "no_pump_rate_available"}

    hours = float(target_liters) / float(rate_lph)
    return {"tank_id": tank_id, "target_liters": target_liters, "estimated_hours": round(hours, 3), "pump_rate_lph": rate_lph}


