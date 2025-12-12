# backend/app/services/farmer/timeline_service.py

from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional
import itertools

# Best-effort imports of in-memory stores / helpers
try:
    from app.services.farmer.unit_service import _unit_store
except Exception:
    _unit_store = {}

try:
    from app.services.farmer.season_calendar_service import _calendar_store
except Exception:
    _calendar_store = {}

try:
    from app.services.farmer.task_service import _task_templates_store
except Exception:
    _task_templates_store = {}

try:
    from app.services.farmer.risk_alerts_service import _alerts_store as _risk_alerts_store
except Exception:
    _risk_alerts_store = {}

try:
    from app.services.farmer.financial_ledger_service import _ledger_store
except Exception:
    _ledger_store = []

try:
    from app.services.farmer.irrigation_service import _irrigation_schedule_store
except Exception:
    _irrigation_schedule_store = {}

try:
    from app.services.farmer.notification_service import _history as _notification_history
except Exception:
    _notification_history = {}

try:
    from app.services.farmer.recommendation_engine_service import generate_recommendations_for_unit
except Exception:
    generate_recommendations_for_unit = None


# Helper to normalize timestamps (returns ISO string)
def _to_iso(dt: Optional[datetime]) -> str:
    if not dt:
        return datetime.utcnow().isoformat()
    if isinstance(dt, str):
        try:
            # if already iso-compatible
            _ = datetime.fromisoformat(dt)
            return dt
        except Exception:
            try:
                # try parsing common formats
                return datetime.fromisoformat(dt)
            except Exception:
                return datetime.utcnow().isoformat()
    return dt.isoformat()


def _parse_iso_date(d: Optional[str]) -> Optional[date]:
    if not d:
        return None
    try:
        return datetime.fromisoformat(d).date()
    except Exception:
        try:
            return datetime.strptime(d, "%Y-%m-%d").date()
        except Exception:
            return None


def _make_event(timestamp_iso: str, kind: str, title: str, details: Dict[str, Any], source: str, unit_id: Optional[str] = None) -> Dict[str, Any]:
    return {
        "timestamp": timestamp_iso,
        "kind": kind,            # e.g., "task", "alert", "irrigation", "ledger", "notification", "recommendation"
        "title": title,
        "details": details,
        "source": source,
        "unit_id": unit_id
    }


def _gather_calendar_events_for_unit(unit_id: str) -> List[Dict[str, Any]]:
    events = []
    cal = _calendar_store.get(unit_id) or {}
    for entry in cal.get("entries", []) if cal else []:
        ts = entry.get("scheduled_start_iso") or entry.get("scheduled_end_iso") or cal.get("season_start_date_iso")
        # fallback to generated_at if none
        ts = ts or _to_iso(datetime.utcnow())
        title = f"Task: {entry.get('task_name')}"
        details = {
            "stage": entry.get("stage_name"),
            "task_id": entry.get("task_id"),
            "scheduled_start": entry.get("scheduled_start_iso"),
            "scheduled_end": entry.get("scheduled_end_iso")
        }
        events.append(_make_event(ts, "task", title, details, "calendar", unit_id=unit_id))
    return events


def _gather_alert_events_for_unit(unit_id: str) -> List[Dict[str, Any]]:
    events = []
    for aid, a in (_risk_alerts_store or {}).items():
        if a.get("unit_id") != unit_id:
            continue
        ts = a.get("created_at") or a.get("generated_at") or _to_iso(datetime.utcnow())
        title = f"Alert: {a.get('kind') or a.get('message')}"
        details = {"severity": a.get("severity"), "evidence": a.get("evidence"), "alert_id": aid}
        events.append(_make_event(ts, "alert", title, details, "risk_alerts", unit_id=unit_id))
    return events


def _gather_irrigation_events_for_unit(unit_id: str) -> List[Dict[str, Any]]:
    events = []
    sch = _irrigation_schedule_store.get(unit_id) or {}
    for ev in sch.get("events", []) if sch else []:
        ts = ev.get("scheduled_date") or ev.get("computed_at") or _to_iso(datetime.utcnow())
        title = f"Irrigation scheduled: {ev.get('apply_mm')} mm"
        details = {"apply_mm": ev.get("apply_mm"), "liters": ev.get("liters"), "duration_hours": ev.get("duration_hours"), "priority": ev.get("priority")}
        events.append(_make_event(ts, "irrigation", title, details, "irrigation", unit_id=unit_id))
    return events


def _gather_ledger_events_for_unit(unit_id: str) -> List[Dict[str, Any]]:
    events = []
    for e in (_ledger_store or []):
        if unit_id and e.get("unit_id") != unit_id:
            continue
        ts = e.get("created_at") or e.get("date") or _to_iso(datetime.utcnow())
        title = f"Ledger: {e.get('type').title()} {e.get('category')} {e.get('amount')}"
        details = {"entry_id": e.get("entry_id"), "amount": e.get("amount"), "category": e.get("category"), "description": e.get("description")}
        events.append(_make_event(ts, "ledger", title, details, "ledger", unit_id=e.get("unit_id")))
    return events


def _gather_notification_events_for_unit(unit_id: str) -> List[Dict[str, Any]]:
    events = []
    for nid, n in (_notification_history or {}).items():
        if unit_id:
            # notifications may not always have unit_id; match by farmer_id if unit->farmer mapping exists (skip for now)
            pass
        # include in timeline anyway — front-end can filter or correlate
        ts = n.get("delivered_at") or _to_iso(datetime.utcnow())
        title = f"Notification ({n.get('channel')})"
        details = {"notif_id": nid, "title": n.get("title"), "body": n.get("body"), "status": n.get("status")}
        events.append(_make_event(ts, "notification", title, details, "notification", unit_id=None))
    return events


def _gather_recommendation_events_for_unit(unit_id: str) -> List[Dict[str, Any]]:
    events = []
    if not generate_recommendations_for_unit:
        return events
    try:
        rec_obj = generate_recommendations_for_unit(unit_id)
        for idx, r in enumerate(rec_obj.get("recommendations", [])):
            # recommendations include generated_at in meta
            ts = r.get("generated_at") or rec_obj.get("generated_at") or _to_iso(datetime.utcnow())
            title = f"Recommendation: {r.get('category')}"
            details = {"recommendation": r.get("recommendation"), "score": r.get("score"), "meta": r.get("meta")}
            events.append(_make_event(ts, "recommendation", title, details, "recommendation_engine", unit_id=unit_id))
    except Exception:
        pass
    return events


# Public: timeline for a unit
def get_timeline_for_unit(
    unit_id: str,
    start_iso: Optional[str] = None,
    end_iso: Optional[str] = None,
    types: Optional[List[str]] = None,
    limit: int = 100,
    cursor: Optional[str] = None  # cursor is ISO timestamp to paginate older results (return items older than cursor)
) -> Dict[str, Any]:
    """
    Returns a timeline sorted by timestamp desc (most recent first).
    - types: optional list of kinds to include e.g. ["task","alert","irrigation","ledger","notification","recommendation"]
    - start_iso, end_iso: ISO date/time boundaries (inclusive)
    - cursor: ISO timestamp string; if provided, fetch events older than cursor (for pagination)
    - limit: max items to return
    """

    if unit_id not in _unit_store:
        return {"status": "unit_not_found", "unit_id": unit_id}

    # gather events
    events: List[Dict[str, Any]] = []
    events += _gather_calendar_events_for_unit(unit_id)
    events += _gather_alert_events_for_unit(unit_id)
    events += _gather_irrigation_events_for_unit(unit_id)
    events += _gather_ledger_events_for_unit(unit_id)
    # notifications are farm-level; include optionally
    events += _gather_notification_events_for_unit(unit_id)
    events += _gather_recommendation_events_for_unit(unit_id)

    # CUSTOM ACTIVITY EVENTS (vision + misc)
    try:
        for ce in _activity_store:
            if ce.get("unit_id") == unit_id:
                events.append(ce)
    except Exception:
        pass

    # normalize timestamps to datetime for filtering/sorting
    normalized = []
    for e in events:
        try:
            ts = e.get("timestamp")
            dt = datetime.fromisoformat(ts) if isinstance(ts, str) else ts
        except Exception:
            dt = datetime.utcnow()
        e["_ts_dt"] = dt
        normalized.append(e)

    # apply date range filters
    if start_iso:
        try:
            start_dt = datetime.fromisoformat(start_iso)
            normalized = [e for e in normalized if e["_ts_dt"] >= start_dt]
        except Exception:
            pass
    if end_iso:
        try:
            end_dt = datetime.fromisoformat(end_iso)
            normalized = [e for e in normalized if e["_ts_dt"] <= end_dt]
        except Exception:
            pass

    # apply cursor pagination: return events older than cursor (cursor represents last_seen timestamp)
    if cursor:
        try:
            cursor_dt = datetime.fromisoformat(cursor)
            normalized = [e for e in normalized if e["_ts_dt"] < cursor_dt]
        except Exception:
            pass

    # apply type filters
    if types:
        types_norm = set([t.lower() for t in types])
        normalized = [e for e in normalized if e.get("kind", "").lower() in types_norm]

    # sort descending (most recent first)
    normalized.sort(key=lambda x: x["_ts_dt"], reverse=True)

    # build page
    page = normalized[:limit]
    # prepare result items (remove internal _ts_dt)
    result_items = []
    for e in page:
        item = dict(e)
        item.pop("_ts_dt", None)
        result_items.append(item)

    # next cursor (for older results): timestamp of last item if there are more results
    next_cursor = None
    if len(normalized) > limit:
        last_dt = normalized[limit - 1]["_ts_dt"]
        next_cursor = last_dt.isoformat()

    return {
        "unit_id": unit_id,
        "count": len(result_items),
        "next_cursor": next_cursor,
        "items": result_items,
        "generated_at": datetime.utcnow().isoformat()
    }


# Public: farm-wide timeline (aggregate across units)
def get_timeline_for_farm(
    start_iso: Optional[str] = None,
    end_iso: Optional[str] = None,
    types: Optional[List[str]] = None,
    limit: int = 200,
    cursor: Optional[str] = None
) -> Dict[str, Any]:
    events = []

    # iterate all units and aggregate (careful with scale; this is in-memory aggregator)
    for uid in list(_unit_store.keys()):
        res = get_timeline_for_unit(uid, start_iso=start_iso, end_iso=end_iso, types=types, limit=limit, cursor=cursor)
        # extend with unit items
        for it in res.get("items", []):
            events.append(it)

    # append all custom events
    for ce in _activity_store:
        events.append(ce)

    # sort and paginate
    # normalize timestamps
    for e in events:
        try:
            e["_ts_dt"] = datetime.fromisoformat(e.get("timestamp"))
        except Exception:
            e["_ts_dt"] = datetime.utcnow()

    if types:
        types_norm = set([t.lower() for t in types])
        events = [e for e in events if e.get("kind","").lower() in types_norm]

    if start_iso:
        try:
            start_dt = datetime.fromisoformat(start_iso)
            events = [e for e in events if e["_ts_dt"] >= start_dt]
        except Exception:
            pass
    if end_iso:
        try:
            end_dt = datetime.fromisoformat(end_iso)
            events = [e for e in events if e["_ts_dt"] <= end_dt]
        except Exception:
            pass

    # cursor pagination older than cursor
    if cursor:
        try:
            cursor_dt = datetime.fromisoformat(cursor)
            events = [e for e in events if e["_ts_dt"] < cursor_dt]
        except Exception:
            pass

    events.sort(key=lambda x: x["_ts_dt"], reverse=True)
    page = events[:limit]
    items = []
    for e in page:
        e.pop("_ts_dt", None)
        items.append(e)

    next_cursor = None
    if len(events) > limit:
        next_cursor = events[limit - 1]["timestamp"]

    return {"count": len(items), "next_cursor": next_cursor, "items": items, "generated_at": datetime.utcnow().isoformat()}


# ============================================================
# PUBLIC: Record custom timeline event (used by Vision module)
# ============================================================

try:
    _activity_store
except NameError:
    _activity_store = []  # simple shared timeline store for custom events


def record_custom_event(
    unit_id: Optional[str],
    kind: str,
    title: str,
    details: Dict[str, Any],
    source: str = "custom",
    timestamp_iso: Optional[str] = None
) -> Dict[str, Any]:
    """
    Inserts a custom timeline event (ex: image analysis, equipment event, manual notes)
    """
    ts = timestamp_iso or datetime.utcnow().isoformat()
    ev = {
        "timestamp": ts,
        "kind": kind,
        "title": title,
        "details": details,
        "source": source,
        "unit_id": unit_id
    }
    _activity_store.append(ev)
    return ev