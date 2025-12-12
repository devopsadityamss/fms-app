# backend/app/services/farmer/moisture_calibration_service.py
"""
Moisture Calibration & Sensor Integration Service (Feature 333)

Provides:
 - manage calibration profiles for sensors (linear model: calibrated = a * raw + b)
 - train calibration from paired lab sensor readings
 - map sensors to harvest lots (sensor -> lot_id)
 - apply calibration to sensor timeseries and produce calibrated series
 - simple diagnostics & summary statistics
"""

from datetime import datetime
from threading import Lock
from typing import Dict, Any, List, Optional, Tuple
import uuid
import statistics

# defensive imports (best-effort)
try:
    from app.services.farmer.harvest_lot_service import list_quality_tests, get_harvest_lot
except Exception:
    list_quality_tests = lambda lot_id: []
    get_harvest_lot = lambda lot_id: {}

_lock = Lock()

_profiles: Dict[str, Dict[str, Any]] = {}          # profile_id -> { sensor_id, a, b, trained_at, samples: [...] }
_profiles_by_sensor: Dict[str, str] = {}          # sensor_id -> profile_id
_sensor_to_lot: Dict[str, str] = {}               # sensor_id -> lot_id
_sensor_readings: Dict[str, List[Dict[str, Any]]] = {}  # sensor_id -> [{ts, raw_value, metadata}]

def _now_iso():
    return datetime.utcnow().isoformat()

def _uid(prefix="cal"):
    return f"{prefix}_{uuid.uuid4()}"

# -----------------------
# Sensor readings ingestion (store raw)
# -----------------------
def ingest_sensor_reading(sensor_id: str, timestamp_iso: Optional[str], raw_moisture_pct: float, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    rec = {
        "reading_id": _uid("sr"),
        "sensor_id": sensor_id,
        "timestamp": (timestamp_iso or _now_iso()),
        "raw_moisture_pct": float(raw_moisture_pct),
        "metadata": metadata or {}
    }
    with _lock:
        _sensor_readings.setdefault(sensor_id, []).append(rec)
    return rec

def list_sensor_readings(sensor_id: str, limit: int = 1000) -> List[Dict[str, Any]]:
    with _lock:
        items = list(_sensor_readings.get(sensor_id, []))
    # return newest first
    return sorted(items, key=lambda r: r.get("timestamp",""), reverse=False)[:limit]

# -----------------------
# Calibration profile CRUD
# -----------------------
def create_calibration_profile(sensor_id: str, a: float = 1.0, b: float = 0.0, samples: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    profile: calibrated = a * raw + b
    """
    pid = _uid("prof")
    rec = {
        "profile_id": pid,
        "sensor_id": sensor_id,
        "a": float(a),
        "b": float(b),
        "samples": samples or [],  # list of {"raw":..., "lab":..., "ts":...}
        "trained_at": None,
        "created_at": _now_iso(),
        "updated_at": None
    }
    with _lock:
        _profiles[pid] = rec
        _profiles_by_sensor[sensor_id] = pid
    return rec

def get_profile(profile_id: str) -> Dict[str, Any]:
    with _lock:
        p = _profiles.get(profile_id)
        return p.copy() if p else {}

def get_profile_for_sensor(sensor_id: str) -> Dict[str, Any]:
    with _lock:
        pid = _profiles_by_sensor.get(sensor_id)
        if not pid:
            return {}
        return _profiles.get(pid, {}).copy()

def list_profiles() -> List[Dict[str, Any]]:
    with _lock:
        return list(_profiles.values())

def delete_profile(profile_id: str) -> Dict[str, Any]:
    with _lock:
        p = _profiles.pop(profile_id, None)
        if not p:
            return {"error": "not_found"}
        sid = p.get("sensor_id")
        if sid and sid in _profiles_by_sensor and _profiles_by_sensor[sid] == profile_id:
            _profiles_by_sensor.pop(sid, None)
    return {"status": "deleted", "profile_id": profile_id}

# -----------------------
# Map sensor -> lot
# -----------------------
def map_sensor_to_lot(sensor_id: str, lot_id: str) -> Dict[str, Any]:
    with _lock:
        _sensor_to_lot[sensor_id] = lot_id
    return {"sensor_id": sensor_id, "lot_id": lot_id, "mapped_at": _now_iso()}

def get_mapped_lot(sensor_id: str) -> Optional[str]:
    return _sensor_to_lot.get(sensor_id)

# -----------------------
# Calibration training
# -----------------------
def train_profile_from_samples(profile_id: str, samples: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    samples: list of { raw: float, lab: float, ts: Optional[str] }
    Train simple linear regression y = a*x + b using least squares.
    Store a/b and samples in profile.
    """
    if not samples or len(samples) < 2:
        return {"error": "insufficient_samples"}

    xs = []
    ys = []
    for s in samples:
        try:
            xs.append(float(s.get("raw")))
            ys.append(float(s.get("lab")))
        except Exception:
            continue

    if len(xs) < 2:
        return {"error": "insufficient_numeric_samples"}

    n = len(xs)
    mean_x = sum(xs)/n
    mean_y = sum(ys)/n
    num = sum((xs[i]-mean_x)*(ys[i]-mean_y) for i in range(n))
    den = sum((xs[i]-mean_x)**2 for i in range(n)) or 1.0
    a = num/den
    b = mean_y - a*mean_x

    with _lock:
        prof = _profiles.get(profile_id)
        if not prof:
            return {"error": "profile_not_found"}
        prof["a"] = float(a)
        prof["b"] = float(b)
        prof["samples"] = samples
        prof["trained_at"] = _now_iso()
        prof["updated_at"] = _now_iso()
        _profiles[profile_id] = prof

    return {"profile_id": profile_id, "a": round(a,6), "b": round(b,6), "n_samples": n, "trained_at": prof["trained_at"]}

def train_profile_for_sensor(sensor_id: str, samples: List[Dict[str, Any]]) -> Dict[str, Any]:
    prof = get_profile_for_sensor(sensor_id)
    if not prof:
        prof = create_calibration_profile(sensor_id)
    return train_profile_from_samples(prof["profile_id"], samples)

# -----------------------
# Calibrate raw value
# -----------------------
def apply_calibration_to_value(sensor_id: str, raw_value: float) -> float:
    prof = get_profile_for_sensor(sensor_id)
    if not prof:
        # no profile -> return raw
        return float(raw_value)
    a = float(prof.get("a",1.0))
    b = float(prof.get("b",0.0))
    return float(a*float(raw_value) + b)

# -----------------------
# Calibrated timeseries for a sensor or for a lot
# -----------------------
def calibrated_timeseries_for_sensor(sensor_id: str, limit: int = 1000) -> Dict[str, Any]:
    raws = list_sensor_readings(sensor_id, limit=limit)
    calib = []
    for r in raws:
        calibrated = apply_calibration_to_value(sensor_id, r["raw_moisture_pct"])
        rec = {
            "reading_id": r["reading_id"],
            "timestamp": r["timestamp"],
            "raw_moisture_pct": r["raw_moisture_pct"],
            "calibrated_moisture_pct": round(calibrated,3),
            "metadata": r.get("metadata",{})
        }
        calib.append(rec)
    return {"sensor_id": sensor_id, "count": len(calib), "series": calib}

def calibrated_timeseries_for_lot(lot_id: str, limit_per_sensor: int = 1000) -> Dict[str, Any]:
    """
    For all sensors mapped to this lot, fetch calibrated timeseries and merge by timestamp ascending.
    """
    # find sensors mapped to lot_id
    with _lock:
        sensors = [s for s,l in _sensor_to_lot.items() if l == lot_id]
    merged = []
    for s in sensors:
        series = calibrated_timeseries_for_sensor(s, limit=limit_per_sensor).get("series", [])
        for rec in series:
            merged.append({"sensor_id": s, **rec})
    # sort by timestamp
    merged_sorted = sorted(merged, key=lambda r: r.get("timestamp",""))
    return {"lot_id": lot_id, "count": len(merged_sorted), "series": merged_sorted}

# -----------------------
# Diagnostics & summary
# -----------------------
def calibration_summary_for_sensor(sensor_id: str) -> Dict[str, Any]:
    prof = get_profile_for_sensor(sensor_id)
    readings = list_sensor_readings(sensor_id, limit=1000)
    if not readings:
        return {"sensor_id": sensor_id, "error": "no_readings"}

    raw_vals = [r["raw_moisture_pct"] for r in readings if r.get("raw_moisture_pct") is not None]
    if not raw_vals:
        return {"sensor_id": sensor_id, "error": "no_numeric_readings"}

    calib_vals = [apply_calibration_to_value(sensor_id, v) for v in raw_vals]
    stats = {
        "raw_mean": round(statistics.mean(raw_vals),3),
        "raw_stdev": round(statistics.pstdev(raw_vals),3) if len(raw_vals)>1 else 0.0,
        "calib_mean": round(statistics.mean(calib_vals),3),
        "calib_stdev": round(statistics.pstdev(calib_vals),3) if len(calib_vals)>1 else 0.0,
        "n_readings": len(raw_vals),
        "profile": prof or {}
    }
    return {"sensor_id": sensor_id, "stats": stats}

# -----------------------
# Utility: pair lab tests with nearest sensor reading by timestamp
# -----------------------
def pair_lab_with_sensor_samples(sensor_id: str, lab_samples: List[Dict[str,Any]], max_seconds_delta: int = 3600) -> List[Dict[str,Any]]:
    """
    lab_samples: [{ ts: iso, lab_moisture_pct: float }, ...]
    For each lab sample, find nearest sensor reading within max_seconds_delta and return pairs.
    """
    sensor_series = list_sensor_readings(sensor_id, limit=10000)
    out = []
    import bisect
    # build sorted timestamps list
    sensor_ts = [s["timestamp"] for s in sensor_series]
    for ls in lab_samples:
        lts = ls.get("ts") or ls.get("timestamp")
        if not lts:
            continue
        # find nearest
        best = None
        best_dt_diff = None
        for s in sensor_series:
            try:
                sd = s["timestamp"]
                # crude iso comparison - assume both iso strings compatible lexicographically; fallback to parsing
                import dateutil.parser as dp  # may not exist; fall back
                try:
                    st = dp.parse(sd)
                    lt = dp.parse(lts)
                    dt = abs((lt - st).total_seconds())
                except Exception:
                    # fallback parse with datetime.fromisoformat if possible
                    try:
                        st = datetime.fromisoformat(sd)
                        lt = datetime.fromisoformat(lts)
                        dt = abs((lt - st).total_seconds())
                    except Exception:
                        dt = None
                if dt is None:
                    continue
                if dt <= max_seconds_delta and (best_dt_diff is None or dt < best_dt_diff):
                    best_dt_diff = dt
                    best = s
            except Exception:
                continue
        if best:
            out.append({"lab_ts": lts, "lab_moisture_pct": ls.get("lab_moisture_pct"), "sensor_reading": best})
    return out
