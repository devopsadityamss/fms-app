# backend/app/services/farmer/irrigation_service.py

from datetime import datetime, timedelta, date
from typing import Dict, Any, List, Optional, Callable
from threading import Lock
import math
import uuid

# Shared in-memory stores from other services
try:
    from app.services.farmer.unit_service import _unit_store
except Exception:
    _unit_store = {}

try:
    from app.services.farmer.season_calendar_service import get_calendar_for_unit, generate_season_calendar_for_unit
except Exception:
    get_calendar_for_unit = generate_season_calendar_for_unit = lambda *args, **kwargs: None

try:
    from app.services.farmer.risk_alerts_service import evaluate_risks_for_unit
except Exception:
    evaluate_risks_for_unit = lambda *args, **kwargs: {"alerts": []}


"""
Unified Irrigation Intelligence Engine (in-memory)

Features from both systems:
1. Smart Irrigation Scheduling (ET0-based, forecast-aware, soil-aware, avoid windows, risk-aware)
2. Irrigation Logging + Moisture/Weather Updates
3. Real-time Recommendations (urgency, next date, duration)
4. Under/Over Irrigation Pattern Detection
5. Full Summary Dashboard

All functionality preserved and enhanced — ready for sensor integration & API use.
"""

# ===================================================================
# 1. SMART IRRIGATION SCHEDULER (Forecast + Soil + Risk Aware)
# ===================================================================

_irrigation_schedule_store: Dict[str, Dict[str, Any]] = {}
_schedule_lock = Lock()

# Default crop coefficients & root zones
_DEFAULT_KC = {
    "wheat": 0.9, "rice": 1.05, "maize": 1.15, "cotton": 0.8, "soybean": 1.0, "paddy": 1.1
}
_DEFAULT_ROOT_DEPTH_M = {
    "wheat": 0.5, "rice": 0.3, "maize": 0.7, "cotton": 0.6, "soybean": 0.6, "paddy": 0.3
}
_DEFAULT_AWC_MM_PER_M = 150.0
_DEFAULT_MAD = 0.5


def _area_acre_to_m2(area_acre: float) -> float:
    return float(area_acre) * 4046.8564224


def _mm_to_liters(mm: float, area_m2: float) -> float:
    return mm * area_m2


def _estimate_root_zone_depth(crop: str) -> float:
    return _DEFAULT_ROOT_DEPTH_M.get(str(crop).lower(), 0.5)


def _estimate_kc(crop: str) -> float:
    return _DEFAULT_KC.get(str(crop).lower(), 1.0)


def compute_available_water_mm(root_zone_m: Optional[float] = None, awc_mm_per_m: float = _DEFAULT_AWC_MM_PER_M) -> float:
    rz = root_zone_m if root_zone_m is not None else 0.5
    return rz * awc_mm_per_m


def compute_daily_crop_water_need_mm(et0_mm: float, crop: str, kc_override: Optional[float] = None) -> float:
    kc = kc_override if kc_override is not None else _estimate_kc(crop)
    return float(et0_mm) * float(kc)


def estimate_soil_moisture_deficit_mm(
    unit_id: str,
    current_soil_moisture_pct: Optional[float],
    root_zone_m: Optional[float] = None,
    awc_mm_per_m: float = _DEFAULT_AWC_MM_PER_M
) -> Dict[str, Any]:
    rz = root_zone_m if root_zone_m is not None else _estimate_root_zone_depth(_unit_store.get(unit_id, {}).get("crop", ""))
    aw = compute_available_water_mm(rz, awc_mm_per_m)
    if current_soil_moisture_pct is None:
        current_storage = 0.6 * aw
    else:
        current_storage = max(0.0, min(100.0, float(current_soil_moisture_pct))) / 100.0 * aw
    depletion = aw - current_storage
    return {
        "available_water_mm": aw,
        "current_storage_mm": round(current_storage, 2),
        "depletion_mm": round(depletion, 2)
    }


def schedule_irrigation_for_unit(
    unit_id: str,
    et0_forecast: List[Dict[str, Any]],
    start_date_iso: Optional[str] = None,
    end_date_iso: Optional[str] = None,
    soil_moisture_pct: Optional[float] = None,
    system_flow_rate_lph: float = 2000.0,
    kc_override: Optional[float] = None,
    mad: float = _DEFAULT_MAD,
    awc_mm_per_m: float = _DEFAULT_AWC_MM_PER_M,
    avoid_windows: Optional[List[Dict[str, str]]] = None,
    lookahead_days: int = 14
) -> Dict[str, Any]:
    unit = _unit_store.get(unit_id)
    if not unit:
        return {"status": "unit_not_found", "unit_id": unit_id}

    area_acre = float(unit.get("area", 1.0) or 1.0)
    area_m2 = _area_acre_to_m2(area_acre)
    crop = unit.get("crop")
    root_zone = _estimate_root_zone_depth(crop)
    aw_mm = compute_available_water_mm(root_zone, awc_mm_per_m)

    today = datetime.utcnow().date()
    start = datetime.fromisoformat(start_date_iso).date() if start_date_iso else today
    end = datetime.fromisoformat(end_date_iso).date() if end_date_iso else (start + timedelta(days=lookahead_days))

    fc_map = {d["date"]: d for d in et0_forecast} if et0_forecast else {}
    avoid_parsed = []
    if avoid_windows:
        for w in avoid_windows:
            try:
                s = datetime.fromisoformat(w.get("start")).date()
                e = datetime.fromisoformat(w.get("end")).date()
                avoid_parsed.append({"start": s, "end": e})
            except Exception:
                continue

    deficit_info = estimate_soil_moisture_deficit_mm(unit_id, soil_moisture_pct, root_zone_m=root_zone, awc_mm_per_m=awc_mm_per_m)
    depletion_mm = deficit_info["depletion_mm"]
    allow_depletion_mm = mad * aw_mm

    events = []
    cursor = start

    while cursor <= end:
        date_str = cursor.isoformat()
        fc = fc_map.get(date_str, {})
        et0 = float(fc.get("et0_mm", 4.0) or 0.0)
        rain = float(fc.get("rain_mm", 0.0) or 0.0)

        daily_need_mm = compute_daily_crop_water_need_mm(et0, crop, kc_override=kc_override)
        effective_rain = min(rain, 20.0)
        net_need_mm = max(0.0, daily_need_mm - effective_rain)
        depletion_mm += net_need_mm

        if depletion_mm >= allow_depletion_mm:
            apply_mm = min(depletion_mm, aw_mm)
            liters = _mm_to_liters(apply_mm, area_m2)
            duration_hours = round(max(0.1, liters / float(system_flow_rate_lph)), 2)

            in_avoid = any(cursor >= w["start"] and cursor <= w["end"] for w in avoid_parsed)
            scheduled_date = cursor
            reason = []
            if in_avoid:
                for w in avoid_parsed:
                    if cursor >= w["start"] and cursor <= w["end"]:
                        scheduled_date = w["end"] + timedelta(days=1)
                        reason.append("shifted_due_to_avoid_window")
                        break

            ra = evaluate_risks_for_unit(unit_id, weather_now=None, inputs_snapshot=None, auto_record=False)
            priority = "high" if any(a.get("severity") == "high" for a in ra.get("alerts", [])) else "normal"
            if priority == "high":
                reason.append("high_risk_alerts_present")

            event = {
                "unit_id": unit_id,
                "scheduled_date": scheduled_date.isoformat(),
                "apply_mm": round(apply_mm, 2),
                "liters": round(liters, 2),
                "duration_hours": duration_hours,
                "system_flow_rate_lph": system_flow_rate_lph,
                "priority": priority,
                "reason": reason or ["depletion_exceeded_allowable"],
                "computed_at": datetime.utcnow().isoformat()
            }
            events.append(event)
            depletion_mm = max(0.0, depletion_mm - apply_mm)
            cursor += timedelta(days=1)
            continue

        cursor += timedelta(days=1)

    schedule = {
        "unit_id": unit_id,
        "crop": crop,
        "area_acre": area_acre,
        "root_zone_m": root_zone,
        "available_water_mm": round(aw_mm, 2),
        "allowable_depletion_mm": round(allow_depletion_mm, 2),
        "generated_at": datetime.utcnow().isoformat(),
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "events": events
    }

    with _schedule_lock:
        _irrigation_schedule_store[unit_id] = schedule

    return schedule


def get_irrigation_schedule(unit_id: str) -> Optional[Dict[str, Any]]:
    with _schedule_lock:
        return _irrigation_schedule_store.get(unit_id)


def list_all_schedules() -> Dict[str, Any]:
    with _schedule_lock:
        return {"count": len(_irrigation_schedule_store), "schedules": list(_irrigation_schedule_store.values())}


# ===================================================================
# 2. IRRIGATION LOGGING + REAL-TIME RECOMMENDATIONS
# ===================================================================

_irrigation_logs: Dict[str, Dict[str, Any]] = {}
_logs_by_unit: Dict[str, List[str]] = {}
_soil_moisture: Dict[str, Dict[str, Any]] = {}
_weather_cache: Dict[str, Dict[str, Any]] = {}

Kc_TABLE = {
    "paddy": {"initial": 1.1, "mid": 1.2, "late": 0.9},
    "wheat": {"initial": 0.7, "mid": 1.05, "late": 0.8},
    "maize": {"initial": 0.7, "mid": 1.15, "late": 0.9},
    "generic": {"initial": 0.7, "mid": 1.0, "late": 0.8}
}

METHOD_EFFICIENCY = {
    "drip": 0.9, "sprinkler": 0.75, "flood": 0.5
}

def _now(): return datetime.utcnow().isoformat()


# Moisture + Weather
def update_soil_moisture(unit_id: str, moisture_pct: float):
    _soil_moisture[unit_id] = {"moisture_pct": float(moisture_pct), "updated_at": _now()}
    return _soil_moisture[unit_id]

def update_weather(unit_id: str, rainfall_mm: float, evapotranspiration_et0: float):
    _weather_cache[unit_id] = {"rainfall_mm": rainfall_mm, "et0": evapotranspiration_et0, "updated_at": _now()}
    return _weather_cache[unit_id]

def get_moisture(unit_id: str): return _soil_moisture.get(unit_id)
def get_weather(unit_id: str): return _weather_cache.get(unit_id)


# Irrigation Logging
def log_irrigation(
    unit_id: str,
    method: str,
    duration_minutes: float,
    water_used_liters: Optional[float] = None,
    notes: Optional[str] = None
):
    log_id = f"ir_{uuid.uuid4()}"
    rec = {
        "log_id": log_id, "unit_id": unit_id, "method": method,
        "duration_minutes": float(duration_minutes),
        "water_used_liters": float(water_used_liters) if water_used_liters is not None else None,
        "notes": notes or "", "created_at": _now()
    }
    _irrigation_logs[log_id] = rec
    _logs_by_unit.setdefault(unit_id, []).append(log_id)
    return rec

def list_irrigation_logs(unit_id: str):
    return [_irrigation_logs[i] for i in _logs_by_unit.get(unit_id, [])]


# Water Requirement & Recommendation
def compute_water_requirement(crop: str, stage: str, area_acres: float, unit_id: str) -> Dict[str, Any]:
    weather = get_weather(unit_id) or {"rainfall_mm": 0, "et0": 4}
    kc = Kc_TABLE.get(crop.lower(), Kc_TABLE["generic"]).get(stage.lower(), 1.0)
    etc = weather["et0"] * kc
    net = max(0, etc - weather["rainfall_mm"])
    efficiency = METHOD_EFFICIENCY.get("flood", 0.7)
    gross = net / efficiency
    total_liters = gross * 4046 * area_acres
    return {
        "crop": crop, "stage": stage, "area_acres": area_acres,
        "etc_mm": round(etc, 2), "rainfall_mm": weather["rainfall_mm"],
        "net_requirement_mm": round(net, 2), "gross_requirement_liters": round(total_liters, 2)
    }


def recommend_irrigation(unit_id: str, crop: str, stage: str, area_acres: float, method: str = "flood"):
    moisture = get_moisture(unit_id)
    moisture_pct = moisture["moisture_pct"] if moisture else 20
    water_req = compute_water_requirement(crop, stage, area_acres, unit_id)
    efficiency = METHOD_EFFICIENCY.get(method, 0.7)
    flow_rate_lpm = 15
    duration_minutes = water_req["gross_requirement_liters"] / flow_rate_lpm

    urgency = "critical" if moisture_pct < 20 else "high" if moisture_pct < 30 else "medium" if moisture_pct < 40 else "low"
    next_date = datetime.utcnow().date() + timedelta(days=2 if urgency == "low" else 1 if urgency == "medium" else 0)

    return {
        "unit_id": unit_id, "urgency": urgency, "recommended_method": method,
        "recommended_irrigation_date": next_date.isoformat(),
        "recommended_duration_minutes": round(duration_minutes, 2),
        "water_requirement": water_req, "moisture_pct": moisture_pct,
        "last_irrigations": list_irrigation_logs(unit_id)[-3:],
        "timestamp": _now()
    }


def irrigation_pattern_analysis(unit_id: str):
    logs = list_irrigation_logs(unit_id)
    if not logs:
        return {"unit_id": unit_id, "status": "no_data"}
    avg_dur = sum(l["duration_minutes"] for l in logs) / len(logs)
    status = "over_irrigation" if avg_dur > 90 else "under_irrigation" if avg_dur < 20 else "balanced"
    return {"unit_id": unit_id, "avg_duration": round(avg_dur, 2), "status": status, "timestamp": _now()}


def irrigation_summary(unit_id: str, crop: str, stage: str, area_acres: float):
    return {
        "unit_id": unit_id,
        "moisture": get_moisture(unit_id),
        "weather": get_weather(unit_id),
        "logs": list_irrigation_logs(unit_id),
        "analysis": irrigation_pattern_analysis(unit_id),
        "next_recommendation": recommend_irrigation(unit_id, crop, stage, area_acres),
        "smart_schedule": get_irrigation_schedule(unit_id),
        "timestamp": _now()
    }