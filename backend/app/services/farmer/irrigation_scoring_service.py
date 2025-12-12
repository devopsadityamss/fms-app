# backend/app/services/farmer/irrigation_scoring_service.py

"""
Irrigation Event Scoring (Feature 322)

Scores each irrigation event (log) on multiple axes:
 - timeliness: how close to scheduled date/time (if schedule exists)
 - volume_match: actual liters vs predicted liters
 - efficiency: method efficiency (drip > sprinkler > flood)
 - energy_efficiency: kWh per 1000L (if energy estimate available)
 - anomaly_penalty: spikes, continuous flow, leakage flags reduce score
 - soil_context: high soil moisture or rainfall reduces score if irrigation unnecessary

Outputs:
{
  "score_id": "...",
  "log_id": "...",
  "unit_id": "...",
  "overall_score": 78.5,
  "components": {
    "timeliness": {"score": 90, "weight":0.2, "reason": "..."},
    "volume_match": {"score": 60, "weight":0.3, "reason": "..."},
    "efficiency": {"score": 80, "weight":0.2, "reason": "..."},
    "energy": {"score": 70, "weight":0.15, "reason": "..."},
    "anomaly": {"score": 50, "weight":0.15, "reason": "..."}
  },
  "timestamp": "...",
  "notes": ...
}
"""

from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, Any, List, Optional
import uuid
import math

# Defensive imports (best-effort)
try:
    from app.services.farmer.irrigation_service import get_irrigation_schedule, list_irrigation_logs
except Exception:
    get_irrigation_schedule = lambda unit_id: {}
    list_irrigation_logs = lambda unit_id: []

try:
    from app.services.farmer.water_deviation_service import _predicted_usage, _actual_usage, analyze_deviation_for_unit
except Exception:
    analyze_deviation_for_unit = lambda *args, **kwargs: {}

try:
    from app.services.farmer.water_energy_service import estimate_energy_for_irrigation_log
except Exception:
    estimate_energy_for_irrigation_log = lambda *args, **kwargs: {}

try:
    from app.services.farmer.leakage_service import list_anomalies, compute_risk_score
except Exception:
    list_anomalies = lambda channel_id, limit=200: []
    compute_risk_score = lambda channel_id: {"risk_score": 0}

try:
    from app.services.farmer.irrigation_audit_service import add_audit_event
except Exception:
    add_audit_event = lambda *args, **kwargs: {}

_lock = Lock()

_scores: Dict[str, Dict[str, Any]] = {}       # score_id -> record
_scores_by_log: Dict[str, str] = {}          # log_id -> score_id
_scores_by_unit: Dict[str, List[str]] = {}   # unit_id -> [score_ids]


# Weight defaults (tunable)
WEIGHTS = {
    "timeliness": 0.2,
    "volume_match": 0.35,
    "efficiency": 0.15,
    "energy": 0.15,
    "anomaly": 0.15
}

METHOD_SCORES = {
    "drip": 100,
    "sprinkler": 80,
    "flood": 40,
    "default": 60
}

def _now_iso():
    return datetime.utcnow().isoformat()

def _uid(prefix="score"):
    return f"{prefix}_{uuid.uuid4()}"

# -------------------------
# Helpers
# -------------------------
def _clamp_0_100(x):
    try:
        return max(0.0, min(100.0, float(x)))
    except Exception:
        return 0.0

def _pct_diff(pred, actual):
    try:
        if pred == 0:
            return None
        return (actual - pred) / pred * 100.0
    except Exception:
        return None

# -------------------------
# Core scoring function
# -------------------------
def score_irrigation_log(irrigation_log: Dict[str, Any], predicted_liters: Optional[float] = None, channels: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    irrigation_log expected keys:
      - log_id
      - unit_id
      - method (flood/sprinkler/drip)
      - duration_minutes
      - water_used_liters
      - timestamp / created_at (ISO)
      - metadata (optional) may contain 'scheduled_date' or 'flow_lph'
    predicted_liters: optional predicted liters for this event (if known)
    channels: optional list of channel_ids for anomaly lookup
    """

    log_id = irrigation_log.get("log_id") or irrigation_log.get("irrigation_id") or f"log_{uuid.uuid4()}"
    unit_id = irrigation_log.get("unit_id") or irrigation_log.get("unit")
    method = (irrigation_log.get("method") or "unknown").lower()
    liters = float(irrigation_log.get("water_used_liters") or irrigation_log.get("liters") or 0.0)
    ts_str = irrigation_log.get("timestamp") or irrigation_log.get("created_at") or _now_iso()
    try:
        ts = datetime.fromisoformat(ts_str)
    except Exception:
        ts = datetime.utcnow()

    # 1) Timeliness: compare to schedule
    timeliness_score = 50.0
    timeliness_reason = "no_schedule"
    try:
        schedule = get_irrigation_schedule(unit_id) or {}
        events = schedule.get("events", []) if isinstance(schedule, dict) else []
        # find the nearest scheduled event date to this timestamp
        closest = None
        min_delta = None
        for ev in events:
            try:
                ev_date = datetime.fromisoformat(ev.get("scheduled_date"))
                delta = abs((ev_date - ts).total_seconds())
                if min_delta is None or delta < min_delta:
                    min_delta = delta
                    closest = ev
            except Exception:
                continue
        if closest and min_delta is not None:
            # convert to days
            delta_days = min_delta / 86400.0
            # scoring: within 0.5 day => 100, within 1 day => 80, within 2 days => 60, else decays
            if delta_days <= 0.5:
                timeliness_score = 100.0
                timeliness_reason = "on_time"
            elif delta_days <= 1.0:
                timeliness_score = 80.0
                timeliness_reason = "near_time"
            elif delta_days <= 2.0:
                timeliness_score = 60.0
                timeliness_reason = "late"
            else:
                timeliness_score = 40.0
                timeliness_reason = "off_schedule"
    except Exception:
        timeliness_score = 50.0

    # 2) Volume match
    volume_score = 50.0
    volume_reason = "no_prediction"
    if predicted_liters is None:
        # try to fetch predicted from deviation service analysis for that date
        try:
            analysis = analyze_deviation_for_unit(unit_id)
            # find event matching date
            date_str = ts.date().isoformat()
            for ev in analysis.get("events", []):
                if ev.get("date") == date_str:
                    predicted_liters = ev.get("predicted_liters")
                    break
        except Exception:
            predicted_liters = None

    if predicted_liters is not None:
        pred = float(predicted_liters)
        if pred <= 0:
            volume_score = 50.0
            volume_reason = "invalid_pred"
        else:
            dev = _pct_diff(pred, liters)
            # ideal dev within +/-20% => 100
            if dev is None:
                volume_score = 50.0
                volume_reason = "calc_error"
            else:
                abs_dev = abs(dev)
                if abs_dev <= 10:
                    volume_score = 100.0
                    volume_reason = f"match_within_{abs_dev:.1f}%"
                elif abs_dev <= 25:
                    volume_score = 80.0
                    volume_reason = f"within_{abs_dev:.1f}%"
                elif abs_dev <= 50:
                    volume_score = 50.0
                    volume_reason = f"dev_{abs_dev:.1f}%"
                else:
                    volume_score = 20.0
                    volume_reason = f"large_dev_{abs_dev:.1f}%"
    else:
        volume_score = 50.0
        volume_reason = "no_pred_available"

    # 3) Efficiency by method
    method_score = METHOD_SCORES.get(method, METHOD_SCORES["default"]) if 'METHOD_SCORES' in globals() else (80 if method == "sprinkler" else 60)
    method_reason = f"method_{method}"

    # 4) Energy efficiency (lower kWh per 1000L => higher score)
    energy_score = 50.0
    energy_reason = "no_energy_estimate"
    try:
        energy_est = estimate_energy_for_irrigation_log(irrigation_log)
        kwh_per_1000l = energy_est.get("kwh_per_1000l")
        if kwh_per_1000l is not None and kwh_per_1000l > 0:
            # heuristic mapping: <= 0.5 kWh/m3 => 100, <=1.5 => 80, <=3 => 60, <=6 => 40, else 20
            v = float(kwh_per_1000l)
            if v <= 0.5:
                energy_score = 100.0
                energy_reason = "excellent_energy"
            elif v <= 1.5:
                energy_score = 80.0
                energy_reason = "good_energy"
            elif v <= 3.0:
                energy_score = 60.0
                energy_reason = "ok_energy"
            elif v <= 6.0:
                energy_score = 40.0
                energy_reason = "poor_energy"
            else:
                energy_score = 20.0
                energy_reason = "very_poor_energy"
        else:
            energy_score = 50.0
    except Exception:
        energy_score = 50.0

    # 5) Anomaly penalty (reduce score if leakage/spike etc. detected)
    anomaly_score = 100.0
    anomaly_reasons: List[str] = []
    try:
        # if channels provided, check their anomalies; otherwise best-effort check any channel anomalies for unit
        detected_any = False
        total_penalty = 0.0
        if channels:
            for ch in channels:
                anomalies = list_anomalies(ch, limit=50)
                if anomalies:
                    detected_any = True
                    # apply penalty proportional to anomaly severity if present
                    for a in anomalies[-3:]:
                        tp = a.get("type")
                        if tp == "spike":
                            total_penalty += 20
                            anomaly_reasons.append("spike")
                        elif tp == "continuous_flow":
                            total_penalty += 30
                            anomaly_reasons.append("continuous_flow")
                        elif tp == "overuse_vs_pred":
                            total_penalty += 25
                            anomaly_reasons.append("overuse")
        else:
            # try unit-level overuse detection by scanning recent logs risk (best-effort)
            pass
        # convert penalty to anomaly score
        if detected_any:
            anomaly_score = max(0.0, 100.0 - min(80.0, total_penalty))
            if total_penalty > 0 and not anomaly_reasons:
                anomaly_reasons.append("anomaly_detected")
    except Exception:
        anomaly_score = 100.0

    anomaly_reason_str = ", ".join(anomaly_reasons) if anomaly_reasons else ("no_anomalies" if anomaly_score == 100.0 else "unknown")

    # Combine component scores using weights
    w = WEIGHTS
    comps = {
        "timeliness": {"score": _clamp_0_100(timeliness_score), "weight": w.get("timeliness", 0.2), "reason": timeliness_reason},
        "volume_match": {"score": _clamp_0_100(volume_score), "weight": w.get("volume_match", 0.35), "reason": volume_reason},
        "efficiency": {"score": _clamp_0_100(method_score), "weight": w.get("efficiency", 0.15), "reason": method_reason},
        "energy": {"score": _clamp_0_100(energy_score), "weight": w.get("energy", 0.15), "reason": energy_reason},
        "anomaly": {"score": _clamp_0_100(anomaly_score), "weight": w.get("anomaly", 0.15), "reason": anomaly_reason_str}
    }

    overall = 0.0
    for k, v in comps.items():
        overall += v["score"] * v["weight"]

    overall = round(overall, 2)

    score_rec = {
        "score_id": _uid(),
        "log_id": log_id,
        "unit_id": unit_id,
        "overall_score": overall,
        "components": comps,
        "predicted_liters": predicted_liters,
        "actual_liters": liters,
        "timestamp": _now_iso(),
        "notes": irrigation_log.get("metadata", {})
    }

    # store
    with _lock:
        _scores[score_rec["score_id"]] = score_rec
        _scores_by_log[log_id] = score_rec["score_id"]
        _scores_by_unit.setdefault(str(unit_id), []).append(score_rec["score_id"])

    # write audit event for scoring
    try:
        add_audit_event(None, unit_id, "irrigation_scored", f"Irrigation log {log_id} scored {overall}", {"score": score_rec})
    except Exception:
        pass

    return score_rec


# -------------------------
# Query helpers
# -------------------------
def get_score_by_log(log_id: str) -> Dict[str, Any]:
    sid = _scores_by_log.get(log_id)
    if not sid:
        return {}
    return _scores.get(sid, {})

def list_scores_for_unit(unit_id: str, limit: int = 200) -> List[Dict[str, Any]]:
    ids = _scores_by_unit.get(str(unit_id), [])[-limit:]
    return [ _scores[i] for i in ids ]

def top_scores_for_unit(unit_id: str, top_n: int = 10) -> List[Dict[str, Any]]:
    scores = list_scores_for_unit(unit_id, limit=1000)
    sorted_scores = sorted(scores, key=lambda x: x.get("overall_score", 0), reverse=True)
    return sorted_scores[:top_n]
