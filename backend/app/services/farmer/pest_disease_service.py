# backend/app/services/farmer/pest_disease_service.py

"""
Pest & Disease Forecasting (in-memory)

Features:
 - record vision-based or manual alerts per unit
 - compute risk score using simple heuristics combining:
     recent alerts, temperature, humidity, rainfall, crop susceptibility, phenological stage
 - classify risk into low/medium/high/critical
 - suggest recommended actions (inspect, spray, scout, apply biocontrol)
 - provide simulated short-term forecast (next N days) using forecasted weather inputs
 - list recent alerts and aggregate counts
"""

from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, Any, List, Optional
import uuid
import math

_lock = Lock()

# alert store: alert_id -> alert record
_alerts: Dict[str, Dict[str, Any]] = {}

# index by unit: unit_id -> [alert_id, ...]
_alerts_by_unit: Dict[str, List[str]] = {}

# quick crop susceptibility map (heuristic)
CROP_SUSCEPTIBILITY = {
    "paddy": {"fungal": 1.3, "bacterial": 1.1, "insect": 1.0},
    "wheat": {"fungal": 1.2, "bacterial": 1.0, "insect": 1.0},
    "maize": {"fungal": 1.1, "bacterial": 1.0, "insect": 1.2},
    "cotton": {"fungal": 1.0, "bacterial": 1.0, "insect": 1.3},
}

def _now_iso():
    return datetime.utcnow().isoformat()

def _uid(prefix: str):
    return f"{prefix}_{uuid.uuid4()}"

# -------------------------
# Create / record alerts
# -------------------------
def record_alert(
    reporter_id: str,
    unit_id: str,
    crop: str,
    stage: Optional[str],
    alert_type: str,  # e.g., fungal, bacterial, insect, nutrient_symptom, unknown
    confidence: float,  # 0..1 from vision model or human estimate
    image_meta: Optional[Dict[str, Any]] = None,
    notes: Optional[str] = None,
    location: Optional[Dict[str, float]] = None,
    timestamp_iso: Optional[str] = None
) -> Dict[str, Any]:
    """
    Store an incoming alert (vision or manual).
    """
    aid = _uid("alert")
    rec = {
        "alert_id": aid,
        "reporter_id": reporter_id,
        "unit_id": str(unit_id),
        "crop": crop.lower(),
        "stage": stage,
        "alert_type": alert_type,
        "confidence": float(confidence),
        "image_meta": image_meta or {},
        "notes": notes or "",
        "location": location or {},
        "timestamp_iso": timestamp_iso or _now_iso(),
        "severity": None,  # computed later
    }
    # compute provisional severity
    rec["severity"] = classify_severity_from_alert(rec)
    with _lock:
        _alerts[aid] = rec
        _alerts_by_unit.setdefault(str(unit_id), []).append(aid)
    return rec

def get_alert(alert_id: str) -> Dict[str, Any]:
    return _alerts.get(alert_id, {})

def list_alerts_for_unit(unit_id: str, since_days: Optional[int] = 30) -> List[Dict[str, Any]]:
    unit_id = str(unit_id)
    ids = _alerts_by_unit.get(unit_id, [])[:]
    res = []
    cutoff = None
    if since_days:
        cutoff = datetime.utcnow() - timedelta(days=since_days)
    for aid in reversed(ids):
        a = _alerts.get(aid)
        if not a:
            continue
        if cutoff:
            try:
                if datetime.fromisoformat(a.get("timestamp_iso")) < cutoff:
                    continue
            except Exception:
                pass
        res.append(a)
    return res

# -------------------------
# Heuristics: risk scoring
# -------------------------
def classify_severity_from_alert(alert: Dict[str, Any]) -> str:
    """
    Simple mapping: confidence * type weight -> severity band
    """
    base = alert.get("confidence", 0.0)
    t = alert.get("alert_type", "unknown")
    crop = alert.get("crop", "")
    type_w = 1.0
    if t in ("fungal", "bacterial"):
        type_w = 1.2
    elif t == "insect":
        type_w = 1.1
    elif t == "nutrient_symptom":
        type_w = 0.8
    # crop susceptibility
    crop_s = 1.0
    try:
        crop_s = CROP_SUSCEPTIBILITY.get(crop, {}).get(t, 1.0)
    except Exception:
        crop_s = 1.0
    score = base * type_w * crop_s
    # bands
    if score >= 0.75:
        return "critical"
    if score >= 0.5:
        return "high"
    if score >= 0.25:
        return "medium"
    return "low"

def compute_risk_score_for_unit(
    unit_id: str,
    recent_days: int = 7,
    weather: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Produce a risk score (0..100) for a unit using recent alerts and basic weather heuristics.
    weather: {temperature, humidity, rainfall_mm, wind_speed}
    """

    unit_id = str(unit_id)
    recent_alerts = list_alerts_for_unit(unit_id, since_days=recent_days)
    # base from alerts: weighted by severity and confidence and recency
    severity_weights = {"low": 0.5, "medium": 1.0, "high": 1.5, "critical": 2.0}
    now = datetime.utcnow()
    alert_score = 0.0
    max_possible = 0.0
    for a in recent_alerts:
        conf = float(a.get("confidence", 0.0))
        sev = a.get("severity", "low")
        w = severity_weights.get(sev, 1.0)
        # recency weight: fresher alerts matter more
        try:
            age_days = (now - datetime.fromisoformat(a.get("timestamp_iso"))).days
        except Exception:
            age_days = 0
        recency_w = max(0.1, 1.0 - (age_days / float(recent_days + 1)))
        incremental = conf * w * recency_w
        alert_score += incremental
        max_possible += 1.0 * 2.0 * 1.0  # conf(1.0) * max weight * recency 1.0

    alert_score_norm = (alert_score / max(1.0, max_possible)) if max_possible > 0 else 0.0

    # weather-based adjustments: warm + humid + rain create fungal risk
    weather_adj = 0.0
    if weather:
        temp = float(weather.get("temperature", 25))
        hum = float(weather.get("humidity", 60))
        rain = float(weather.get("rainfall_mm", 0))
        # fungal risk factor
        if temp >= 20 and temp <= 30 and hum >= 70:
            weather_adj += 0.2
        if rain > 10:
            weather_adj += 0.2
        # dry windy conditions increase insect spread
        wind = float(weather.get("wind_speed", 5))
        if wind > 10 and hum < 50:
            weather_adj += 0.1

    # baseline vulnerability if crop susceptible
    crop_vul = 1.0
    if recent_alerts:
        crop = recent_alerts[0].get("crop")
        if crop:
            crop_vul = 1.0 + (CROP_SUSCEPTIBILITY.get(crop, {}).get("fungal", 1.0) - 1.0)

    # compute aggregated risk score 0..100
    raw = (alert_score_norm * 0.6) + (weather_adj * 0.3) + ((crop_vul - 1.0) * 0.1)
    # clamp
    raw = max(0.0, min(raw, 1.0))
    risk_pct = round(raw * 100, 2)

    # map to band
    band = "low"
    if risk_pct >= 75:
        band = "critical"
    elif risk_pct >= 50:
        band = "high"
    elif risk_pct >= 25:
        band = "medium"

    # recommended actions heuristic
    actions = recommend_actions_from_risk(band)

    return {
        "unit_id": unit_id,
        "risk_score": risk_pct,
        "risk_band": band,
        "recent_alerts_count": len(recent_alerts),
        "weather_adjustment": round(weather_adj, 2),
        "crop_vulnerability_factor": round(crop_vul, 2),
        "recommended_actions": actions,
        "timestamp": _now_iso()
    }

def recommend_actions_from_risk(band: str) -> List[str]:
    if band == "critical":
        return ["Inspect immediately", "Isolate affected area", "Consider emergency spraying (consult expert)", "Collect lab sample"]
    if band == "high":
        return ["Scout fields within 24 hours", "Apply recommended fungicide/insecticide if confirmed", "Increase monitoring frequency"]
    if band == "medium":
        return ["Regular scouting", "Apply cultural controls (remove affected leaves)", "Monitor weather"]
    return ["Routine scouting", "No immediate action"]

# -------------------------
# Simulate short-term forecast
# -------------------------
def simulate_forecast_for_unit(
    unit_id: str,
    days: int = 5,
    baseline_weather: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Returns a list of predicted risk scores for next `days`.
    baseline_weather: optional list of day weather dicts; if omitted we use mild defaults.
    """
    predictions = []
    for i in range(days):
        # pick weather for day
        w = {}
        if baseline_weather and i < len(baseline_weather):
            w = baseline_weather[i]
        else:
            # mild synthetic fluctuation
            temp = 25 + 2 * math.sin(i)
            hum = 60 + 10 * math.cos(i)
            rain = 5 if (i % 3 == 0) else 0
            w = {"temperature": temp, "humidity": hum, "rainfall_mm": rain, "wind_speed": 6}
        risk = compute_risk_score_for_unit(unit_id, recent_days=7, weather=w)
        # attach day offset
        predictions.append({"day_offset": i, "date": (datetime.utcnow() + timedelta(days=i)).date().isoformat(), "weather": w, "prediction": risk})
    return {"unit_id": str(unit_id), "predictions": predictions}

# -------------------------
# Aggregations / counts
# -------------------------
def aggregate_alerts_summary(unit_id: Optional[str] = None, since_days: int = 30) -> Dict[str, Any]:
    """
    Returns counts by severity and type for unit or globally
    """
    cutoff = datetime.utcnow() - timedelta(days=since_days)
    cnts = {"total": 0, "by_severity": {}, "by_type": {}}
    with _lock:
        ids = []
        if unit_id:
            ids = _alerts_by_unit.get(str(unit_id), [])[:]
        else:
            ids = list(_alerts.keys())
        for aid in ids:
            a = _alerts.get(aid)
            if not a:
                continue
            try:
                if datetime.fromisoformat(a.get("timestamp_iso")) < cutoff:
                    continue
            except Exception:
                pass
            cnts["total"] += 1
            sev = a.get("severity", "low")
            cnts["by_severity"][sev] = cnts["by_severity"].get(sev, 0) + 1
            typ = a.get("alert_type", "unknown")
            cnts["by_type"][typ] = cnts["by_type"].get(typ, 0) + 1
    return cnts

# -------------------------
# Optional hook: send notification (left as stub)
# -------------------------
def alert_and_notify_if_critical(alert_rec: Dict[str, Any], notify_callback: Optional[callable] = None) -> Dict[str, Any]:
    """
    If alert severity is high/critical, optionally call notify_callback(notification_payload)
    notify_callback should accept a dict; it's up to the integrator to wire to notification service.
    """
    if alert_rec.get("severity") in ("high", "critical"):
        payload = {
            "unit_id": alert_rec.get("unit_id"),
            "alert_id": alert_rec.get("alert_id"),
            "severity": alert_rec.get("severity"),
            "message": f"{alert_rec.get('alert_type')} alert with confidence {alert_rec.get('confidence')}"
        }
        try:
            if notify_callback:
                notify_callback(payload)
        except Exception:
            pass
    return {"notified": alert_rec.get("severity") in ("high", "critical")}

