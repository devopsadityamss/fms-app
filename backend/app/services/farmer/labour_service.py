# backend/app/services/farmer/labour_service.py

"""
Unified Farm Labour Management & Workload Optimization Engine (in-memory)

Hybrid merge:
 - Keeps original functions (add_laborer, record_labor_hours, estimate_labor_required, detect_labor_shortage, labor_summary, etc.)
 - Adds advanced features from labor_service: worker registry with skills/hourly_rate/active,
   availability calendar, task status + assignment, clock-in/clock-out timesheets, payroll, auto-assign, reports.
 - Names and helpers provide backward-compatible aliases where feasible.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from threading import Lock
import uuid
import math

_lock = Lock()

# Stores (merged)
_laborers: Dict[str, Dict[str, Any]] = {}            # laborer_id -> record (merged worker/laborer)
_labor_by_farmer: Dict[str, List[str]] = {}          # farmer_id -> [laborer_ids]

_labor_logs: Dict[str, Dict[str, Any]] = {}          # log_id -> record (per-hour logs)
_labor_logs_by_unit: Dict[str, List[str]] = {}       # unit_id -> [log_ids]

_task_assignments: Dict[str, Dict[str, Any]] = {}    # assignment_id -> record (tasks)
_assignments_by_unit: Dict[str, List[str]] = {}      # unit_id -> [assignment_ids]
_tasks_by_farmer: Dict[str, List[str]] = {}          # farmer_id -> [task_ids]

_availability: Dict[str, List[Dict[str, Any]]] = {}  # laborer_id -> availability entries
_timesheets: Dict[str, List[Dict[str, Any]]] = {}    # laborer_id -> timesheet entries
_assignments_for_worker: Dict[str, List[str]] = {}   # worker_id -> [assignment_ids]

# simple labor requirement heuristics (hours per acre)
LABOR_REQUIREMENTS = {
    "land_preparation": 4,
    "sowing": 6,
    "weeding": 5,
    "fertilization": 3,
    "irrigation": 2,
    "harvest": 10
}

def _now():
    return datetime.utcnow().isoformat()

def _newid(prefix: str):
    return f"{prefix}_{uuid.uuid4()}"

# -------------------------------------------------------------------
# LABORER REGISTRATION (merged)
# -------------------------------------------------------------------
def add_laborer(
    farmer_id: str,
    name: str,
    labor_type: str,        # family / hired
    daily_wage: Optional[float] = None,
    skills: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Backwards-compatible original add_laborer.
    Internally we store hourly_rate if provided in metadata.
    """
    lid = f"lab_{uuid.uuid4()}"
    rec = {
        "laborer_id": lid,
        "farmer_id": farmer_id,
        "name": name,
        "labor_type": labor_type,
        "daily_wage": daily_wage,
        # convert to hybrid fields
        "hourly_rate": metadata.get("hourly_rate") if metadata and metadata.get("hourly_rate") else (round(daily_wage/8,2) if daily_wage else None),
        "skills": skills or [],
        "active": True,
        "metadata": metadata or {},
        "created_at": _now()
    }
    with _lock:
        _laborers[lid] = rec
        _labor_by_farmer.setdefault(farmer_id, []).append(lid)
        _availability.setdefault(lid, [])
        _timesheets.setdefault(lid, [])
        _assignments_for_worker.setdefault(lid, [])
    return rec

# alias / compatibility: register_worker (new style) -> wrap add_laborer semantics
def register_worker(
    name: str,
    contact: Optional[str] = None,
    skill_tags: Optional[List[str]] = None,
    hourly_rate: Optional[float] = 100.0,
    farmer_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    New-style worker registration. If farmer_id not provided, caller should add mapping later.
    Returns worker record compatible with newer functions.
    """
    wid = _newid("wrk")
    rec = {
        "laborer_id": wid,
        "farmer_id": farmer_id,
        "name": name,
        "contact": contact,
        "skills": skill_tags or [],
        "hourly_rate": float(hourly_rate or 0.0),
        "daily_wage": round(float(hourly_rate or 0.0) * 8, 2) if hourly_rate else None,
        "active": True,
        "metadata": metadata or {},
        "created_at": _now()
    }
    with _lock:
        _laborers[wid] = rec
        if farmer_id:
            _labor_by_farmer.setdefault(farmer_id, []).append(wid)
        _availability.setdefault(wid, [])
        _timesheets.setdefault(wid, [])
        _assignments_for_worker.setdefault(wid, [])
    return rec

def get_worker(laborer_id: str) -> Dict[str, Any]:
    return _laborers.get(laborer_id, {})

def list_laborers(farmer_id: Optional[str] = None, skill_tags: Optional[List[str]] = None, active_only: bool = True) -> List[Dict[str, Any]]:
    with _lock:
        if farmer_id:
            ids = _labor_by_farmer.get(farmer_id, [])[:]
            items = [_laborers[i] for i in ids if i in _laborers]
        else:
            items = list(_laborers.values())
    if active_only:
        items = [w for w in items if w.get("active", True)]
    if skill_tags:
        items = [w for w in items if all(tag in w.get("skills", []) for tag in skill_tags)]
    return items

def update_worker(laborer_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    with _lock:
        w = _laborers.get(laborer_id)
        if not w:
            return {"error": "worker_not_found"}
        w.update(updates)
        w["updated_at"] = _now()
        _laborers[laborer_id] = w
    return w

def deactivate_worker(laborer_id: str) -> Dict[str, Any]:
    return update_worker(laborer_id, {"active": False})

# -------------------------------------------------------------------
# AVAILABILITY (new)
# -------------------------------------------------------------------
def set_availability(laborer_id: str, date_iso: str, from_time_iso: Optional[str], to_time_iso: Optional[str], note: Optional[str] = None) -> Dict[str, Any]:
    if laborer_id not in _laborers:
        return {"error": "worker_not_found"}
    rec = {
        "availability_id": _newid("avail"),
        "date_iso": date_iso,
        "from_time": from_time_iso,
        "to_time": to_time_iso,
        "note": note or "",
        "created_at": _now()
    }
    with _lock:
        _availability.setdefault(laborer_id, []).append(rec)
    return rec

def list_availability(laborer_id: str, from_date_iso: Optional[str] = None, to_date_iso: Optional[str] = None) -> List[Dict[str, Any]]:
    arr = _availability.get(laborer_id, [])[:]
    if from_date_iso or to_date_iso:
        def in_range(diso):
            try:
                d = datetime.fromisoformat(diso).date()
            except Exception:
                d = datetime.fromisoformat(diso + "T00:00:00").date()
            if from_date_iso and d < datetime.fromisoformat(from_date_iso).date():
                return False
            if to_date_iso and d > datetime.fromisoformat(to_date_iso).date():
                return False
            return True
        arr = [a for a in arr if in_range(a.get("date_iso"))]
    return arr

# -------------------------------------------------------------------
# RECORD HOURS / LABOR COST (merged)
# -------------------------------------------------------------------
def record_labor_hours(
    laborer_id: str,
    unit_id: str,
    task_name: str,
    hours: float,
    cost: Optional[float] = None,
    date_iso: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    log_id = f"log_{uuid.uuid4()}"
    rec = {
        "log_id": log_id,
        "laborer_id": laborer_id,
        "unit_id": str(unit_id),
        "task_name": task_name,
        "hours": float(hours),
        "cost": float(cost) if cost is not None else None,
        "date_iso": date_iso or datetime.utcnow().date().isoformat(),
        "metadata": metadata or {},
        "created_at": _now()
    }
    with _lock:
        _labor_logs[log_id] = rec
        _labor_logs_by_unit.setdefault(str(unit_id), []).append(log_id)
    return rec

def list_labor_logs(unit_id: str) -> List[Dict[str, Any]]:
    ids = _labor_logs_by_unit.get(str(unit_id), [])
    return [_labor_logs[i] for i in ids]

# -------------------------------------------------------------------
# TASK ASSIGNMENTS (merged)
# -------------------------------------------------------------------
def assign_task_to_labor(
    farmer_id: str,
    unit_id: str,
    laborer_id: str,
    task_name: str,
    estimated_hours: float,
    due_date_iso: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    aid = f"assign_{uuid.uuid4()}"
    rec = {
        "assignment_id": aid,
        "farmer_id": farmer_id,
        "unit_id": str(unit_id),
        "laborer_id": laborer_id,
        "task_name": task_name,
        "estimated_hours": float(estimated_hours),
        "due_date_iso": due_date_iso or datetime.utcnow().date().isoformat(),
        "status": "assigned",
        "metadata": metadata or {},
        "created_at": _now()
    }
    with _lock:
        _task_assignments[aid] = rec
        _assignments_by_unit.setdefault(str(unit_id), []).append(aid)
        _assignments_for_worker.setdefault(laborer_id, []).append(aid)
        _tasks_by_farmer.setdefault(farmer_id, []).append(aid)
    return rec

def list_assignments(unit_id: str) -> List[Dict[str, Any]]:
    ids = _assignments_by_unit.get(str(unit_id), [])
    return [_task_assignments[i] for i in ids]

def list_tasks(farmer_id: Optional[str] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
    with _lock:
        items = list(_task_assignments.values())
    if farmer_id:
        ids = _tasks_by_farmer.get(farmer_id, [])[:]
        items = [_task_assignments[i] for i in ids if _task_assignments.get(i)]
    if status:
        items = [t for t in items if t.get("status") == status]
    return items

def update_task_status(assignment_id: str, status: str) -> Dict[str, Any]:
    with _lock:
        t = _task_assignments.get(assignment_id)
        if not t:
            return {"error": "task_not_found"}
        t["status"] = status
        t["updated_at"] = _now()
        _task_assignments[assignment_id] = t
    return t

# auto-assign: find a worker with required skill and availability for the task date
def auto_assign(assignment_id: str) -> Dict[str, Any]:
    t = _task_assignments.get(assignment_id)
    if not t:
        return {"error": "task_not_found"}
    # basic skill match from metadata.skills_required or task_name keywords
    skills_required = t.get("metadata", {}).get("skills_required") or []
    date_iso = t.get("due_date_iso")
    # find candidates for the farmer
    farmer_id = t.get("farmer_id")
    candidate_ids = _labor_by_farmer.get(farmer_id, [])[:]
    for wid in candidate_ids:
        w = _laborers.get(wid)
        if not w or not w.get("active", True):
            continue
        # skill check
        if skills_required and not all(s in w.get("skills", []) for s in skills_required):
            continue
        # availability check
        av = list_availability(wid, from_date_iso=date_iso, to_date_iso=date_iso)
        if not av:
            continue
        # assign
        with _lock:
            t["laborer_id"] = wid
            t["status"] = "assigned"
            t["assigned_at"] = _now()
            _task_assignments[assignment_id] = t
            _assignments_for_worker.setdefault(wid, []).append(assignment_id)
        return {"assigned": True, "task": t}
    return {"error": "no_available_workers"}

def list_assignments_for_worker(worker_id: str) -> List[Dict[str, Any]]:
    tids = _assignments_for_worker.get(worker_id, [])[:]
    return [_task_assignments[t] for t in tids if t in _task_assignments]

def list_open_tasks_for_farmer(farmer_id: str) -> List[Dict[str, Any]]:
    return [t for t in list_tasks(farmer_id=farmer_id) if t.get("status") in ("open","assigned","in_progress")]

# -------------------------------------------------------------------
# TIMESHEETS & PAYROLL (new)
# -------------------------------------------------------------------
def clock_in(worker_id: str, task_id: Optional[str] = None, ts_iso: Optional[str] = None) -> Dict[str, Any]:
    if worker_id not in _laborers:
        return {"error": "worker_not_found"}
    rec = {
        "timesheet_id": _newid("ts"),
        "worker_id": worker_id,
        "task_id": task_id,
        "clock_in": ts_iso or _now(),
        "clock_out": None,
        "duration_hours": None,
        "created_at": _now()
    }
    with _lock:
        _timesheets.setdefault(worker_id, []).append(rec)
    return rec

def clock_out(worker_id: str, timesheet_id: str, ts_iso: Optional[str] = None) -> Dict[str, Any]:
    if worker_id not in _timesheets:
        return {"error": "no_timesheets_for_worker"}
    with _lock:
        rows = _timesheets.get(worker_id, [])
        for i, r in enumerate(rows):
            if r.get("timesheet_id") == timesheet_id:
                if r.get("clock_out"):
                    return {"error": "already_clocked_out"}
                r["clock_out"] = ts_iso or _now()
                try:
                    dt_in = datetime.fromisoformat(r["clock_in"])
                    dt_out = datetime.fromisoformat(r["clock_out"])
                    dur = (dt_out - dt_in).total_seconds() / 3600.0
                    r["duration_hours"] = round(dur, 2)
                except Exception:
                    r["duration_hours"] = None
                r["updated_at"] = _now()
                rows[i] = r
                _timesheets[worker_id] = rows
                return r
    return {"error": "timesheet_not_found"}

def list_timesheets(worker_id: str, from_date_iso: Optional[str] = None, to_date_iso: Optional[str] = None) -> List[Dict[str, Any]]:
    rows = _timesheets.get(worker_id, [])[:]
    if from_date_iso or to_date_iso:
        def in_range(r):
            try:
                d = datetime.fromisoformat(r["clock_in"]).date()
            except Exception:
                return False
            if from_date_iso and d < datetime.fromisoformat(from_date_iso).date():
                return False
            if to_date_iso and d > datetime.fromisoformat(to_date_iso).date():
                return False
            return True
        rows = [r for r in rows if in_range(r)]
    return rows

def compute_payroll_for_worker(worker_id: str, from_date_iso: Optional[str] = None, to_date_iso: Optional[str] = None) -> Dict[str, Any]:
    worker = _laborers.get(worker_id)
    if not worker:
        return {"error": "worker_not_found"}
    rows = list_timesheets(worker_id, from_date_iso, to_date_iso)
    total_hours = sum((r.get("duration_hours") or 0.0) for r in rows)
    hourly = float(worker.get("hourly_rate", 0.0) or 0.0)
    gross = round(total_hours * hourly, 2)
    deductions = 0.0
    net = round(gross - deductions, 2)
    return {"worker_id": worker_id, "total_hours": round(total_hours,2), "hourly_rate": hourly, "gross_pay": gross, "deductions": deductions, "net_pay": net, "timesheets": rows}

# -------------------------------------------------------------------
# LABOR REQUIREMENT ESTIMATION & SHORTAGE (original)
# -------------------------------------------------------------------
def estimate_labor_required(stage: str, area_acres: float) -> float:
    hrs_per_acre = LABOR_REQUIREMENTS.get(stage, 3)
    return round(hrs_per_acre * area_acres, 2)

def detect_labor_shortage(unit_id: str, stage: str, area_acres: float) -> Dict[str, Any]:
    required = estimate_labor_required(stage, area_acres)
    logs = list_labor_logs(unit_id)
    logged_hours = sum(l["hours"] for l in logs)
    shortage = required - logged_hours
    return {
        "unit_id": unit_id,
        "stage": stage,
        "required_hours": required,
        "logged_hours": logged_hours,
        "shortage_hours": round(shortage, 2) if shortage > 0 else 0,
        "status": "shortage" if shortage > 0 else "sufficient"
    }

# -------------------------------------------------------------------
# LABOR EFFICIENCY SCORE & SUMMARY (original + merged)
# -------------------------------------------------------------------
def labor_efficiency_score(unit_id: str) -> Dict[str, Any]:
    logs = list_labor_logs(unit_id)
    if not logs:
        return {"unit_id": unit_id, "score": 50}
    hours = [l["hours"] for l in logs]
    cost_vals = [l["cost"] for l in logs if l["cost"] is not None]
    avg_hours = sum(hours) / len(hours)
    avg_cost = sum(cost_vals) / len(cost_vals) if cost_vals else 0
    score = 100
    if avg_hours > 8:
        score -= 20
    if avg_cost > 500:
        score -= 30
    if avg_hours < 3:
        score -= 10
    score = max(0, min(score, 100))
    return {"unit_id": unit_id, "score": score}

def labor_summary(unit_id: str, stage: Optional[str], area_acres: float) -> Dict[str, Any]:
    return {
        "labor_logs": list_labor_logs(unit_id),
        "assignments": list_assignments(unit_id),
        "efficiency": labor_efficiency_score(unit_id),
        "shortage": detect_labor_shortage(unit_id, stage, area_acres) if stage else None,
        "timestamp": _now()
    }

# -------------------------------------------------------------------
# HELPERS
# -------------------------------------------------------------------
def find_available_workers(skill_tags: Optional[List[str]] = None, date_iso: Optional[str] = None) -> List[Dict[str, Any]]:
    candidates = list_laborers(skill_tags=skill_tags)
    if date_iso:
        out = []
        for w in candidates:
            av = list_availability(w["laborer_id"], from_date_iso=date_iso, to_date_iso=date_iso)
            if av:
                out.append(w)
        return out
    return candidates

# Backwards compatibility aliases
register_worker_alias = register_worker
add_laborer_alias = add_laborer

# End of labour_service.py
