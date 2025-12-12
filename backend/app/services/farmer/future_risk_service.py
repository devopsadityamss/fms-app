# backend/app/services/farmer/future_risk_service.py

"""
Future Risk Simulation Engine (Feature 302 - Medium)

Produces a 3/7-day forecast of farm risk for a unit by simulating:
 - weather-driven risk
 - schedule/task execution impact
 - behaviour/reliability impact
 - pest/disease interaction via humidity + stage
 - stage progression vulnerabilities

Design:
 - Rule-based weighted model
 - Uses compute_risk_score/get_current_weather/schedule_service/execution_monitor/adaptive_modifiers when available
 - Graceful fallbacks when dependencies missing
 - Returns list of day-by-day risk points with contributing factors
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from threading import Lock
import math

# Optional imports (best-effort)
try:
    from app.services.farmer.farm_risk_service import compute_risk_score, DEFAULT_WEIGHTS as RISK_DEFAULT_WEIGHTS
except Exception:
    compute_risk_score = None
    RISK_DEFAULT_WEIGHTS = None

try:
    from app.services.farmer.weather_service import get_forecast_weather, get_current_weather
except Exception:
    get_forecast_weather = None
    get_current_weather = None

try:
    from app.services.farmer.schedule_service import generate_schedule
except Exception:
    generate_schedule = None

try:
    from app.services.farmer.execution_monitor_service import get_farmer_reliability
except Exception:
    get_farmer_reliability = None

try:
    from app.services.farmer.adaptive_intelligence_service import get_modifiers_for_farmer
except Exception:
    get_modifiers_for_farmer = None

try:
    from app.services.farmer.early_warning_service import run_check as run_early_warning
except Exception:
    run_early_warning = None

_lock = Lock()

# Tunables
BASE_GROWTH_RATE = 0.0  # baseline daily drift in risk (percent)
WEIGHT_WEATHER = 0.35
WEIGHT_EXECUTION = 0.25
WEIGHT_BEHAVIOUR = 0.20
WEIGHT_STAGE = 0.15
WEIGHT_PEST = 0.05

DEFAULT_DAYS = 7

# Helper
def _now_iso():
    return datetime.utcnow().isoformat()

def _clamp(v: float) -> float:
    return max(0.0, min(100.0, float(round(v, 2))))

def _map_temp_to_risk(temp_c: float) -> float:
    # temp extremes raise risk; 28-33 is comfortable
    if temp_c >= 40:
        return 30.0
    if temp_c >= 36:
        return 20.0
    if temp_c >= 33:
        return 10.0
    if temp_c < 10:
        return 15.0
    return 2.0

def _map_rain_to_risk(rain_mm_24h: float) -> float:
    if rain_mm_24h >= 75:
        return 30.0
    if rain_mm_24h >= 50:
        return 20.0
    if rain_mm_24h >= 20:
        return 10.0
    if rain_mm_24h < 1:
        # dry stress incremental small risk
        return 6.0
    return 2.0

def _map_humidity_to_pest_risk(rel_humidity: float) -> float:
    if rel_humidity >= 85:
        return 20.0
    if rel_humidity >= 75:
        return 12.0
    if rel_humidity >= 60:
        return 6.0
    return 1.0

def _combine_components(components: Dict[str, float], weights: Dict[str, float]) -> float:
    total = 0.0
    for k, v in components.items():
        w = weights.get(k, 0.0)
        total += (v * w)
    return total

# Default weight map used internally (these are relative; final normalised by sum)
DEFAULT_COMPONENT_WEIGHTS = {
    "weather": WEIGHT_WEATHER,
    "execution": WEIGHT_EXECUTION,
    "behaviour": WEIGHT_BEHAVIOUR,
    "stage": WEIGHT_STAGE,
    "pest": WEIGHT_PEST
}

# -------------------------
# Sub-simulators
# -------------------------
def _simulate_weather_component(day_index: int, unit_id: Optional[int], weather_forecast_override: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    Returns approximate weather-driven risk for a day index (0=current day, 1=tomorrow, ...).
    weather_forecast_override: list-of-day dicts -> [{ "day":0,"temp":..,"rain_mm":..,"humidity":..}, ...]
    If get_forecast_weather exists it will be used (best-effort).
    """
    # default safe values
    temp = 28.0
    rain = 0.0
    humidity = 60.0

    if weather_forecast_override and len(weather_forecast_override) > day_index:
        w = weather_forecast_override[day_index]
        temp = float(w.get("temp", temp))
        rain = float(w.get("rain_mm", rain))
        humidity = float(w.get("humidity", humidity))
    else:
        # attempt to call weather service
        try:
            if get_forecast_weather and unit_id is not None:
                # expect get_forecast_weather(unit_id, days) -> list-of-day dicts or dict with forecasts
                fc = get_forecast_weather(unit_id, days=day_index+1)
                # the API of get_forecast_weather may vary; best-effort parse
                if isinstance(fc, list) and len(fc) > day_index:
                    w = fc[day_index]
                    temp = float(w.get("temperature", temp) or temp)
                    # try multiple keys
                    rain = float(w.get("forecast_rain_24h", w.get("rain_mm", w.get("rainfall_mm", rain))) or rain)
                    humidity = float(w.get("humidity", humidity) or humidity)
                elif isinstance(fc, dict) and fc.get("daily"):
                    daily = fc.get("daily")
                    if len(daily) > day_index:
                        w = daily[day_index]
                        temp = float(w.get("temp", {}).get("day", temp) or temp)
                        rain = float(w.get("rain", rain) or rain)
                        humidity = float(w.get("humidity", humidity) or humidity)
        except Exception:
            # fallback to current weather for day 0
            if day_index == 0 and get_current_weather and unit_id is not None:
                try:
                    cw = get_current_weather(unit_id)
                    temp = float(cw.get("temperature", temp) or temp)
                    rain = float(cw.get("rainfall_mm", rain) or rain)
                    humidity = float(cw.get("humidity_pct", humidity) or humidity)
                except Exception:
                    pass

    temp_risk = _map_temp_to_risk(temp)
    rain_risk = _map_rain_to_risk(rain)
    pest_humidity_risk = _map_humidity_to_pest_risk(humidity)
    # weather component primarily from temp+rain; humidity reported separately for pest module
    weather_score = round((temp_risk * 0.6) + (rain_risk * 0.4), 2)
    return {"weather_score": weather_score, "temp": temp, "rain_mm": rain, "humidity": humidity, "pest_humidity_risk": pest_humidity_risk}

def _simulate_execution_component(day_index: int, unit_id: Optional[int], schedule: Optional[Dict[str, Any]] = None, simulate_execute_plan: bool = False) -> Dict[str, Any]:
    """
    Estimate impact of scheduled actions. If simulate_execute_plan True -> assume scheduled actions succeed.
    Otherwise assume a fraction based on historical reliability.
    schedule: dict as returned by generate_schedule (today/next_3_days/next_7_days)
    """
    # default neutral
    exec_impact = 0.0
    reasons = []

    # count high-priority mitigation actions planned for this day
    planned_actions = []
    if schedule:
        # map day_index -> bucket
        if day_index == 0:
            planned_actions = schedule.get("today", [])
        elif 1 <= day_index <= 3:
            # fill from next_3_days (approx)
            planned_actions = schedule.get("next_3_days", [])
        else:
            planned_actions = schedule.get("next_7_days", [])

    high_priority_count = sum(1 for a in planned_actions if int(a.get("priority", 0)) >= 70)
    if high_priority_count:
        reasons.append(f"{high_priority_count} high-priority planned actions")

    # reliability baseline
    reliability_pct = 70.0
    if get_farmer_reliability and schedule:
        # try to get farmer id from first action if present
        try:
            fid = None
            if schedule.get("today"):
                fid = schedule["today"][0].get("details", {}).get("farmer_id") or schedule["today"][0].get("details", {}).get("farmer") or None
            if fid is None:
                # cannot get farmer id; skip
                pass
        except Exception:
            pass

    # if simulate_execute_plan is True -> assume actions reduce risk
    if simulate_execute_plan:
        # each high priority action reduces execution component risk by 5..12 depending on count
        exec_impact = -min(40.0, 8.0 * high_priority_count)
        if high_priority_count:
            reasons.append("Assuming scheduled high-priority actions execute -> reduced risk")
    else:
        # otherwise assume partial adherence; small benefit if actions exist but rely on behaviour
        if high_priority_count:
            exec_impact = -min(15.0, 3.0 * high_priority_count)
            reasons.append("Planned actions present but not assumed executed -> small benefit only")

    return {"execution_score_delta": exec_impact, "planned_high_priority": high_priority_count, "reasons": reasons}

def _simulate_behaviour_component(day_index: int, farmer_id: Optional[str], behaviour_modifier: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Behaviour acts as a multiplier to growth (bad behaviour increases future risk growth).
    Use farmer reliability and adaptive modifiers if available.
    """
    # default neutral multiplier 1.0 => no change
    multiplier = 1.0
    reasons = []

    # reliability if available
    reliability_score = None
    try:
        if farmer_id and get_farmer_reliability:
            rr = get_farmer_reliability(farmer_id)
            reliability_score = rr.get("reliability_score")
    except Exception:
        reliability_score = None

    # adaptive modifiers
    mods = {}
    try:
        if farmer_id and get_modifiers_for_farmer:
            mods = get_modifiers_for_farmer(farmer_id) or {}
    except Exception:
        mods = {}

    # apply basic logic:
    if behaviour_modifier and isinstance(behaviour_modifier, dict):
        # allow external override influence values like "aggressive": 1.2
        multiplier = float(behaviour_modifier.get("multiplier", multiplier))
        reasons.append("External behaviour modifier applied")
    elif reliability_score is not None:
        # low reliability -> increase risk growth; high reliability reduces growth
        if reliability_score >= 85:
            multiplier = 0.85
            reasons.append("High farmer reliability -> lower risk growth")
        elif reliability_score >= 70:
            multiplier = 0.95
            reasons.append("Good reliability -> slight reduction")
        elif reliability_score >= 50:
            multiplier = 1.0
            reasons.append("Average reliability")
        else:
            multiplier = 1.2
            reasons.append("Low reliability -> higher risk growth")
    else:
        # fallback to adaptive modifier for schedule capacity if present
        sc = mods.get("schedule_capacity_multiplier")
        if sc is not None:
            if sc < 0.8:
                multiplier = 1.12
                reasons.append("Low schedule capacity modifier -> mild increase in growth")
            elif sc > 1.2:
                multiplier = 0.9
                reasons.append("High schedule capacity modifier -> reduced growth")

    return {"behaviour_multiplier": round(multiplier, 3), "reliability_score": reliability_score, "reasons": reasons}

def _simulate_stage_component(day_index: int, crop: Optional[str], stage: Optional[str]) -> Dict[str, Any]:
    """
    Estimate stage vulnerability for the upcoming day(s).
    For now: map known sensitive stages to small risk increments.
    """
    # simple mapping of vulnerable stages
    vulnerable_map = {
        "sowing": 8.0,
        "germination": 6.0,
        "vegetative": 4.0,
        "flowering": 12.0,
        "fruiting": 8.0,
        "harvest": 10.0
    }
    s_key = (stage or "").lower()
    base = vulnerable_map.get(s_key, 3.0)
    # assume vulnerability highest in the mid-window for flowering etc; for day index weighting reduce away from 0
    day_penalty = max(0.5, 1.0 - (day_index * 0.12))
    score = round(base * day_penalty, 2)
    return {"stage_vulnerability_score": score, "stage": stage, "crop": crop}

def _simulate_pest_component(day_index: int, weather_info: Dict[str, Any], crop: Optional[str], stage: Optional[str]) -> Dict[str, Any]:
    """
    Pest risk driven by humidity + stage vulnerability + prior alerts (if available via early_warning_service).
    """
    humidity = float(weather_info.get("humidity", 60.0) or 60.0)
    pest_humidity_risk = _map_humidity_to_pest_risk(humidity)
    stage_factor = 0.0
    if stage and stage.lower() in ("flowering", "germination", "vegetative"):
        stage_factor = 5.0
    # try to incorporate early warnings if available
    early_pest_flag = False
    try:
        # we won't call run_early_warning here for every day (expensive), caller may supply more context
        pass
    except Exception:
        pass

    score = round(pest_humidity_risk + stage_factor + (10.0 if early_pest_flag else 0.0), 2)
    return {"pest_score": score, "humidity": humidity, "stage_factor": stage_factor, "early_flag": early_pest_flag}

# -------------------------
# Main simulator
# -------------------------
def simulate_future_risk(
    unit_id: Optional[int],
    days: int = DEFAULT_DAYS,
    farmer_id: Optional[str] = None,
    crop: Optional[str] = None,
    stage: Optional[str] = None,
    weather_forecast_override: Optional[List[Dict[str, Any]]] = None,
    schedule_override: Optional[Dict[str, Any]] = None,
    behaviour_modifier: Optional[Dict[str, Any]] = None,
    simulate_execute_plan: bool = False,
    base_seed_risk: Optional[float] = None
) -> Dict[str, Any]:
    """
    Simulate future risk timeline for `days` days (default 7).
    Returns:
      {
        "unit_id": ...,
        "generated_at": ...,
        "days": [ {"day_index":0,"date":"...","risk":xx,"components":{...},"factors":[...]} , ... ],
        "summary": {...}
      }

    - simulate_execute_plan: if True, assume scheduled actions execute as planned (bigger risk reduction)
    - schedule_override: optional precomputed schedule dict to be used instead of calling generate_schedule
    - weather_forecast_override: list-of-dicts with per-day weather overrides (temp, rain_mm, humidity)
    """
    days = max(1, int(days))
    timeline: List[Dict[str, Any]] = []

    # attempt to get a seed/current risk from compute_risk_score
    seed_risk = 40.0
    if base_seed_risk is not None:
        seed_risk = float(base_seed_risk)
    else:
        try:
            if compute_risk_score and unit_id is not None:
                rr = compute_risk_score(unit_id=unit_id, farmer_id=farmer_id, crop=crop, stage=stage)
                seed_risk = rr.get("risk_score", seed_risk) or seed_risk
        except Exception:
            pass

    seed_risk = _clamp(seed_risk)

    # attempt to fetch/generate schedule (best-effort)
    schedule = schedule_override
    if schedule is None:
        try:
            if generate_schedule and unit_id is not None:
                schedule = generate_schedule(unit_id=unit_id, farmer_id=farmer_id, crop=crop, stage=stage)
        except Exception:
            schedule = None

    # compute per-day simulations
    current_risk = float(seed_risk)
    for d in range(days):
        date_for_day = (datetime.utcnow() + timedelta(days=d)).date().isoformat()
        # weather component
        weather_info = _simulate_weather_component(d, unit_id, weather_forecast_override)
        weather_score = weather_info["weather_score"]

        # execution component
        exec_info = _simulate_execution_component(d, unit_id, schedule=schedule, simulate_execute_plan=simulate_execute_plan)
        exec_delta = exec_info["execution_score_delta"]

        # behaviour component (multiplier on growth)
        behaviour_info = _simulate_behaviour_component(d, farmer_id, behaviour_modifier)
        behaviour_mult = behaviour_info.get("behaviour_multiplier", 1.0)

        # stage vulnerability
        stage_info = _simulate_stage_component(d, crop, stage)
        stage_score = stage_info["stage_vulnerability_score"]

        # pest component (uses weather humidity)
        pest_info = _simulate_pest_component(d, weather_info, crop, stage)
        pest_score = pest_info["pest_score"]

        # aggregate components into day's delta relative to baseline
        components = {
            "weather": weather_score,
            "execution_delta": exec_delta,       # can be negative (reducing risk)
            "behaviour_multiplier": behaviour_mult,
            "stage": stage_score,
            "pest": pest_score
        }

        # combine baseline: base_component_score = weighted sum of weather, stage, pest
        comp_for_combine = {
            "weather": weather_score,
            "stage": stage_score,
            "pest": pest_score,
            # execution and behaviour not direct additive but modify growth; we'll include execution as delta later
            "execution": max(0.0, -exec_delta)  # convert negative exec_delta -> reduction; positive none
        }
        combined_component_score = _combine_components(comp_for_combine, DEFAULT_COMPONENT_WEIGHTS)

        # growth: day_growth = base + combined_component_score * influence * behaviour_mult
        # baseline growth uses small BASE_GROWTH_RATE + normalized combined score factor
        day_growth_raw = BASE_GROWTH_RATE + (combined_component_score * 0.02)  # scale down component contribution
        # apply behaviour multiplier
        day_growth_adjusted = day_growth_raw * behaviour_mult

        # apply execution delta directly (benefit if negative)
        risk_next = current_risk + day_growth_adjusted + exec_delta
        # safety clamps and smoothing
        risk_next = _clamp(risk_next)

        # collect factors for explainability (top contributors)
        factors = []
        # include weather flags
        if weather_info.get("temp", 0) >= 36:
            factors.append("High temperature stress")
        if weather_info.get("rain_mm", 0) >= 50:
            factors.append("Heavy rainfall / waterlogging risk")
        if weather_info.get("pest_humidity_risk", 0) >= 12:
            factors.append("High humidity → pest risk")

        if exec_info.get("planned_high_priority", 0) > 0:
            if simulate_execute_plan:
                factors.append("Planned high-priority actions assumed executed → reduced near-term risk")
            else:
                factors.append("Planned actions exist but execution uncertain")

        if behaviour_info.get("reliability_score") is not None and behaviour_info.get("reliability_score") < 50:
            factors.append("Low farmer reliability increases escalation risk")

        if stage_info.get("stage"):
            factors.append(f"Stage vulnerability: {stage_info.get('stage')}")

        timeline.append({
            "day_index": d,
            "date": date_for_day,
            "risk": round(risk_next, 2),
            "components": components,
            "weather": {"temp": weather_info.get("temp"), "rain_mm": weather_info.get("rain_mm"), "humidity": weather_info.get("humidity")},
            "exec_info": exec_info,
            "behaviour_info": behaviour_info,
            "stage_info": stage_info,
            "pest_info": pest_info,
            "factors": factors
        })

        # next iteration seed
        current_risk = risk_next

    # compute summary trends
    risk_vals = [p["risk"] for p in timeline]
    trend = {}
    if len(risk_vals) >= 2:
        trend["start"] = risk_vals[0]
        trend["end"] = risk_vals[-1]
        trend["delta"] = round(risk_vals[-1] - risk_vals[0], 2)
        trend["direction"] = "up" if trend["delta"] > 0 else ("down" if trend["delta"] < 0 else "flat")
    else:
        trend["start"] = risk_vals[0] if risk_vals else None
        trend["end"] = trend["start"]
        trend["delta"] = 0.0
        trend["direction"] = "flat"

    return {
        "unit_id": unit_id,
        "farmer_id": farmer_id,
        "generated_at": _now_iso(),
        "days": timeline,
        "summary": {"trend": trend, "days_simulated": days, "seed_risk": seed_risk}
    }
