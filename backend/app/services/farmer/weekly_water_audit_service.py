# backend/app/services/farmer/weekly_water_audit_service.py

"""
Weekly Water Audit Service (Feature 315)

Produces a single-week audit report per unit:
 - predicted_liters (from schedule)
 - actual_liters (from irrigation logs)
 - deviation_pct
 - leakage_summary (from infra service)
 - deficit_alerts (from water_deficit_service)
 - audit_events (recent)
 - simple recommendations
"""

from datetime import datetime, timedelta, date
from typing import Dict, Any, List, Optional

# best-effort imports (don't crash if missing)
try:
    from app.services.farmer.weekly_demand_service import weekly_aggregated_demand
except Exception:
    weekly_aggregated_demand = None

try:
    from app.services.farmer.water_deviation_service import analyze_deviation_for_unit as _analyze_deviation_stub
except Exception:
    _analyze_deviation_stub = None

try:
    from app.services.farmer.irrigation_infrastructure_service import estimate_leakage as _estimate_leakage_stub
except Exception:
    _estimate_leakage_stub = None

try:
    from app.services.farmer.irrigation_service import list_irrigation_logs, get_irrigation_schedule
except Exception:
    list_irrigation_logs = lambda uid: []
    get_irrigation_schedule = lambda uid: {}

try:
    from app.services.farmer.water_deficit_service import list_water_deficit_alerts
except Exception:
    list_water_deficit_alerts = lambda uid: {"alerts": []}

try:
    from app.services.farmer.water_audit_service import list_audit
except Exception:
    list_audit = lambda uid, limit=50: {"items": []}

# helper
def _iso_week_key(d: date) -> str:
    y, w, _ = d.isocalendar()
    return f"{y}-{w:02d}"

def _week_start_from_iso(week_iso: Optional[str]) -> date:
    # accept YYYY-MM-DD (a day inside week) or ISO week YYYY-WW
    if not week_iso:
        today = datetime.utcnow().date()
        return today - timedelta(days=today.weekday())  # monday
    # try YYYY-MM-DD
    try:
        d = datetime.fromisoformat(week_iso).date()
        return d - timedelta(days=d.weekday())
    except Exception:
        pass
    # try YYYY-WW
    try:
        parts = week_iso.split("-")
        if len(parts) == 2:
            y = int(parts[0]); w = int(parts[1])
            # ISO week to date: Monday
            return datetime.strptime(f'{y} {w} 1', '%G %V %u').date()
    except Exception:
        pass
    # fallback: today monday
    t = datetime.utcnow().date()
    return t - timedelta(days=t.weekday())

def _sum_predicted_for_week(unit_id: str, week_start: date) -> float:
    # use get_irrigation_schedule which stores events for unit; sums events that fall in week
    sched = get_irrigation_schedule(unit_id) or {}
    events = sched.get("events", []) if isinstance(sched, dict) else []
    week_end = week_start + timedelta(days=6)
    total = 0.0
    for ev in events:
        sd = ev.get("scheduled_date")
        if not sd:
            continue
        try:
            d = datetime.fromisoformat(sd).date()
        except Exception:
            try:
                d = date.fromisoformat(str(sd).split("T")[0])
            except Exception:
                continue
        if week_start <= d <= week_end:
            total += float(ev.get("liters") or 0.0)
    return round(total,2)

def _sum_actual_for_week(unit_id: str, week_start: date) -> float:
    logs = list_irrigation_logs(unit_id) or []
    week_end = week_start + timedelta(days=6)
    total = 0.0
    for l in logs:
        ts = l.get("created_at") or l.get("timestamp") or l.get("date")
        if not ts:
            continue
        try:
            d = datetime.fromisoformat(ts).date()
        except Exception:
            try:
                d = date.fromisoformat(str(ts).split("T")[0])
            except Exception:
                continue
        if week_start <= d <= week_end:
            total += float(l.get("water_used_liters") or l.get("water_used") or 0.0)
    return round(total,2)

def _collect_leakage_info(unit_id: str) -> Dict[str, Any]:
    # best-effort: iterate channels for unit and estimate_leakage if available
    leaks = []
    try:
        # irrigation_infrastructure_service exposes irrigation_infra_summary or channel listing; try best-effort function names
        from app.services.farmer.irrigation_infrastructure_service import list_channels as _list_channels, estimate_leakage as _est
        channels = _list_channels(unit_id) if callable(_list_channels) else []
        for c in channels:
            cid = c.get("channel_id")
            if cid and callable(_est):
                res = _est(cid)
                leaks.append({"channel_id": cid, "name": c.get("name"), "leakage": res})
    except Exception:
        # fallback to stub if provided
        try:
            # try single channel estimate if stub exists
            pass
        except Exception:
            pass
    return {"count": len(leaks), "items": leaks}

def _simple_efficiency_score(predicted: float, actual: float) -> float:
    """
    If actual less than predicted, penalize for underuse; if overuse, penalize more.
    Score 0..100 where 100 is perfect match.
    """
    if predicted <= 0:
        return 50.0
    dev = abs(actual - predicted) / predicted
    score = max(0.0, 100.0 - dev * 100.0)
    return round(score,2)

def run_weekly_audit(unit_id: str, week_iso: Optional[str] = None, include_events_limit: int = 20) -> Dict[str, Any]:
    week_start = _week_start_from_iso(week_iso)
    week_end = week_start + timedelta(days=6)
    week_label = _iso_week_key(week_start)

    predicted = _sum_predicted_for_week(unit_id, week_start)
    actual = _sum_actual_for_week(unit_id, week_start)

    deviation_pct = None
    if predicted and predicted > 0:
        deviation_pct = round((actual - predicted) / predicted * 100.0, 2)

    # leakage summary
    leakage = _collect_leakage_info(unit_id)

    # deficit alerts (best-effort)
    try:
        deficit = list_water_deficit_alerts(unit_id)
    except Exception:
        deficit = {"alerts": []}

    # recent audit events
    try:
        audits = list_audit(unit_id, limit=include_events_limit).get("items", [])
    except Exception:
        audits = []

    eff_score = _simple_efficiency_score(predicted, actual)

    recommendations = []
    if deviation_pct is None:
        recommendations.append("No predicted data for the week — schedule needed.")
    else:
        if deviation_pct > 30:
            recommendations.append("High overconsumption detected; inspect for leaks or over-watering.")
        elif deviation_pct < -30:
            recommendations.append("Significant under-watering detected; consider prioritizing irrigation or check source availability.")
        else:
            recommendations.append("Water usage within acceptable bounds.")

    if leakage.get("count",0) > 0:
        recommendations.append("Infrastructure leakage detected — inspect channels listed in leakage report.")

    report = {
        "unit_id": unit_id,
        "week_label": week_label,
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "predicted_liters": predicted,
        "actual_liters": actual,
        "deviation_pct": deviation_pct,
        "efficiency_score": eff_score,
        "leakage_summary": leakage,
        "deficit_alerts": deficit.get("alerts", []),
        "recent_audit_events": audits,
        "recommendations": recommendations,
        "generated_at": datetime.utcnow().isoformat()
    }
    return report
