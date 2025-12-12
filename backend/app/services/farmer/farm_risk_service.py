# backend/app/services/farmer/farm_risk_service.py

"""
Unified Farm Risk Assessment Engine (Feature #295 - Medium)

Produces a 0-100 risk score for a farm unit by combining environmental,
operational and crop-health signals. Designed to call existing in-memory
services when available and degrade gracefully.

Weights (default):
 - weather: 25%
 - pest/disease: 20%
 - operational (tasks/labour/equipment): 30%
 - crop health: 15%
 - stage vulnerability: 10%
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
import math

# Try optional imports from other services; if missing, we fallback to safe defaults
try:
    from app.services.farmer.weather_service import get_current_weather
except Exception:
    get_current_weather = None

try:
    from app.services.farmer.task_service import count_overdue_tasks, list_overdue_tasks
except Exception:
    count_overdue_tasks = None
    list_overdue_tasks = None

try:
    from app.services.farmer.labour_service import detect_labor_shortage
except Exception:
    detect_labor_shortage = None

try:
    from app.services.farmer.advisory_service import pest_triage, stage_practices
except Exception:
    pest_triage = None
    stage_practices = None

try:
    # if you have an equipment_service, it may provide availability or booking conflicts
    from app.services.farmer.equipment_service import equipment_availability_risk
except Exception:
    equipment_availability_risk = None

# local helpers
def _now_iso():
    return datetime.utcnow().isoformat()

def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))

def _score_to_level(score: float) -> str:
    if score >= 75:
        return "high"
    if score >= 40:
        return "moderate"
    return "low"

# -----------------------
# Component risk functions (return 0..100)
# -----------------------

def weather_risk(unit_id: Optional[int] = None, weather_override: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Compute environmental weather risk using heuristics:
     - high temperature stress (temp > 35C) -> raises risk
     - heavy rainfall forecast (>= 50mm in window) -> raises flood/waterlogging risk
     - drought risk: low rainfall & high evapotranspiration (not available) => heuristic
    """
    w = None
    if weather_override is not None:
        w = weather_override
    else:
        if get_current_weather and unit_id is not None:
            try:
                w = get_current_weather(unit_id) or {}
            except Exception:
                w = {}
        else:
            w = {}

    temp = float(w.get("temperature", 28) or 28)
    forecast_48h = float(w.get("forecast_rain_48h", w.get("rainfall_next_48h", 0)) or 0)
    recent_rain = float(w.get("recent_rain_mm", 0) or 0)

    # heuristics -> produce sub-scores 0..100
    temp_score = 0.0
    if temp >= 40:
        temp_score = 100.0
    elif temp >= 36:
        temp_score = 75.0
    elif temp >= 33:
        temp_score = 40.0
    else:
        temp_score = 5.0

    rain_score = 0.0
    if forecast_48h >= 75 or recent_rain >= 100:
        rain_score = 100.0  # flood / waterlogging risk
    elif forecast_48h >= 50:
        rain_score = 75.0
    elif forecast_48h >= 20:
        rain_score = 40.0
    else:
        rain_score = 5.0

    # if both high temp and heavy rain improbable, average them as weather risk
    combined = round((temp_score * 0.6) + (rain_score * 0.4), 2)
    return {"score": combined, "components": {"temperature_score": temp_score, "rain_score": rain_score}, "weather": w, "generated_at": _now_iso()}

def pest_risk(unit_id: Optional[int] = None, pest_alerts_count: Optional[int] = None, symptom_text: Optional[str] = None) -> Dict[str, Any]:
    """
    Pest/disease risk: either based on provided alert counts, or heuristic using symptom_text via pest_triage
    """
    alerts = pest_alerts_count if pest_alerts_count is not None else 0
    if alerts > 0:
        # map counts to 0..100
        if alerts >= 10:
            s = 100.0
        else:
            s = round((alerts / 10.0) * 100.0, 2)
        return {"score": s, "method": "alert_count", "alerts": alerts, "generated_at": _now_iso()}

    # fallback: use pest_triage to detect likely issues if symptom text is provided
    if pest_triage and symptom_text:
        try:
            triage = pest_triage(symptom_text)
            # if triage returned results, assign higher risk
            if triage.get("results"):
                s = 70.0
            elif triage.get("matches"):
                s = 40.0
            else:
                s = 10.0
            return {"score": s, "method": "symptom_triage", "triage": triage, "generated_at": _now_iso()}
        except Exception:
            pass

    # default low baseline
    return {"score": 10.0, "method": "none", "alerts": 0, "generated_at": _now_iso()}

def crop_health_risk(unit_id: Optional[int] = None, health_score: Optional[float] = None) -> Dict[str, Any]:
    """
    health_score is expected 0..100 (higher is better). We convert to risk as inverted value.
    If none provided, default neutral.
    """
    if health_score is None:
        # attempt to extract from other systems (not required)
        # default neutral: 50 health -> 50% risk invert -> 50 risk? We'll use neutral low risk.
        return {"score": 40.0, "method": "default", "health_score": None, "generated_at": _now_iso()}

    # clamp health between 0..100
    hs = max(0.0, min(100.0, float(health_score)))
    # risk decreases with health, so invert: risk = (100 - hs)
    risk = round(100.0 - hs, 2)
    return {"score": risk, "method": "provided", "health_score": hs, "generated_at": _now_iso()}

def operational_risk(unit_id: Optional[int] = None, farmer_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Combine task overdue, labor shortage, and equipment availability into one operational risk 0..100
    Each sub-component contributes equally (unless data missing).
    """
    sub_scores = []
    # 1) task risk: overdue tasks
    task_score = 0.0
    try:
        if count_overdue_tasks and unit_id is not None:
            try:
                overdue = count_overdue_tasks(unit_id)  # expecting integer
            except TypeError:
                # some implementations might require farmer_id
                overdue = count_overdue_tasks(farmer_id) if farmer_id else 0
            if overdue >= 10:
                task_score = 100.0
            else:
                task_score = round(min(100.0, (overdue / 10.0) * 100.0), 2)
        else:
            task_score = 20.0  # unknown => small baseline risk
    except Exception:
        task_score = 20.0
    sub_scores.append(("tasks", task_score))

    # 2) labour risk: detect shortages
    labour_score = 0.0
    try:
        if detect_labor_shortage and unit_id is not None:
            try:
                # detect_labor_shortage expects unit_id, stage, area - we try with minimal info
                shortage = detect_labor_shortage(str(unit_id), stage="", area_acres=0.0)
                # shortage returns shortage_hours; map to 0..100
                sh = float(shortage.get("shortage_hours", 0) or 0)
                if sh <= 0:
                    labour_score = 5.0
                elif sh >= 20:
                    labour_score = 100.0
                else:
                    labour_score = round(min(100.0, (sh / 20.0) * 100.0), 2)
            except Exception:
                labour_score = 20.0
        else:
            labour_score = 10.0
    except Exception:
        labour_score = 20.0
    sub_scores.append(("labour", labour_score))

    # 3) equipment risk: if equipment service exists, query it
    equip_score = 0.0
    try:
        if equipment_availability_risk and unit_id is not None:
            try:
                equip_score = float(equipment_availability_risk(unit_id).get("score", 0) or 0)
            except Exception:
                equip_score = 20.0
        else:
            equip_score = 10.0
    except Exception:
        equip_score = 20.0
    sub_scores.append(("equipment", equip_score))

    # compute mean of available sub-scores
    vals = [v for (_, v) in sub_scores if v is not None]
    if len(vals) == 0:
        combined = 20.0
    else:
        combined = round(sum(vals) / len(vals), 2)

    return {"score": combined, "components": {k: v for (k, v) in sub_scores}, "generated_at": _now_iso()}

def stage_vulnerability_risk(crop: Optional[str] = None, stage: Optional[str] = None) -> Dict[str, Any]:
    """
    Use stage_practices to see if stage is particularly vulnerable.
    For simplicity: if stage_practices for crop+stage is non-empty, vulnerability is moderate (30)
    If empty -> low (10)
    """
    if stage_practices and crop and stage:
        try:
            sp = stage_practices(crop, stage)
            practices = sp.get("practices", []) if isinstance(sp, dict) else []
            if practices:
                return {"score": 35.0, "method": "practices_present", "count_practices": len(practices), "generated_at": _now_iso()}
        except Exception:
            pass
    # default low vulnerability
    return {"score": 10.0, "method": "default", "generated_at": _now_iso()}

# -----------------------
# Weighting & combine engine
# -----------------------
DEFAULT_WEIGHTS = {
    "weather": 0.25,
    "pest": 0.20,
    "operational": 0.30,
    "health": 0.15,
    "stage": 0.10
}

def compute_risk_score(
    unit_id: Optional[int] = None,
    farmer_id: Optional[str] = None,
    *,
    weather_override: Optional[Dict[str, Any]] = None,
    pest_alerts_count: Optional[int] = None,
    symptom_text: Optional[str] = None,
    health_score: Optional[float] = None,
    crop: Optional[str] = None,
    stage: Optional[str] = None,
    weights: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Compute all components and return unified risk summary.
    """
    w = weights or DEFAULT_WEIGHTS

    # compute components
    w_comp = weather_risk(unit_id=unit_id, weather_override=weather_override)
    p_comp = pest_risk(unit_id=unit_id, pest_alerts_count=pest_alerts_count, symptom_text=symptom_text)
    op_comp = operational_risk(unit_id=unit_id, farmer_id=farmer_id)
    h_comp = crop_health_risk(unit_id=unit_id, health_score=health_score)
    s_comp = stage_vulnerability_risk(crop=crop, stage=stage)

    # convert to normalized 0..1
    ws = _clamp01(w_comp.get("score", 0) / 100.0)
    ps = _clamp01(p_comp.get("score", 0) / 100.0)
    ops = _clamp01(op_comp.get("score", 0) / 100.0)
    hs = _clamp01(h_comp.get("score", 0) / 100.0)
    ss = _clamp01(s_comp.get("score", 0) / 100.0)

    # combine with weights (weights are expected to sum to 1.0; if not, normalize)
    total_weight = sum([w.get(k, 0) for k in ["weather", "pest", "operational", "health", "stage"]])
    if total_weight <= 0:
        total_weight = 1.0

    norm_weights = {k: (w.get(k, 0)/total_weight) for k in w.keys()}

    combined_norm = (ws * norm_weights.get("weather",0)) + (ps * norm_weights.get("pest",0)) + (ops * norm_weights.get("operational",0)) + (hs * norm_weights.get("health",0)) + (ss * norm_weights.get("stage",0))
    combined_score = round(combined_norm * 100.0, 2)

    # basic recommendations heuristics
    recommendations: List[str] = []
    if w_comp.get("components",{}).get("temperature_score",0) >= 75 or w_comp.get("components",{}).get("rain_score",0) >= 75:
        recommendations.append("Monitor local weather closely and take protective measures (shade/netting or drainage).")

    if p_comp.get("score",0) >= 50:
        recommendations.append("Carry out immediate scouting and apply targeted pest/disease controls as per advisory.")

    if op_comp.get("score",0) >= 50:
        recommendations.append("Review overdue tasks and labour allocation; consider re-prioritizing critical operations.")

    if h_comp.get("score",0) >= 50:
        recommendations.append("Investigate crop health drivers (soil test, nutrient application, irrigation uniformity).")

    if s_comp.get("score",0) >= 30:
        recommendations.append("Follow stage-specific best practices and ensure critical operations are completed timely.")

    # fallback recommendation (if none created)
    if not recommendations:
        recommendations.append("No immediate high-risk signals detected. Continue routine monitoring and scouting.")

    out = {
        "unit_id": unit_id,
        "farmer_id": farmer_id,
        "risk_score": combined_score,
        "risk_level": _score_to_level(combined_score),
        "weights": norm_weights,
        "components": {
            "weather": w_comp,
            "pest": p_comp,
            "operational": op_comp,
            "health": h_comp,
            "stage": s_comp
        },
        "recommendations": recommendations,
        "generated_at": _now_iso()
    }
    return out
