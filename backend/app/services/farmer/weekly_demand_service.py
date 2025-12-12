# backend/app/services/farmer/weekly_demand_service.py

"""
Weekly Aggregated Demand Service (Feature 313)

- Aggregates scheduled irrigation (predicted) and actual irrigation logs per ISO week.
- Returns buckets for `weeks` number of past weeks (including current week).
- Deviation percent computed when prediction > 0.
"""

from datetime import datetime, timedelta, date
from typing import Dict, Any, List, Optional
import collections

# best-effort imports from existing services
try:
    from app.services.farmer.irrigation_service import get_irrigation_schedule, list_irrigation_logs
except Exception:
    # fallback stubs
    def get_irrigation_schedule(unit_id: str):
        return None
    def list_irrigation_logs(unit_id: str):
        return []

def _now_date() -> date:
    return datetime.utcnow().date()

def _iso_week_key(d: date) -> str:
    # ISO year-week as YYYY-WW
    y, w, _ = d.isocalendar()
    return f"{y}-{w:02d}"

def weekly_aggregated_demand(unit_id: str, weeks: int = 12, start_date_iso: Optional[str] = None) -> Dict[str, Any]:
    """
    Returns:
      {
        "unit_id": unit_id,
        "generated_at": ISO,
        "weeks": [
          { "week": "2025-11", "start_date": "2025-03-10", "end_date": "2025-03-16",
            "predicted_liters": 12345.0, "actual_liters": 11000.0, "deviation_pct": -10.88 }
        ]
      }
    """
    today = _now_date()
    if start_date_iso:
        try:
            today = datetime.fromisoformat(start_date_iso).date()
        except Exception:
            pass

    # build week ranges: current week and previous (weeks-1) weeks
    # find Monday of current week
    monday = today - timedelta(days=(today.weekday()))
    week_starts = [monday - timedelta(weeks=i) for i in range(0, weeks)]
    # we'll present oldest first
    week_starts = list(reversed(week_starts))

    # prepare maps
    predicted_map = collections.defaultdict(float)  # week_key -> liters
    actual_map = collections.defaultdict(float)

    # Collect predicted liters from irrigation schedule events
    try:
        sched = get_irrigation_schedule(unit_id)
        if sched and isinstance(sched, dict):
            events = sched.get("events", []) or []
            for ev in events:
                sd = ev.get("scheduled_date")
                liters = ev.get("liters") or 0.0
                if not sd:
                    continue
                try:
                    d = datetime.fromisoformat(sd).date()
                except Exception:
                    # if scheduled_date maybe date-only string, try fallback
                    try:
                        d = date.fromisoformat(sd.split("T")[0])
                    except Exception:
                        continue
                wk = _iso_week_key(d)
                predicted_map[wk] += float(liters)
    except Exception:
        # defensive: ignore errors
        pass

    # Collect actual liters from irrigation logs
    try:
        logs = list_irrigation_logs(unit_id) or []
        for l in logs:
            # try created_at or a date field
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
            liters = l.get("water_used_liters") or l.get("water_used") or 0.0
            try:
                actual_map[_iso_week_key(d)] += float(liters)
            except Exception:
                continue
    except Exception:
        pass

    weeks_out: List[Dict[str, Any]] = []
    for start in week_starts:
        wk_key = _iso_week_key(start)
        end = start + timedelta(days=6)
        pred = round(predicted_map.get(wk_key, 0.0), 2)
        act = round(actual_map.get(wk_key, 0.0), 2)
        deviation = None
        if pred and pred > 0:
            deviation = round((act - pred) / pred * 100.0, 2)
        weeks_out.append({
            "week": wk_key,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "predicted_liters": pred,
            "actual_liters": act,
            "deviation_pct": deviation
        })

    return {
        "unit_id": unit_id,
        "generated_at": datetime.utcnow().isoformat(),
        "weeks": weeks_out
    }
