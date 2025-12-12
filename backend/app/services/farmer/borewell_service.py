# backend/app/services/farmer/borewell_service.py

"""
Borewell Service — Feature 305: Borewell Recharge Estimator

Capabilities:
- Register / update / list borewells for a farmer.
- Record water-table / static water level readings for a borewell.
- Estimate recharge volume from rainfall using simple heuristics.
- Convert recharge volume to groundwater table rise using specific yield and aquifer area.
- Simulate multi-day recharge from a rainfall series (useful with forecast).
- Provide basic observed recharge rate estimation from recorded readings.

Notes:
- This is an engineering heuristic, not a full hydrogeological model.
- Key formulas:
    recharged_volume_l = (rainfall_mm / 1000) * recharge_area_m2 * recharge_coefficient
    water_table_rise_m = recharged_volume_m3 / (aquifer_area_m2 * specific_yield)
    where recharged_volume_m3 = recharged_volume_l / 1000
- Defaults:
    recharge_coefficient: 0.12 (12% of rainfall contributes to aquifer)
    specific_yield: 0.1 (typical unconfined aquifer)
"""

from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, Any, List, Optional
import uuid
import statistics

_lock = Lock()

_borewells: Dict[str, Dict[str, Any]] = {}       # well_id -> record
_borewells_by_farmer: Dict[str, List[str]] = {}  # farmer_id -> [well_ids]
_readings: Dict[str, List[Dict[str, Any]]] = {}  # well_id -> list of water-level readings (depth_m)

def _now_iso() -> str:
    return datetime.utcnow().isoformat()

def _uid(prefix: str = "bw") -> str:
    return f"{prefix}_{uuid.uuid4()}"

# -------------------------
# Borewell registry
# -------------------------
def add_borewell(
    farmer_id: str,
    name: str,
    location: Optional[str] = None,
    depth_m: Optional[float] = None,
    static_water_level_m: Optional[float] = None,
    recharge_area_m2: Optional[float] = None,
    recharge_coefficient: Optional[float] = 0.12,
    aquifer_area_m2: Optional[float] = None,
    specific_yield: Optional[float] = 0.1,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Register a borewell. Units:
      - depth_m: total borewell depth (m)
      - static_water_level_m: depth to water from ground level (m) (shallower = smaller number)
      - recharge_area_m2: area where recharge from rainfall is effective (m2)
      - recharge_coefficient: fraction of rainfall contributing to recharge (0..1)
      - aquifer_area_m2: horizontal spread area for converting volume to water table rise (m2)
      - specific_yield: dimensionless (0..1), default 0.1
    """
    wid = _uid("bore")
    rec = {
        "borewell_id": wid,
        "farmer_id": farmer_id,
        "name": name,
        "location": location or "",
        "depth_m": float(depth_m) if depth_m is not None else None,
        "static_water_level_m": float(static_water_level_m) if static_water_level_m is not None else None,
        "recharge_area_m2": float(recharge_area_m2) if recharge_area_m2 is not None else None,
        "recharge_coefficient": float(recharge_coefficient) if recharge_coefficient is not None else 0.12,
        "aquifer_area_m2": float(aquifer_area_m2) if aquifer_area_m2 is not None else (float(recharge_area_m2) if recharge_area_m2 else None),
        "specific_yield": float(specific_yield) if specific_yield is not None else 0.1,
        "metadata": metadata or {},
        "created_at": _now_iso(),
        "updated_at": None
    }
    with _lock:
        _borewells[wid] = rec
        _borewells_by_farmer.setdefault(farmer_id, []).append(wid)
    return rec

def get_borewell(borewell_id: str) -> Dict[str, Any]:
    with _lock:
        rec = _borewells.get(borewell_id)
        return rec.copy() if rec else {}

def list_borewells(farmer_id: str) -> List[Dict[str, Any]]:
    with _lock:
        ids = _borewells_by_farmer.get(farmer_id, [])
        return [ _borewells[i].copy() for i in ids ]

def update_borewell(borewell_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    with _lock:
        rec = _borewells.get(borewell_id)
        if not rec:
            return {"error": "not_found"}
        # cast numeric fields carefully
        for k in ("depth_m","static_water_level_m","recharge_area_m2","recharge_coefficient","aquifer_area_m2","specific_yield"):
            if k in updates and updates[k] is not None:
                try:
                    updates[k] = float(updates[k])
                except Exception:
                    pass
        rec.update(updates)
        rec["updated_at"] = _now_iso()
        _borewells[borewell_id] = rec
        return rec.copy()

def delete_borewell(borewell_id: str) -> Dict[str, Any]:
    with _lock:
        rec = _borewells.pop(borewell_id, None)
        if not rec:
            return {"error": "not_found"}
        farmer_id = rec.get("farmer_id")
        if farmer_id and farmer_id in _borewells_by_farmer:
            _borewells_by_farmer[farmer_id] = [i for i in _borewells_by_farmer[farmer_id] if i != borewell_id]
        _readings.pop(borewell_id, None)
        return {"status": "deleted", "borewell_id": borewell_id}

# -------------------------
# Readings: water-table / static level records
# -------------------------
def record_water_level_reading(
    borewell_id: str,
    timestamp_iso: Optional[str] = None,
    depth_to_water_m: Optional[float] = None,
    note: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    depth_to_water_m: depth from ground to water (m). Lower value means shallower water table.
    """
    with _lock:
        if borewell_id not in _borewells:
            return {"error": "borewell_not_found"}

    ts = None
    if timestamp_iso:
        try:
            ts = datetime.fromisoformat(timestamp_iso)
        except Exception:
            ts = datetime.utcnow()
    else:
        ts = datetime.utcnow()

    rec = {
        "reading_id": _uid("r"),
        "borewell_id": borewell_id,
        "timestamp": ts.isoformat(),
        "depth_to_water_m": float(depth_to_water_m) if depth_to_water_m is not None else None,
        "note": note or "",
        "metadata": metadata or {}
    }
    with _lock:
        _readings.setdefault(borewell_id, []).append(rec)
    return rec

def get_readings(borewell_id: str, limit: int = 200) -> List[Dict[str, Any]]:
    with _lock:
        items = list(_readings.get(borewell_id, []))
    items_sorted = sorted(items, key=lambda r: r.get("timestamp",""), reverse=True)[:limit]
    return items_sorted

# -------------------------
# Core recharge estimator
# -------------------------
def estimate_recharge_from_rainfall(
    borewell_id: str,
    rainfall_mm: float,
    days: int = 1
) -> Dict[str, Any]:
    """
    Estimate recharge volume (liters) and expected water table rise (meters) for a given rainfall (mm)
    over `days` days. If borewell metadata missing, apply conservative defaults.

    Returns:
      { recharged_liters, recharged_m3, water_table_rise_m, notes, inputs... }
    """
    with _lock:
        rec = _borewells.get(borewell_id)
        if not rec:
            return {"error": "borewell_not_found"}

    recharge_area_m2 = rec.get("recharge_area_m2") or rec.get("metadata", {}).get("recharge_area_m2")
    if not recharge_area_m2:
        # fallback: assume recharge area 5x borewell depth radial area (very rough)
        depth = rec.get("depth_m") or rec.get("metadata", {}).get("depth_m") or 10.0
        # assume radius 10 m * (depth/10) -> area pi*r^2; use simple factor
        recharge_area_m2 = 100.0  # default small area
    recharge_coeff = rec.get("recharge_coefficient") or 0.12
    aquifer_area_m2 = rec.get("aquifer_area_m2") or recharge_area_m2 * 10.0  # aquifer spreads wider than recharge zone
    specific_yield = rec.get("specific_yield") or 0.1

    # rainfall_mm is per day average or total over `days`; treat as total mm across days for simplicity
    try:
        total_rain_mm = float(rainfall_mm) * float(days)
    except Exception:
        total_rain_mm = float(rainfall_mm)

    # recharged volume in cubic meters: (rain_mm / 1000) * area_m2 * recharge_coeff
    recharged_m3 = (total_rain_mm / 1000.0) * float(recharge_area_m2) * float(recharge_coeff)
    recharged_liters = recharged_m3 * 1000.0

    # water table rise (meters) = recharged_m3 / (aquifer_area_m2 * specific_yield)
    try:
        water_table_rise_m = recharged_m3 / (float(aquifer_area_m2) * float(specific_yield))
    except Exception:
        water_table_rise_m = None

    return {
        "borewell_id": borewell_id,
        "rainfall_mm": total_rain_mm,
        "recharge_area_m2": recharge_area_m2,
        "recharge_coefficient": recharge_coeff,
        "aquifer_area_m2": aquifer_area_m2,
        "specific_yield": specific_yield,
        "recharged_liters": round(recharged_liters, 2),
        "recharged_m3": round(recharged_m3, 4),
        "water_table_rise_m": round(water_table_rise_m, 4) if water_table_rise_m is not None else None,
        "generated_at": _now_iso()
    }

def simulate_recharge_from_rain_series(
    borewell_id: str,
    daily_rainfall_mm: List[float],
    start_depth_to_water_m: Optional[float] = None,
    days_to_simulate: Optional[int] = None
) -> Dict[str, Any]:
    """
    Run a day-by-day simulation given daily rainfall series.
    Returns list of daily cumulative recharge and estimated water table depth (assuming no pumping).
    If start_depth_to_water_m is None, use latest recorded reading if present.
    """
    with _lock:
        rec = _borewells.get(borewell_id)
        if not rec:
            return {"error": "borewell_not_found"}

    if days_to_simulate is None:
        days_to_simulate = len(daily_rainfall_mm)

    # determine starting water table depth
    if start_depth_to_water_m is None:
        latest = None
        readings = _readings.get(borewell_id, [])
        if readings:
            try:
                latest = sorted(readings, key=lambda r: r.get("timestamp",""), reverse=True)[0]
                start_depth_to_water_m = latest.get("depth_to_water_m")
            except Exception:
                start_depth_to_water_m = None

    if start_depth_to_water_m is None:
        # default conservative value
        start_depth_to_water_m = rec.get("static_water_level_m") or rec.get("metadata", {}).get("static_water_level_m") or 10.0

    recharge_area_m2 = rec.get("recharge_area_m2") or rec.get("metadata", {}).get("recharge_area_m2") or 100.0
    recharge_coeff = rec.get("recharge_coefficient") or 0.12
    aquifer_area_m2 = rec.get("aquifer_area_m2") or recharge_area_m2 * 10.0
    specific_yield = rec.get("specific_yield") or 0.1

    timeline = []
    current_depth = float(start_depth_to_water_m)
    cumulative_recharged_m3 = 0.0

    for day_index in range(days_to_simulate):
        rain = float(daily_rainfall_mm[day_index]) if day_index < len(daily_rainfall_mm) else 0.0
        # estimate recharge for single day
        recharged_m3 = (rain / 1000.0) * float(recharge_area_m2) * float(recharge_coeff)
        cumulative_recharged_m3 += recharged_m3
        # water table rise in meters
        try:
            rise_m = recharged_m3 / (float(aquifer_area_m2) * float(specific_yield))
        except Exception:
            rise_m = 0.0
        # shallower water table => subtract depth
        current_depth = max(0.0, current_depth - rise_m)
        timeline.append({
            "day_index": day_index,
            "rain_mm": rain,
            "recharged_m3": round(recharged_m3, 4),
            "cumulative_recharged_m3": round(cumulative_recharged_m3, 4),
            "water_table_depth_m": round(current_depth, 3),
            "estimated_rise_m": round(rise_m, 4)
        })

    return {
        "borewell_id": borewell_id,
        "start_depth_to_water_m": start_depth_to_water_m,
        "timeline": timeline,
        "summary": {
            "total_recharged_m3": round(cumulative_recharged_m3, 4),
            "final_depth_to_water_m": round(current_depth, 3)
        },
        "generated_at": _now_iso()
    }

# -------------------------
# Observed recharge estimation (from readings)
# -------------------------
def estimate_observed_recharge_rate(borewell_id: str, lookback_days: int = 30) -> Dict[str, Any]:
    """
    Using recorded water level readings, estimate the observed recharge rate (m/day) and volume/day (m3/day)
    across the lookback window. We use simple linear regression (slope) if multiple readings are available.
    """
    with _lock:
        readings = list(_readings.get(borewell_id, []))

    if not readings or len(readings) < 2:
        return {"borewell_id": borewell_id, "error": "insufficient_readings"}

    # filter by lookback window
    cutoff = datetime.utcnow() - timedelta(days=lookback_days)
    filt = []
    for r in readings:
        try:
            ts = datetime.fromisoformat(r.get("timestamp"))
            if ts >= cutoff and r.get("depth_to_water_m") is not None:
                filt.append((ts, float(r.get("depth_to_water_m"))))
        except Exception:
            continue

    if len(filt) < 2:
        return {"borewell_id": borewell_id, "error": "insufficient_recent_readings"}

    # sort by time ascending
    filt_sorted = sorted(filt, key=lambda x: x[0])
    times = [(t - filt_sorted[0][0]).total_seconds() / 86400.0 for t, _ in filt_sorted]  # days since start
    depths = [d for _, d in filt_sorted]

    # compute slope (m/day) using simple least-squares
    n = len(times)
    mean_t = sum(times) / n
    mean_d = sum(depths) / n
    num = sum((times[i] - mean_t) * (depths[i] - mean_d) for i in range(n))
    den = sum((times[i] - mean_t) ** 2 for i in range(n)) or 1.0
    slope_m_per_day = num / den

    # positive slope means depth increasing (water table getting deeper) => negative recharge
    # convert slope to volume/day using aquifer area & specific yield if available
    with _lock:
        rec = _borewells.get(borewell_id)
    aquifer_area_m2 = rec.get("aquifer_area_m2") or (rec.get("recharge_area_m2") or 100.0) * 10.0
    specific_yield = rec.get("specific_yield") or 0.1

    # volume change per day (m3/day) = slope_m_per_day * aquifer_area_m2 * specific_yield * (-1)
    # (we use -1 so positive recharge corresponds to negative slope (shallower depth))
    volume_m3_per_day = -slope_m_per_day * float(aquifer_area_m2) * float(specific_yield)

    return {
        "borewell_id": borewell_id,
        "slope_m_per_day": round(slope_m_per_day, 6),
        "volume_m3_per_day": round(volume_m3_per_day, 4),
        "n_readings": n,
        "lookback_days": lookback_days,
        "generated_at": _now_iso()
    }

# -------------------------
# Utility summary
# -------------------------
def borewell_overview(farmer_id: str) -> Dict[str, Any]:
    with _lock:
        ids = _borewells_by_farmer.get(farmer_id, [])
        wells = []
        for wid in ids:
            w = _borewells.get(wid, {}).copy()
            latest = None
            rd = _readings.get(wid, [])
            if rd:
                latest = sorted(rd, key=lambda r: r.get("timestamp",""), reverse=True)[0]
            w["latest_reading"] = latest
            wells.append(w)
    return {"farmer_id": farmer_id, "count": len(wells), "borewells": wells, "generated_at": _now_iso()}
