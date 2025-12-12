# backend/app/services/farmer/yield_service.py

"""
Yield Prediction & Harvest Planning (in-memory)

- record_field_measurement: store periodic observations (ndvi, biomass_est, rainfall, fertilizer_applied)
- record_harvest: store actual harvest results (yield_kg, revenue)
- predict_yield: light-weight heuristic prediction using weighted features
- plan_harvest: estimate harvest window, labor needs, expected revenue
- trend: historical yields and simple moving average
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import uuid
import math

# stores
_field_measurements: Dict[str, Dict[str, Any]] = {}    # meas_id -> record
_measurements_by_unit: Dict[str, List[str]] = {}      # unit_id -> [meas_id]

_harvest_records: Dict[str, Dict[str, Any]] = {}
_harvests_by_unit: Dict[str, List[str]] = {}

# simple variety/crop multipliers (can be extended)
CROP_VARIETY_FACTORS = {
    "paddy": {"default": 1.0, "high_yield_variety": 1.15},
    "wheat": {"default": 1.0, "dhw_var": 1.1},
    "maize": {"default": 1.0, "hybrid": 1.2}
}


def _now_iso():
    return datetime.utcnow().isoformat()


# -----------------------------
# Recording functions
# -----------------------------
def record_field_measurement(
    unit_id: str,
    measured_at_iso: Optional[str],
    ndvi: Optional[float] = None,
    biomass_est: Optional[float] = None,
    rainfall_mm: Optional[float] = None,
    fertilizer_applied_kg: Optional[float] = None,
    notes: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    mid = f"meas_{uuid.uuid4()}"
    rec = {
        "meas_id": mid,
        "unit_id": str(unit_id),
        "measured_at_iso": measured_at_iso or _now_iso(),
        "ndvi": float(ndvi) if ndvi is not None else None,
        "biomass_est": float(biomass_est) if biomass_est is not None else None,
        "rainfall_mm": float(rainfall_mm) if rainfall_mm is not None else None,
        "fertilizer_applied_kg": float(fertilizer_applied_kg) if fertilizer_applied_kg is not None else None,
        "notes": notes or "",
        "metadata": metadata or {},
        "created_at": _now_iso()
    }
    _field_measurements[mid] = rec
    _measurements_by_unit.setdefault(str(unit_id), []).append(mid)
    return rec


def list_measurements(unit_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    ids = _measurements_by_unit.get(str(unit_id), [])[:]
    # return newest first
    return [ _field_measurements[i] for i in reversed(ids[-limit:]) ]


def record_harvest(
    unit_id: str,
    harvest_date_iso: Optional[str],
    yield_kg: float,
    price_per_kg: Optional[float] = None,
    notes: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    hid = f"harv_{uuid.uuid4()}"
    total_rev = round((price_per_kg or 0) * float(yield_kg), 2) if price_per_kg else None
    rec = {
        "harvest_id": hid,
        "unit_id": str(unit_id),
        "harvest_date_iso": harvest_date_iso or _now_iso(),
        "yield_kg": float(yield_kg),
        "price_per_kg": float(price_per_kg) if price_per_kg is not None else None,
        "revenue": total_rev,
        "notes": notes or "",
        "metadata": metadata or {},
        "created_at": _now_iso()
    }
    _harvest_records[hid] = rec
    _harvests_by_unit.setdefault(str(unit_id), []).append(hid)
    return rec


def list_harvests(unit_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    ids = _harvests_by_unit.get(str(unit_id), [])[:]
    return [ _harvest_records[i] for i in reversed(ids[-limit:]) ]


# -----------------------------
# Prediction heuristics
# -----------------------------
def _recent_measurements_for_unit(unit_id: str, lookback_days: int = 21) -> List[Dict[str, Any]]:
    rows = list_measurements(unit_id, limit=1000)
    cutoff = datetime.utcnow() - timedelta(days=lookback_days)
    res = []
    for r in rows:
        try:
            dt = datetime.fromisoformat(r["measured_at_iso"])
        except Exception:
            dt = datetime.fromisoformat(r["created_at"])
        if dt >= cutoff:
            res.append(r)
    return res


def predict_yield(
    unit_id: str,
    crop: str,
    variety: Optional[str],
    area_acres: float,
    baseline_yield_per_acre: Optional[float] = None
) -> Dict[str, Any]:
    """
    Predict yield (kg) using:
     - baseline yield per acre (if not provided use crop defaults)
     - recent NDVI (0..1) average
     - biomass estimates (kg/ha-like), normalize and weight
     - rainfall in recent period
     - fertilizer applied (kg)
     - variety factor
    Returns predicted_total_kg, per_acre_kg, confidence (0..1) and feature contributions.
    """

    crop = (crop or "generic").lower()
    variety = variety or "default"
    # fallback base yields (kg per acre)
    DEFAULT_BASE_YIELD = {"paddy": 3000.0, "wheat": 2500.0, "maize": 3500.0, "generic": 2000.0}
    base = baseline_yield_per_acre or DEFAULT_BASE_YIELD.get(crop, DEFAULT_BASE_YIELD["generic"])

    recs = _recent_measurements_for_unit(unit_id, lookback_days=30)
    # features aggregation
    ndvi_vals = [r["ndvi"] for r in recs if r.get("ndvi") is not None]
    avg_ndvi = sum(ndvi_vals)/len(ndvi_vals) if ndvi_vals else None

    biomass_vals = [r["biomass_est"] for r in recs if r.get("biomass_est") is not None]
    avg_biomass = sum(biomass_vals)/len(biomass_vals) if biomass_vals else None

    rainfall_total = sum(r.get("rainfall_mm",0) or 0 for r in recs)
    fertilizer_total = sum(r.get("fertilizer_applied_kg",0) or 0 for r in recs)

    # compute multipliers from features
    ndvi_mul = 1.0
    if avg_ndvi is not None:
        # map typical NDVI 0.2..0.9 to 0.7..1.3 multiplier
        ndvi_mul = 0.7 + ((avg_ndvi - 0.2) / 0.7) * 0.6
        ndvi_mul = max(0.5, min(1.5, ndvi_mul))

    biomass_mul = 1.0
    if avg_biomass is not None:
        # assume biomass 0..1000 (kg/ha-like) map to 0.8..1.25
        biomass_mul = 0.8 + min(avg_biomass, 1000)/1000 * 0.45
        biomass_mul = max(0.6, min(1.4, biomass_mul))

    rain_mul = 1.0
    # ideal rainfall window (last 30 days) depends on crop; use simple heuristic:
    if rainfall_total < 20:
        rain_mul = 0.9
    elif rainfall_total > 200:
        rain_mul = 0.95
    else:
        rain_mul = 1.05

    fert_mul = 1.0
    if fertilizer_total > 0:
        # modest uplift if fertilizer applied
        fert_mul = 1.0 + min(fertilizer_total/100.0, 0.2)

    variety_factor = 1.0
    try:
        variety_factor = CROP_VARIETY_FACTORS.get(crop, {}).get(variety, CROP_VARIETY_FACTORS.get(crop, {}).get("default", 1.0))
    except Exception:
        variety_factor = 1.0

    # final per-acre estimation
    per_acre = base * ndvi_mul * biomass_mul * rain_mul * fert_mul * variety_factor
    total_kg = round(per_acre * float(area_acres), 2)

    # confidence estimation based on number & recency of measurements
    confidence = 0.5
    if ndvi_vals or biomass_vals:
        # more data increases confidence
        confidence += min(0.4, (len(ndvi_vals)+len(biomass_vals))/20)
        # measurements recency
        if recs:
            newest = recs[0]
            try:
                age_days = (datetime.utcnow() - datetime.fromisoformat(newest["measured_at_iso"])).days
            except Exception:
                age_days = 10
            if age_days <= 3:
                confidence += 0.05
            elif age_days <= 10:
                confidence += 0.02
    confidence = min(0.99, confidence)

    # feature contributions for explainability
    features = {
        "base_yield_per_acre": base,
        "avg_ndvi": avg_ndvi,
        "ndvi_multiplier": round(ndvi_mul,3),
        "avg_biomass": avg_biomass,
        "biomass_multiplier": round(biomass_mul,3),
        "rainfall_total_mm": round(rainfall_total,2),
        "rain_multiplier": round(rain_mul,3),
        "fertilizer_total_kg": round(fertilizer_total,2),
        "fertilizer_multiplier": round(fert_mul,3),
        "variety_factor": round(variety_factor,3)
    }

    return {
        "unit_id": str(unit_id),
        "crop": crop,
        "variety": variety,
        "area_acres": area_acres,
        "predicted_total_kg": total_kg,
        "predicted_per_acre_kg": round(per_acre,2),
        "confidence": round(confidence,3),
        "features": features,
        "timestamp": _now_iso()
    }


# -----------------------------
# Harvest planning
# -----------------------------
def plan_harvest(
    unit_id: str,
    predicted_total_kg: float,
    price_per_kg: Optional[float],
    harvest_rate_kg_per_hour: Optional[float] = 100.0,
    laborers_available: Optional[int] = 2
) -> Dict[str, Any]:
    """
    Estimate labor hours, harvest duration (days), estimated revenue, and recommended harvest window.
    """

    # labor hours needed
    rate = float(harvest_rate_kg_per_hour) if harvest_rate_kg_per_hour and harvest_rate_kg_per_hour>0 else 100.0
    hours_needed = predicted_total_kg / rate
    total_labor_hours = hours_needed
    # if multiple laborers working in parallel
    effective_hours = total_labor_hours / (laborers_available or 1)
    days_needed = math.ceil(effective_hours / 8.0)

    est_revenue = round((price_per_kg or 0) * float(predicted_total_kg), 2) if price_per_kg else None

    # naive harvest window: earliest tomorrow to days_needed from tomorrow
    start = datetime.utcnow().date() + timedelta(days=1)
    end = start + timedelta(days=max(1, days_needed))

    return {
        "unit_id": str(unit_id),
        "predicted_total_kg": round(float(predicted_total_kg),2),
        "hours_needed": round(hours_needed,2),
        "laborers_assumed": laborers_available or 1,
        "days_needed": days_needed,
        "estimated_revenue": est_revenue,
        "harvest_window_start": start.isoformat(),
        "harvest_window_end": end.isoformat(),
        "notes": "Adjust harvest_rate_kg_per_hour and laborers_available for different scenarios",
        "timestamp": _now_iso()
    }


# -----------------------------
# Trending & simple metrics
# -----------------------------
def yield_trend(unit_id: str, last_n: int = 6) -> Dict[str, Any]:
    """
    Return last_n harvests and simple moving average.
    """
    harvs = list_harvests(unit_id, limit=1000)
    samples = [h for h in harvs][:last_n]
    ys = [s["yield_kg"] for s in samples] if samples else []
    sma = None
    if ys:
        sma = round(sum(ys)/len(ys),2)
    return {"unit_id": str(unit_id), "recent_harvests": samples, "simple_moving_avg_kg": sma}
