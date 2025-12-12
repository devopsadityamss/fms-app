# backend/app/services/farmer/utilization_heatmap_service.py

from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, Any, List, Optional
import math

# Reuse internal stores & helpers from other services (we import internals where needed)
from app.services.farmer.equipment_service import (
    _equipment_store,
    _store_lock,
    list_task_assignments,   # returns assignments stored by smart_assign_tasks
    equipment_workload_pressure_score,
    compute_equipment_operating_cost
)
from app.services.farmer.operator_behavior_service import (
    _operator_usage_log
)
from app.services.farmer.fuel_analytics_service import (
    _fuel_logs
)

# ---------------------------------------------------------
# Utility: parse ISO datetimes safely
# ---------------------------------------------------------
def _parse_iso(dt_str: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(dt_str)
    except Exception:
        try:
            return datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S")
        except Exception:
            return None


# ---------------------------------------------------------
# Core: build event list per equipment from multiple sources
# sources:
#  - _task_assignments (assignment records with start_iso/end_iso and estimated_hours)
#  - _operator_usage_log (entries with logged_at and hours)
#  - _fuel_logs (refill/consumption timestamps, weaker signal)
# Each event is normalized to: { start: datetime, end: datetime, hours: float }
# ---------------------------------------------------------
def _gather_usage_events(equipment_id: str, lookback_days: int = 90) -> List[Dict[str, Any]]:
    cutoff = datetime.utcnow() - timedelta(days=lookback_days)
    events: List[Dict[str, Any]] = []

    # 1) from assignments
    try:
        assignments = list_task_assignments()  # returns {"count":, "assignments":[...]}
        for rec in assignments.get("assignments", []):
            if rec.get("equipment_id") != equipment_id:
                continue
            # parse start/end
            s = _parse_iso(rec.get("start_iso"))
            e = _parse_iso(rec.get("end_iso"))
            est_hours = rec.get("estimated_hours") or 0
            if not s:
                continue
            if not e and est_hours:
                e = s + timedelta(hours=float(est_hours))
            if not e:
                # fallback to same day 8 hours
                e = s + timedelta(hours=8)
            if e < cutoff:
                continue
            duration_hours = max(0.1, (e - s).total_seconds() / 3600.0)
            events.append({"start": s, "end": e, "hours": duration_hours, "source": "assignment"})
    except Exception:
        # ignore errors and continue with other sources
        pass

    # 2) from operator usage logs
    try:
        for rec in list(_operator_usage_log):
            if rec.get("equipment_id") != equipment_id:
                continue
            logged_at = _parse_iso(rec.get("logged_at"))
            hours = float(rec.get("hours", 0) or 0)
            if not logged_at:
                continue
            if logged_at < cutoff:
                continue
            # we don't have an end timestamp; assume logged_at -> logged_at + hours
            end = logged_at + timedelta(hours=hours) if hours > 0 else logged_at + timedelta(hours=1)
            events.append({"start": logged_at, "end": end, "hours": hours or ((end - logged_at).total_seconds()/3600.0), "source": "operator_usage"})
    except Exception:
        pass

    # 3) fuel logs (use refill/consumption timestamps as lightweight proxies)
    try:
        for rec in list(_fuel_logs):
            if rec.get("equipment_id") != equipment_id:
                continue
            ts = _parse_iso(rec.get("timestamp"))
            if not ts or ts < cutoff:
                continue
            # assume a short event around timestamp (0.5 hour)
            events.append({"start": ts, "end": ts + timedelta(minutes=30), "hours": 0.5, "source": "fuel_log"})
    except Exception:
        pass

    # If no detailed events, fall back to compute_equipment_operating_cost total_hours -> create synthetic monthly-distributed events
    if not events:
        try:
            cost = compute_equipment_operating_cost(equipment_id) or {}
            total_hours = cost.get("total_hours", 0) or 0
            if total_hours > 0:
                # distribute across lookback_days evenly as daily events of 4 hours until hours exhausted
                hours_left = total_hours
                day = datetime.utcnow()
                while hours_left > 0 and (datetime.utcnow() - day).days <= lookback_days:
                    h = min(8, hours_left)
                    start = day - timedelta(days=(datetime.utcnow() - day).days)
                    start = datetime.utcnow() - timedelta(days=(datetime.utcnow() - day).days)
                    # schedule backwards uniformly
                    event_start = datetime.utcnow() - timedelta(days=(datetime.utcnow() - day).days)
                    events.append({"start": event_start, "end": event_start + timedelta(hours=h), "hours": h, "source": "synthetic_cost"})
                    hours_left -= h
                    day = day - timedelta(days=1)
        except Exception:
            pass

    return events


# ---------------------------------------------------------
# Build hourly and weekday heatmaps from events
# ---------------------------------------------------------
def generate_utilization_heatmap(equipment_id: str, lookback_days: int = 90) -> Optional[Dict[str, Any]]:
    """
    Returns:
      {
        equipment_id,
        hourly: [24 values total_hours],
        weekday: [7 values Mon(0) .. Sun(6) total_hours],
        monthly: { 'YYYY-MM': total_hours },
        total_hours,
        generated_at
      }
    """
    with _store_lock:
        if equipment_id not in _equipment_store:
            return None

    events = _gather_usage_events(equipment_id, lookback_days=lookback_days)

    # initialize buckets
    hourly = [0.0 for _ in range(24)]
    weekday = [0.0 for _ in range(7)]
    monthly: Dict[str, float] = {}

    total_hours = 0.0
    for ev in events:
        s: datetime = ev["start"]
        e: datetime = ev["end"]
        hours = ev.get("hours", max(0.1, (e - s).total_seconds() / 3600.0))

        total_hours += hours

        # distribute across hours by splitting into 15-min slices for accuracy
        slice_minutes = 15
        slice_duration = timedelta(minutes=slice_minutes)
        cur = s
        while cur < e:
            next_slice = min(e, cur + slice_duration)
            slice_hours = (next_slice - cur).total_seconds() / 3600.0
            # hour index and weekday index
            hour_idx = cur.hour
            weekday_idx = cur.weekday()
            hourly[hour_idx] += slice_hours
            weekday[weekday_idx] += slice_hours
            month_key = f"{cur.year}-{cur.month:02d}"
            monthly[month_key] = monthly.get(month_key, 0.0) + slice_hours
            cur = next_slice

    # normalize to totals and optionally compute percentages
    hourly_pct = []
    weekday_pct = []
    for h in hourly:
        hourly_pct.append(round((h / total_hours * 100) if total_hours > 0 else 0.0, 2))
    for w in weekday:
        weekday_pct.append(round((w / total_hours * 100) if total_hours > 0 else 0.0, 2))

    # also include pressure score and cost summary for augmentation
    pressure = equipment_workload_pressure_score(equipment_id) or {}
    cost = compute_equipment_operating_cost(equipment_id) or {}

    return {
        "equipment_id": equipment_id,
        "hourly_hours": [round(x, 2) for x in hourly],
        "hourly_pct": hourly_pct,
        "weekday_hours": [round(x, 2) for x in weekday],
        "weekday_pct": weekday_pct,
        "monthly_hours": {k: round(v, 2) for k, v in sorted(monthly.items())},
        "total_hours": round(total_hours, 2),
        "pressure_score": pressure.get("pressure_score"),
        "cost_summary": cost,
        "generated_at": datetime.utcnow().isoformat()
    }


# ---------------------------------------------------------
# Fleet-level aggregation
# ---------------------------------------------------------
def fleet_utilization_heatmap(lookback_days: int = 90) -> Dict[str, Any]:
    """
    Aggregates hourly / weekday utilization across entire fleet,
    returning top offenders and an aggregated heatmap.
    """
    with _store_lock:
        eq_ids = list(_equipment_store.keys())

    agg_hourly = [0.0 for _ in range(24)]
    agg_weekday = [0.0 for _ in range(7)]
    per_equipment = []

    for eid in eq_ids:
        res = generate_utilization_heatmap(eid, lookback_days=lookback_days)
        if not res:
            continue
        per_equipment.append({
            "equipment_id": eid,
            "total_hours": res.get("total_hours", 0),
            "pressure_score": res.get("pressure_score")
        })
        for i in range(24):
            agg_hourly[i] += res["hourly_hours"][i]
        for j in range(7):
            agg_weekday[j] += res["weekday_hours"][j]

    total = sum(agg_hourly) or 1.0
    hourly_pct = [round((h / total * 100), 2) for h in agg_hourly]
    weekday_total = sum(agg_weekday) or 1.0
    weekday_pct = [round((w / weekday_total * 100), 2) for w in agg_weekday]

    # sort equipments by total_hours desc
    per_equipment.sort(key=lambda x: x["total_hours"], reverse=True)

    return {
        "fleet_hourly_hours": [round(x, 2) for x in agg_hourly],
        "fleet_hourly_pct": hourly_pct,
        "fleet_weekday_hours": [round(x, 2) for x in agg_weekday],
        "fleet_weekday_pct": weekday_pct,
        "top_equipments_by_hours": per_equipment[:50],
        "generated_at": datetime.utcnow().isoformat()
    }
