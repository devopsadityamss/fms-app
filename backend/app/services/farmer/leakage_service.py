# backend/app/services/farmer/leakage_service.py

"""
Irrigation Leakage Detection & Risk Scoring (Feature 320)

Capabilities:
 - Register irrigation channels / pipes / zones
 - Ingest flow readings (timestamped liters or L/hr)
 - Ingest pressure or runtime hints (optional)
 - Simple detectors:
    * consumption_vs_prediction: compares predicted liters (from schedule/predictions) to actual usage
    * continuous_flow_detector: detects sustained flow outside scheduled irrigation windows
    * sudden_spike_detector: large unexpected increases in flow
 - Compute risk_score (0..100) with reason tags
 - List channels with their current risk, history, and recent detected anomalies
 - Best-effort integration hooks:
    - irrigation_audit_service.add_audit_event
    - notification_service.immediate_send
    - water_deviation_service.record_actual_usage / record_predicted_usage
"""

from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, Any, List, Optional
import uuid
import statistics

# defensive imports (best-effort)
try:
    from app.services.farmer.irrigation_service import list_irrigation_logs, get_irrigation_schedule
except Exception:
    list_irrigation_logs = lambda unit_id: []
    get_irrigation_schedule = lambda unit_id: {}

try:
    from app.services.farmer.water_deviation_service import record_actual_usage, record_predicted_usage, analyze_deviation_for_unit
except Exception:
    record_actual_usage = lambda *args, **kwargs: {}
    record_predicted_usage = lambda *args, **kwargs: {}
    analyze_deviation_for_unit = lambda *args, **kwargs: {}

try:
    from app.services.farmer.irrigation_audit_service import add_audit_event
except Exception:
    add_audit_event = lambda *args, **kwargs: {}

try:
    from app.services.farmer.notification_service import immediate_send
except Exception:
    immediate_send = None

_lock = Lock()

# stores
_channels: Dict[str, Dict[str, Any]] = {}            # channel_id -> metadata (unit_id, name, expected_flow_lph, etc)
_channels_by_unit: Dict[str, List[str]] = {}        # unit_id -> [channel_id]
_flow_readings: Dict[str, List[Dict[str, Any]]] = {} # channel_id -> list of { ts, flow_lph, liters, sensor_id }

_anomaly_history: Dict[str, List[Dict[str, Any]]] = {} # channel_id -> anomalies

# thresholds (tunable)
CONTINUOUS_FLOW_MIN_DURATION_MIN = 60   # minutes of continuous non-zero flow outside schedule considered suspicious
SPIKE_MULTIPLIER = 2.5                 # spike > 2.5x recent median flagged
OVERUSE_PCT_THRESHOLD = 30.0           # actual > predicted by this percent flagged

def _now_iso():
    return datetime.utcnow().isoformat()

def _uid(prefix="ch"):
    return f"{prefix}_{uuid.uuid4()}"

# -----------------------
# Channel registry
# -----------------------
def add_channel(unit_id: str, name: str, expected_flow_lph: Optional[float] = None, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    cid = _uid("channel")
    rec = {
        "channel_id": cid,
        "unit_id": unit_id,
        "name": name,
        "expected_flow_lph": float(expected_flow_lph) if expected_flow_lph is not None else None,
        "metadata": metadata or {},
        "created_at": _now_iso(),
        "updated_at": None
    }
    with _lock:
        _channels[cid] = rec
        _channels_by_unit.setdefault(unit_id, []).append(cid)
    return rec

def get_channel(channel_id: str) -> Dict[str, Any]:
    with _lock:
        return _channels.get(channel_id, {}).copy()

def list_channels(unit_id: str) -> List[Dict[str, Any]]:
    with _lock:
        ids = _channels_by_unit.get(unit_id, [])
        return [_channels[i].copy() for i in ids]

def update_channel(channel_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    with _lock:
        rec = _channels.get(channel_id)
        if not rec:
            return {"error": "not_found"}
        rec.update(updates)
        rec["updated_at"] = _now_iso()
        _channels[channel_id] = rec
        return rec.copy()

def delete_channel(channel_id: str) -> Dict[str, Any]:
    with _lock:
        rec = _channels.pop(channel_id, None)
        if not rec:
            return {"error": "not_found"}
        unit_id = rec.get("unit_id")
        if unit_id and unit_id in _channels_by_unit:
            _channels_by_unit[unit_id] = [i for i in _channels_by_unit[unit_id] if i != channel_id]
        _flow_readings.pop(channel_id, None)
        _anomaly_history.pop(channel_id, None)
    return {"status": "deleted", "channel_id": channel_id}

# -----------------------
# Ingest flow readings
# -----------------------
def record_flow_reading(channel_id: str, timestamp_iso: Optional[str] = None, flow_lph: Optional[float] = None, liters: Optional[float] = None, sensor_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    with _lock:
        if channel_id not in _channels:
            return {"error": "channel_not_found"}

    ts = timestamp_iso or _now_iso()
    rec = {
        "reading_id": f"fr_{uuid.uuid4()}",
        "channel_id": channel_id,
        "timestamp": ts,
        "flow_lph": float(flow_lph) if flow_lph is not None else None,
        "liters": float(liters) if liters is not None else None,
        "sensor_id": sensor_id,
        "metadata": metadata or {}
    }
    with _lock:
        _flow_readings.setdefault(channel_id, []).append(rec)

    # quick anomaly checks (non-blocking)
    try:
        _detect_spike(channel_id)
        _detect_continuous_flow(channel_id)
        _detect_overuse_vs_prediction(channel_id)
    except Exception:
        pass

    return rec

def list_flow_readings(channel_id: str, limit: int = 200) -> List[Dict[str, Any]]:
    with _lock:
        items = list(_flow_readings.get(channel_id, []))
    items_sorted = sorted(items, key=lambda x: x.get("timestamp",""), reverse=True)[:limit]
    return items_sorted

# -----------------------
# Anomaly detectors
# -----------------------
def _detect_spike(channel_id: str):
    readings = list_flow_readings(channel_id, limit=50)
    if len(readings) < 4:
        return None
    # use median of recent flows (excluding newest)
    flows = [r["flow_lph"] for r in readings if r.get("flow_lph") is not None]
    if len(flows) < 3:
        return None
    median_recent = statistics.median(flows[1:])  # exclude latest
    latest = flows[0]
    if median_recent <= 0:
        return None
    if latest > median_recent * SPIKE_MULTIPLIER:
        anomaly = {
            "type": "spike",
            "channel_id": channel_id,
            "timestamp": readings[0]["timestamp"],
            "latest_flow_lph": latest,
            "median_recent": median_recent,
            "score": min(100, round((latest/median_recent - 1) * 50, 2)),
            "message": f"Spike detected: latest {latest} L/h vs median {median_recent} L/h"
        }
        _record_anomaly(channel_id, anomaly)
        _maybe_alert(channel_id, anomaly)
        add_audit_event(None, None, "leakage_spike", f"Spike on channel {channel_id}", anomaly)
        return anomaly
    return None

def _detect_continuous_flow(channel_id: str):
    # find runs of non-zero flow outside scheduled events
    readings = list_flow_readings(channel_id, limit=500)
    if not readings:
        return None
    # convert to times and flows
    runs = []
    current_run = None
    for r in reversed(readings):  # oldest -> newest
        f = r.get("flow_lph") or 0.0
        ts = None
        try:
            ts = datetime.fromisoformat(r.get("timestamp"))
        except Exception:
            continue
        if f > 0 and current_run is None:
            current_run = {"start": ts, "end": ts}
        elif f > 0 and current_run is not None:
            current_run["end"] = ts
        elif f == 0 and current_run is not None:
            runs.append(current_run)
            current_run = None
    if current_run:
        runs.append(current_run)
    # examine last run
    if not runs:
        return None
    last = runs[-1]
    duration_min = (last["end"] - last["start"]).total_seconds() / 60.0
    # check if this run overlaps with a scheduled irrigation in the unit
    ch = get_channel(channel_id)
    unit_id = ch.get("unit_id")
    schedule = get_irrigation_schedule(unit_id) or {}
    events = schedule.get("events", []) if isinstance(schedule, dict) else []
    scheduled_cover = False
    for ev in events:
        try:
            sd = datetime.fromisoformat(ev.get("scheduled_date"))
            # consider event day match as acceptable (coarse)
            if sd.date() == last["start"].date() or sd.date() == last["end"].date():
                scheduled_cover = True
                break
        except Exception:
            continue
    if duration_min >= CONTINUOUS_FLOW_MIN_DURATION_MIN and not scheduled_cover:
        anomaly = {
            "type": "continuous_flow",
            "channel_id": channel_id,
            "start": last["start"].isoformat(),
            "end": last["end"].isoformat(),
            "duration_min": round(duration_min, 2),
            "message": f"Continuous flow for {round(duration_min,2)} minutes outside scheduled events"
        }
        _record_anomaly(channel_id, anomaly)
        _maybe_alert(channel_id, anomaly)
        add_audit_event(None, unit_id, "continuous_flow", f"Continuous flow on channel {channel_id}", anomaly)
        return anomaly
    return None

def _detect_overuse_vs_prediction(channel_id: str):
    # best-effort: aggregate flows for day and compare to any predicted record in water_deviation_service
    ch = get_channel(channel_id)
    unit_id = ch.get("unit_id")
    if not unit_id:
        return None
    # sum flow liters for latest day
    now = datetime.utcnow()
    day_start = (now - timedelta(days=1)).isoformat()
    readings = list_flow_readings(channel_id, limit=1000)
    total_liters = 0.0
    for r in readings:
        try:
            ts = datetime.fromisoformat(r.get("timestamp"))
        except Exception:
            continue
        if ts >= now - timedelta(days=1):
            if r.get("liters") is not None:
                total_liters += float(r.get("liters"))
            elif r.get("flow_lph") is not None:
                # approximate liters from flow * sampling interval unknown -> skip
                pass
    # now try to find predicted usage for unit for today (use analyze_deviation_for_unit if available)
    try:
        analysis = analyze_deviation_for_unit(unit_id)
        # find today record if any
        today = now.date().isoformat()
        preds = [p for p in analysis.get("events", []) if p.get("date") == today]
        if preds:
            pred = preds[0].get("predicted_liters", 0)
            if pred and total_liters > pred * (1 + OVERUSE_PCT_THRESHOLD/100.0):
                anomaly = {
                    "type": "overuse_vs_pred",
                    "channel_id": channel_id,
                    "date": today,
                    "predicted_liters": pred,
                    "actual_liters": total_liters,
                    "deviation_pct": round((total_liters - pred) / pred * 100.0, 2),
                    "message": f"Actual today {total_liters} L > predicted {pred} L by {round((total_liters/pred-1)*100,2)}%"
                }
                _record_anomaly(channel_id, anomaly)
                _maybe_alert(channel_id, anomaly)
                add_audit_event(None, unit_id, "overuse_detected", f"Overuse on channel {channel_id}", anomaly)
                return anomaly
    except Exception:
        pass
    return None

def _record_anomaly(channel_id: str, anomaly: Dict[str, Any]):
    with _lock:
        _anomaly_history.setdefault(channel_id, []).append({"detected_at": _now_iso(), **anomaly})

def list_anomalies(channel_id: str, limit: int = 200) -> List[Dict[str, Any]]:
    with _lock:
        return list(_anomaly_history.get(channel_id, []))[-limit:]

# -----------------------
# Risk scoring
# -----------------------
def compute_risk_score(channel_id: str) -> Dict[str, Any]:
    """
    Compute a composite risk score using:
     - recent spike anomalies
     - continuous flow anomalies (duration)
     - overuse % relative to predicted
     - expected_flow mismatch
    Returns structure with score 0..100 and contributing reasons.
    """
    ch = get_channel(channel_id)
    if not ch:
        return {"error": "channel_not_found"}
    anomalies = list_anomalies(channel_id, limit=50)
    score = 0.0
    reasons = []
    # weight anomalies
    for a in anomalies[-5:]:
        t = a.get("type")
        if t == "spike":
            score += a.get("score", 20) * 0.6
            reasons.append(f"spike:{a.get('score')}")
        elif t == "continuous_flow":
            score += min(40, a.get("duration_min", 60) / 60.0 * 20)
            reasons.append(f"continuous:{a.get('duration_min')}")
        elif t == "overuse_vs_pred":
            score += min(50, a.get("deviation_pct", 0) * 0.5)
            reasons.append(f"overuse:{a.get('deviation_pct')}")
    # expected vs actual flow comparison (if expected_flow_lph exists)
    expected = ch.get("expected_flow_lph")
    recent = list_flow_readings(channel_id, limit=10)
    flows = [r.get("flow_lph") for r in recent if r.get("flow_lph") is not None]
    if expected and flows:
        avg = statistics.mean(flows)
        if avg > expected * 1.3:
            score += min(30, (avg/expected - 1) * 50)
            reasons.append(f"avg_vs_expected:{round(avg,2)}/{expected}")
    # normalize
    score = max(0.0, min(100.0, score))
    return {"channel_id": channel_id, "risk_score": round(score,2), "reasons": reasons, "anomaly_count": len(anomalies), "generated_at": _now_iso()}

# -----------------------
# Alerts
# -----------------------
def _maybe_alert(channel_id: str, anomaly: Dict[str, Any]):
    # best-effort: send in-app notification and audit
    ch = get_channel(channel_id)
    unit_id = ch.get("unit_id")
    farmer_id = None
    try:
        farmer_id = ch.get("metadata",{}).get("farmer_id") or ch.get("metadata",{}).get("owner_id")
    except Exception:
        farmer_id = None
    # write audit
    try:
        add_audit_event(farmer_id, unit_id, "leak_anomaly", anomaly.get("message", ""), anomaly)
    except Exception:
        pass
    # notify farmer (in-app)
    try:
        if immediate_send and farmer_id:
            title = f"Leakage alert — {ch.get('name')}"
            body = anomaly.get("message", "")
            immediate_send(str(farmer_id), title, body, channels=["in_app"])
    except Exception:
        pass

# -----------------------
# Channel summary
# -----------------------
def channel_summary(channel_id: str) -> Dict[str, Any]:
    ch = get_channel(channel_id)
    if not ch:
        return {"error": "channel_not_found"}
    anomalies = list_anomalies(channel_id, limit=50)
    risk = compute_risk_score(channel_id)
    recent = list_flow_readings(channel_id, limit=10)
    return {
        "channel": ch,
        "recent_readings": recent,
        "anomalies": anomalies,
        "risk": risk
    }

def unit_leakage_overview(unit_id: str) -> Dict[str, Any]:
    chans = list_channels(unit_id)
    out = []
    for c in chans:
        out.append(channel_summary(c.get("channel_id")))
    return {"unit_id": unit_id, "channels": out, "generated_at": _now_iso()}
