# backend/app/services/farmer/execution_monitor_service.py

"""
Farm Execution Monitoring Engine (Feature 300 - Moderate)

- Tracks recommended actions produced by the intelligence layer and records execution states.
- Maintains in-memory execution timeline per unit and a reliability score per farmer.
- Supports marking actions (done/partial/skipped/failed) and auto-reconciliation of missed windows (ignored).
- Best-effort integration with notification_service and farm_risk_service to escalate or de-escalate.
"""

from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, Any, List, Optional
import uuid

# Optional integration hooks (best-effort)
try:
    from app.services.farmer.notification_service import immediate_send
except Exception:
    immediate_send = None

try:
    from app.services.farmer.farm_risk_service import compute_risk_score
except Exception:
    compute_risk_score = None

_lock = Lock()

# Execution stores
# executions: unit_id (str) -> list of execution records (newest last)
_executions_by_unit: Dict[str, List[Dict[str, Any]]] = {}

# reliability scores per farmer_id (0..100)
_reliability_by_farmer: Dict[str, int] = {}

# Defaults
DEFAULT_RELIABILITY_START = 80
MIN_RELIABILITY = 20
MAX_RELIABILITY = 100

# Execution TTL for auto-reconcile: if scheduled_window_end < now -> eligible to mark ignored
# For records without explicit scheduled window, use created_at + 48h as window.
DEFAULT_WINDOW_HOURS = 48

# Score adjustments
_ADJ = {
    "done_on_time": +1,
    "done_late": 0,
    "partial": -1,
    "skipped": -2,
    "failed": -2,
    "ignored": -3,
    "missed_high_priority": -5
}

def _now_iso() -> str:
    return datetime.utcnow().isoformat()

def _uid() -> str:
    return str(uuid.uuid4())

def _get_list_for_unit(unit_id: str) -> List[Dict[str, Any]]:
    with _lock:
        return _executions_by_unit.setdefault(unit_id, [])

def _init_reliability(farmer_id: str) -> int:
    with _lock:
        if farmer_id not in _reliability_by_farmer:
            _reliability_by_farmer[farmer_id] = DEFAULT_RELIABILITY_START
        return _reliability_by_farmer[farmer_id]

def _clamp_reliability(v: int) -> int:
    return max(MIN_RELIABILITY, min(MAX_RELIABILITY, int(v)))

# ---------- Execution record creation ----------
def create_execution_record(
    unit_id: str,
    farmer_id: Optional[str],
    action_title: str,
    category: str,
    priority: int,
    scheduled_at_iso: Optional[str] = None,
    window_hours: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create and store an execution record for an action recommended by FARE.
    Returns the execution record (including action_id).
    """
    now = datetime.utcnow()
    scheduled = None
    if scheduled_at_iso:
        try:
            scheduled = datetime.fromisoformat(scheduled_at_iso)
        except Exception:
            scheduled = now

    window_hours = int(window_hours) if window_hours is not None else DEFAULT_WINDOW_HOURS
    scheduled_end = (scheduled or now) + timedelta(hours=window_hours)

    rec = {
        "action_id": _uid(),
        "unit_id": str(unit_id),
        "farmer_id": farmer_id,
        "action_title": action_title,
        "category": category,
        "priority": int(priority or 0),
        "scheduled_at": (scheduled or now).isoformat(),
        "scheduled_window_end": scheduled_end.isoformat(),
        "status": "scheduled",  # scheduled | done | partial | skipped | failed | ignored
        "status_at": None,
        "status_metadata": None,
        "created_at": now.isoformat(),
        "metadata": metadata or {}
    }
    with _lock:
        lst = _executions_by_unit.setdefault(str(unit_id), [])
        lst.append(rec)
    # ensure reliability init
    if farmer_id:
        _init_reliability(farmer_id)
    return rec

# ---------- Mark execution ----------
def mark_execution(unit_id: str, action_id: str, status: str, actor: Optional[str] = None, status_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Mark an execution with a status:
      status in {"done", "partial", "skipped", "failed"}
    Records the time, updates reliability and optionally notifies the farmer if configured.
    """
    valid = {"done", "partial", "skipped", "failed"}
    if status not in valid:
        return {"error": "invalid_status", "allowed": list(valid)}

    unit = str(unit_id)
    with _lock:
        lst = _executions_by_unit.get(unit, [])
        rec = next((r for r in lst if r.get("action_id") == action_id), None)
        if not rec:
            return {"error": "action_not_found"}
        prev_status = rec.get("status")
        rec["status"] = status
        rec["status_at"] = _now_iso()
        rec["status_metadata"] = status_metadata or {"actor": actor}
        # update in place (list holds reference)
    # update reliability
    farmer_id = rec.get("farmer_id")
    _apply_reliability_change(rec, prev_status, status)
    # Optional notify (ack)
    if immediate_send and farmer_id:
        try:
            title = f"Action updated: {rec.get('action_title')}"
            body = f"Status set to {status} by {actor or 'farmer'} for unit {unit}."
            immediate_send(str(farmer_id), title, body, channels=[ "in_app" ])
        except Exception:
            pass
    # Optionally adjust risk engine (best-effort)
    _trigger_risk_adjustment(rec, status)
    return rec

def _apply_reliability_change(record: Dict[str, Any], prev_status: Optional[str], new_status: str) -> None:
    """
    Adjust reliability score based on the transition.
    """
    farmer_id = record.get("farmer_id")
    if not farmer_id:
        return
    with _lock:
        _init_reliability(farmer_id)
        cur = _reliability_by_farmer.get(farmer_id, DEFAULT_RELIABILITY_START)
        adj = 0
        # determine if done_on_time or done_late
        try:
            scheduled_end = datetime.fromisoformat(record.get("scheduled_window_end"))
            marked_at = datetime.fromisoformat(record.get("status_at"))
            on_time = marked_at <= scheduled_end
        except Exception:
            on_time = True

        if new_status == "done":
            if on_time:
                adj = _ADJ["done_on_time"]
            else:
                adj = _ADJ["done_late"]
        elif new_status == "partial":
            adj = _ADJ["partial"]
        elif new_status == "skipped":
            adj = _ADJ["skipped"]
        elif new_status == "failed":
            adj = _ADJ["failed"]

        # extra penalty for high-priority missed (if prev_status scheduled and new_status is skipped/ignored)
        if record.get("priority",0) >= 80 and new_status in ("skipped","failed","partial"):
            adj += _ADJ["missed_high_priority"]

        new_score = _clamp_reliability(cur + adj)
        _reliability_by_farmer[farmer_id] = new_score

def _trigger_risk_adjustment(record: Dict[str, Any], status: str) -> None:
    """
    Best-effort hook: if a high-priority mitigation action was done, we can re-run risk_score.
    If missed/ignored, escalate risk by sending a notification or invoking compute_risk_score (non-persistent).
    """
    try:
        if compute_risk_score:
            # compute but do not store results; consuming systems can re-run if needed
            _ = compute_risk_score(unit_id=int(record.get("unit_id")) if record.get("unit_id") and record.get("unit_id").isdigit() else None, farmer_id=record.get("farmer_id"))
    except Exception:
        pass

    # send a notification for high priority failures
    try:
        if immediate_send and record.get("farmer_id"):
            if status in ("skipped","failed") and record.get("priority",0) >= 80:
                title = f"High-priority action {status}"
                body = f"High priority action '{record.get('action_title')}' marked {status} for unit {record.get('unit_id')}."
                immediate_send(str(record.get("farmer_id")), title, body, channels=[ "in_app" ])
    except Exception:
        pass

# ---------- Auto-reconcile (mark ignored) ----------
def auto_reconcile_executions(now_iso: Optional[str] = None, mark_ignored_for_priority_threshold: int = 50) -> Dict[str, Any]:
    """
    Scan all scheduled executions; if scheduled_window_end < now and status still 'scheduled', mark as 'ignored'.
    Applies reliability adjustments. Returns summary of reconciled items.
    """
    now = datetime.fromisoformat(now_iso) if now_iso else datetime.utcnow()
    reconciled = []
    with _lock:
        # flatten units
        for unit, lst in list(_executions_by_unit.items()):
            for rec in lst:
                if rec.get("status") == "scheduled":
                    try:
                        end = datetime.fromisoformat(rec.get("scheduled_window_end"))
                    except Exception:
                        # if invalid timestamp, treat as expired if older than DEFAULT_WINDOW_HOURS
                        created = datetime.fromisoformat(rec.get("created_at"))
                        end = created + timedelta(hours=DEFAULT_WINDOW_HOURS)
                    if end <= now:
                        # mark ignored
                        rec["status"] = "ignored"
                        rec["status_at"] = now.isoformat()
                        rec["status_metadata"] = {"auto_reconciled": True}
                        reconciled.append(rec)
                        # apply reliability penalty
                        _apply_reliability_change(rec, "scheduled", "ignored")
                        # optional notification for high-priority ignored
                        try:
                            if immediate_send and rec.get("farmer_id") and (rec.get("priority",0) >= mark_ignored_for_priority_threshold):
                                title = f"Missed action (ignored): {rec.get('action_title')}"
                                body = f"Action was not completed within scheduled window and has been marked ignored."
                                immediate_send(str(rec.get("farmer_id")), title, body, channels=[ "in_app" ])
                        except Exception:
                            pass
    return {"reconciled_count": len(reconciled), "reconciled": reconciled, "reconciled_at": _now_iso()}

# ---------- Querying & summary ----------
def list_executions_for_unit(unit_id: str, limit: int = 200) -> Dict[str, Any]:
    lst = _get_list_for_unit(str(unit_id))
    # return most recent first
    items = sorted(lst, key=lambda x: x.get("created_at",""), reverse=True)[:limit]
    return {"unit_id": unit_id, "count": len(items), "items": items}

def get_execution_summary(unit_id: str) -> Dict[str, Any]:
    """
    Return aggregated stats for the unit:
      - counts per status
      - last N executions
      - ignored_count, failed_count
    """
    lst = _get_list_for_unit(str(unit_id))
    counts = {"scheduled":0,"done":0,"partial":0,"skipped":0,"failed":0,"ignored":0}
    for r in lst:
        st = r.get("status","scheduled")
        counts[st] = counts.get(st,0) + 1
    recent = sorted(lst, key=lambda x: x.get("created_at",""), reverse=True)[:20]
    return {"unit_id": unit_id, "counts": counts, "recent": recent, "generated_at": _now_iso()}

def get_farmer_reliability(farmer_id: str) -> Dict[str, Any]:
    with _lock:
        score = _reliability_by_farmer.get(farmer_id)
        if score is None:
            score = _init_reliability(farmer_id)
    # provide some interpretation
    level = "good" if score >= 75 else ("average" if score >= 50 else "low")
    return {"farmer_id": farmer_id, "reliability_score": score, "level": level, "updated_at": _now_iso()}

# ---------- convenience: create from recommended action (useful for FARE integration) ----------
def create_execution_from_action(action: Dict[str, Any], unit_id: str, farmer_id: Optional[str], scheduled_at_iso: Optional[str] = None, window_hours: Optional[int] = None) -> Dict[str, Any]:
    """
    Accepts an action dict (from action_recommendation_service) and creates an execution record.
    Returns the created execution record.
    """
    return create_execution_record(
        unit_id=str(unit_id),
        farmer_id=farmer_id,
        action_title=action.get("action"),
        category=action.get("category") or "action",
        priority=int(action.get("priority",0)),
        scheduled_at_iso=scheduled_at_iso,
        window_hours=window_hours,
        metadata={"sources": action.get("sources",[]), "details": action.get("details",{})}
    )
