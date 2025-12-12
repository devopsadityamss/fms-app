# backend/app/services/farmer/early_warning_service.py

"""
Advanced Early Warning Service (Feature 296 - Option B)

- Maintains in-memory history (sliding window) of risk snapshots per unit
- Produces deterministic warnings from weather, operational, crop health, pests and stage vulnerabilities
- Detects trends (slope/relative change) across recent risk history
- Can trigger notifications via notification_service.immediate_send() if available
- Designed to degrade gracefully if dependent services are absent
"""

from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, Any, List, Optional, Tuple
import math
import statistics

# Attempt to import dependent services; graceful fallback if missing
try:
    from app.services.farmer.farm_risk_service import compute_risk_score
except Exception:
    compute_risk_score = None

try:
    from app.services.farmer.weather_service import get_current_weather
except Exception:
    get_current_weather = None

try:
    from app.services.farmer.task_service import count_overdue_tasks
except Exception:
    count_overdue_tasks = None

try:
    from app.services.farmer.labour_service import detect_labor_shortage
except Exception:
    detect_labor_shortage = None

try:
    from app.services.farmer.advisory_service import pest_triage, stage_practices
except Exception:
    pest_triage = None
    stage_practices = None

# optional notification sender
try:
    from app.services.farmer.notification_service import immediate_send
except Exception:
    immediate_send = None

_lock = Lock()

# In-memory storage
# history: unit_id -> list of snapshots (newest last) ; each snapshot is {timestamp, risk_score, components}
_HISTORY: Dict[str, List[Dict[str, Any]]] = {}
# raw last computed warnings: unit_id -> last warnings list
_LAST_WARNINGS: Dict[str, List[Dict[str, Any]]] = {}

# config
HISTORY_WINDOW = 14  # keep last 14 snapshots (e.g., daily or on-demand)
TREND_MIN_POINTS = 3  # min data points for trend detection

# thresholds (tunable)
TEMPERATURE_HEATWAVE_THRESHOLD_C = 37.0
HEAVY_RAIN_THRESHOLD_MM_48H = 50.0
RAPID_HEALTH_DROP_PERCENT = 15.0  # percent drop in health score considered rapid
OVERDUE_TASKS_WARNING_COUNT = 3   # overdue tasks >= this triggers operational warning
LABOR_SHORTAGE_HOURS_THRESHOLD = 5.0  # shortage hours to trigger labor warning

def _now_iso() -> str:
    return datetime.utcnow().isoformat()

def _push_history(unit_id: str, snapshot: Dict[str, Any]) -> None:
    with _lock:
        lst = _HISTORY.setdefault(unit_id, [])
        lst.append(snapshot)
        # trim history
        if len(lst) > HISTORY_WINDOW:
            lst[:] = lst[-HISTORY_WINDOW:]

def _get_history(unit_id: str) -> List[Dict[str, Any]]:
    with _lock:
        return list(_HISTORY.get(unit_id, []))

# ---------- trend helpers ----------
def _compute_trend(values: List[float]) -> Dict[str, Any]:
    """
    Simple trend detection:
      - slope via linear regression (least squares) normalized per step
      - percent_change from first to last
    Returns {"slope": float, "percent_change": float, "direction": "up"/"down"/"flat"}
    """
    n = len(values)
    if n == 0:
        return {"slope": 0.0, "percent_change": 0.0, "direction": "flat"}
    if n == 1:
        return {"slope": 0.0, "percent_change": 0.0, "direction": "flat"}
    # x = 0..n-1
    xs = list(range(n))
    ys = values
    mean_x = statistics.mean(xs)
    mean_y = statistics.mean(ys)
    num = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(xs, ys))
    den = sum((xi - mean_x) ** 2 for xi in xs) or 1.0
    slope = num / den
    percent_change = ((ys[-1] - ys[0]) / max(1e-6, abs(ys[0]))) * 100.0 if ys[0] != 0 else (ys[-1] - ys[0]) * 100.0
    direction = "flat"
    if slope > 0.01:
        direction = "up"
    elif slope < -0.01:
        direction = "down"
    return {"slope": round(slope, 4), "percent_change": round(percent_change, 2), "direction": direction}

# ---------- warning builders ----------
def _weather_warnings(unit_id: str, weather_override: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    w = weather_override
    if w is None and get_current_weather:
        try:
            w = get_current_weather(int(unit_id))
        except Exception:
            w = {}
    w = w or {}

    temp = float(w.get("temperature", 0) or 0)
    forecast_48h = float(w.get("forecast_rain_48h", w.get("rainfall_next_48h", 0)) or 0)
    recent_rain = float(w.get("recent_rain_mm", 0) or 0)

    warnings = []
    # Heatwave
    if temp >= TEMPERATURE_HEATWAVE_THRESHOLD_C:
        warnings.append({
            "type": "weather",
            "subtype": "heatwave",
            "level": "high",
            "severity_score": min(100, int((temp - TEMPERATURE_HEATWAVE_THRESHOLD_C) * 5) + 70),
            "message": f"High temperatures expected: {temp}°C. Consider irrigation timing and heat-protective measures.",
            "data": {"temperature": temp, "generated_at": _now_iso()}
        })
    # Heavy rain / flood
    if forecast_48h >= HEAVY_RAIN_THRESHOLD_MM_48H or recent_rain >= 100:
        warnings.append({
            "type": "weather",
            "subtype": "heavy_rain",
            "level": "high",
            "severity_score": min(100, int(forecast_48h)),
            "message": f"Heavy rainfall forecast ({forecast_48h} mm) — risk of waterlogging and nutrient leaching.",
            "data": {"forecast_48h": forecast_48h, "recent_rain": recent_rain, "generated_at": _now_iso()}
        })
    # Drought streak detection (simple)
    if recent_rain < 1 and forecast_48h < 5:
        warnings.append({
            "type": "weather",
            "subtype": "dry_spell",
            "level": "medium",
            "severity_score": 50,
            "message": "Low recent rainfall and low forecast — monitor soil moisture and plan irrigation.",
            "data": {"recent_rain": recent_rain, "forecast_48h": forecast_48h, "generated_at": _now_iso()}
        })
    return warnings

def _operational_warnings(unit_id: str) -> List[Dict[str, Any]]:
    warnings = []
    # overdue tasks
    overdue = 0
    if count_overdue_tasks:
        try:
            overdue = int(count_overdue_tasks(int(unit_id)))
        except Exception:
            try:
                overdue = int(count_overdue_tasks(unit_id))
            except Exception:
                overdue = 0
    if overdue >= OVERDUE_TASKS_WARNING_COUNT:
        warnings.append({
            "type": "operational",
            "subtype": "overdue_tasks",
            "level": "high" if overdue >= (OVERDUE_TASKS_WARNING_COUNT * 3) else "medium",
            "severity_score": min(100, overdue * 10),
            "message": f"{overdue} overdue tasks — prioritize critical activities to avoid delays.",
            "data": {"overdue_count": overdue, "generated_at": _now_iso()}
        })

    # labour shortage detection
    if detect_labor_shortage:
        try:
            shortage = detect_labor_shortage(str(unit_id), stage="", area_acres=0.0)
            sh_hours = float(shortage.get("shortage_hours", 0) or 0)
            if sh_hours >= LABOR_SHORTAGE_HOURS_THRESHOLD:
                warnings.append({
                    "type": "operational",
                    "subtype": "labour_shortage",
                    "level": "medium" if sh_hours < (LABOR_SHORTAGE_HOURS_THRESHOLD * 2) else "high",
                    "severity_score": min(100, int((sh_hours / (LABOR_SHORTAGE_HOURS_THRESHOLD * 2)) * 100)),
                    "message": f"Detected labour shortage of ~{sh_hours} hours — may delay upcoming tasks.",
                    "data": {"shortage_hours": sh_hours, "generated_at": _now_iso()}
                })
        except Exception:
            pass

    return warnings

def _crop_health_warnings(unit_id: str, health_score_override: Optional[float] = None, symptom_text: Optional[str] = None) -> List[Dict[str, Any]]:
    warnings = []
    # health decline detection via history: compare last two health signals in risk history if present
    hist = _get_history(unit_id)
    health_points = [h.get("components", {}).get("health", {}).get("score") for h in hist if h.get("components", {}).get("health", {}).get("score") is not None]
    # use override if provided (adds as very recent)
    if health_score_override is not None:
        try:
            health_points.append(float(health_score_override))
        except Exception:
            pass
    if len(health_points) >= 2:
        first = health_points[0]
        last = health_points[-1]
        if first is not None and last is not None:
            # percent drop relative to first
            if first > 0:
                pct_drop = ((first - last) / first) * 100.0
                if pct_drop >= RAPID_HEALTH_DROP_PERCENT:
                    warnings.append({
                        "type": "crop_health",
                        "subtype": "rapid_decline",
                        "level": "high",
                        "severity_score": min(100, int(pct_drop)),
                        "message": f"Rapid crop health decline (~{round(pct_drop,1)}% drop) — urgent scouting recommended.",
                        "data": {"first_health": first, "last_health": last, "percent_drop": round(pct_drop,2), "generated_at": _now_iso()}
                    })

    # symptom-based triage severe flags
    if symptom_text and pest_triage:
        try:
            tri = pest_triage(symptom_text)
            if tri.get("results"):
                warnings.append({
                    "type": "crop_health",
                    "subtype": "pest_alert",
                    "level": "high",
                    "severity_score": 70,
                    "message": "Pest/disease indicators detected from symptoms — inspect field immediately.",
                    "data": {"triage": tri, "generated_at": _now_iso()}
                })
            elif tri.get("matches"):
                warnings.append({
                    "type": "crop_health",
                    "subtype": "possible_pest",
                    "level": "medium",
                    "severity_score": 40,
                    "message": "Possible pest matches found; follow-up scouting advised.",
                    "data": {"triage": tri, "generated_at": _now_iso()}
                })
        except Exception:
            pass

    return warnings

def _stage_warnings(unit_id: str, crop: Optional[str], stage: Optional[str], extra: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    warnings = []
    if crop and stage and stage_practices:
        try:
            sp = stage_practices(crop, stage)
            practices = sp.get("practices", []) if isinstance(sp, dict) else []
            # If many practices exist and urgent ones not done (heuristic), raise medium warning
            if practices:
                warnings.append({
                    "type": "stage",
                    "subtype": "stage_guidance",
                    "level": "medium",
                    "severity_score": min(100, 30 + len(practices) * 5),
                    "message": f"Stage '{stage}' for {crop} has recommended practices — ensure critical ones are scheduled.",
                    "data": {"practices_count": len(practices), "practices": practices, "generated_at": _now_iso()}
                })
        except Exception:
            pass
    return warnings

# ---------- consolidate and trend-driven escalation ----------
def consolidate_warnings(unit_id: str, crop: Optional[str] = None, stage: Optional[str] = None,
                         health_score_override: Optional[float] = None, symptom_text: Optional[str] = None,
                         weather_override: Optional[Dict[str, Any]] = None, auto_notify: bool = False) -> Dict[str, Any]:
    """
    Compute warnings from components, perform trend analysis, store snapshot and optionally send notifications.
    Returns dict with warnings list, snapshot, and history summary.
    """
    # 1. compute risk snapshot (prefer compute_risk_score if exists)
    if compute_risk_score:
        try:
            snapshot = compute_risk_score(unit_id=int(unit_id) if unit_id is not None else None,
                                          health_score=health_score_override,
                                          symptom_text=symptom_text,
                                          weather_override=weather_override,
                                          crop=crop,
                                          stage=stage)
        except Exception:
            snapshot = {"unit_id": unit_id, "risk_score": None, "components": {}, "generated_at": _now_iso()}
    else:
        # fallback minimal snapshot
        snapshot = {"unit_id": unit_id, "risk_score": None, "components": {}, "generated_at": _now_iso()}

    # 2. individual warnings
    try:
        weather_ws = _weather_warnings(unit_id, weather_override)
    except Exception:
        weather_ws = []
    try:
        operational_ws = _operational_warnings(unit_id)
    except Exception:
        operational_ws = []
    try:
        crop_ws = _crop_health_warnings(unit_id, health_score_override=health_score_override, symptom_text=symptom_text)
    except Exception:
        crop_ws = []
    try:
        stage_ws = _stage_warnings(unit_id, crop, stage)
    except Exception:
        stage_ws = []

    all_warnings = weather_ws + operational_ws + crop_ws + stage_ws

    # 3. trend detection on snapshot risk history (if present)
    hist = _get_history(unit_id)
    # build risk scores series for trend analysis; use snapshot.risk_score if available
    series = []
    for h in hist:
        sc = h.get("risk_score")
        if sc is not None:
            series.append(float(sc))
    if snapshot.get("risk_score") is not None:
        series.append(float(snapshot.get("risk_score")))
    trend = _compute_trend(series) if len(series) >= TREND_MIN_POINTS else {"slope": 0.0, "percent_change": 0.0, "direction": "flat"}

    # if trend shows rapidly rising risk, escalate with an aggregated warning
    if trend.get("direction") == "up" and trend.get("percent_change", 0) >= 10.0:
        all_warnings.append({
            "type": "trend",
            "subtype": "rising_risk",
            "level": "high",
            "severity_score": min(100, int(abs(trend.get("percent_change", 0)))),
            "message": f"Risk trending up (~{trend.get('percent_change',0)}% increase) — take proactive measures.",
            "data": {"trend": trend, "generated_at": _now_iso()}
        })
    elif trend.get("direction") == "up" and trend.get("percent_change", 0) >= 5.0:
        all_warnings.append({
            "type": "trend",
            "subtype": "rising_risk",
            "level": "medium",
            "severity_score": min(100, int(abs(trend.get("percent_change", 0)))),
            "message": f"Risk increasing (~{trend.get('percent_change',0)}% change) — monitor and act if persists.",
            "data": {"trend": trend, "generated_at": _now_iso()}
        })

    # 4. deduplicate by type+subtype (keep highest severity)
    dedup_map: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for w in all_warnings:
        key = (w.get("type"), w.get("subtype"))
        existing = dedup_map.get(key)
        if not existing or w.get("severity_score", 0) > existing.get("severity_score", 0):
            dedup_map[key] = w
    consolidated = list(dedup_map.values())

    # 5. store snapshot + warnings into history and last warnings
    snapshot_record = {
        "timestamp": _now_iso(),
        "risk_score": snapshot.get("risk_score"),
        "components": snapshot.get("components"),
        "warnings_count": len(consolidated)
    }
    _push_history(unit_id, snapshot_record)
    with _lock:
        _LAST_WARNINGS[unit_id] = consolidated

    # 6. Optional notifications for high severity warnings
    if auto_notify and immediate_send:
        # prepare compact message
        high_warnings = [w for w in consolidated if w.get("level") in ("high",)]
        if high_warnings:
            title = f"Early Warning: {len(high_warnings)} high alerts for unit {unit_id}"
            body_lines = []
            for w in high_warnings:
                body_lines.append(f"- [{w.get('type')}/{w.get('subtype')}] {w.get('message')}")
            body = "\n".join(body_lines)
            try:
                # for demo: send to farmer_id == unit_id (string) via in-app
                immediate_send(str(unit_id), title, body, channels=[ "in_app" ])
            except Exception:
                # best-effort only
                pass

    return {"unit_id": unit_id, "warnings": consolidated, "trend": trend, "snapshot": snapshot_record, "generated_at": _now_iso()}

# ---------- public getters ----------
def get_last_warnings(unit_id: str) -> List[Dict[str, Any]]:
    with _lock:
        return list(_LAST_WARNINGS.get(unit_id, []))

def get_history(unit_id: str) -> List[Dict[str, Any]]:
    return _get_history(unit_id)

def run_check(unit_id: str, crop: Optional[str] = None, stage: Optional[str] = None,
              health_score_override: Optional[float] = None, symptom_text: Optional[str] = None,
              weather_override: Optional[Dict[str, Any]] = None, auto_notify: bool = False) -> Dict[str, Any]:
    """
    Public function to run a full early-warning check for a unit now.
    """
    return consolidate_warnings(unit_id=unit_id, crop=crop, stage=stage,
                                health_score_override=health_score_override, symptom_text=symptom_text,
                                weather_override=weather_override, auto_notify=auto_notify)
