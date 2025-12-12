# backend/app/services/farmer/equipment_maintenance_service.py

"""
Equipment Maintenance & Predictive Servicing (in-memory)

Features:
 - register equipment (owner farmer, model, serial, type, capacity)
 - log usage events (hours, km, cycles)
 - define maintenance rules (interval_hours, interval_days, checklist)
 - compute next service estimate (based on cumulative usage + last service)
 - create service tickets and manage their lifecycle
 - list maintenance history and equipment due for service
 - simple predictive heuristic: next_service_hours = last_service_hours + interval_hours - usage_since_last
"""

from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, Any, List, Optional
import uuid
import math

_lock = Lock()

# Stores
_equipment_store: Dict[str, Dict[str, Any]] = {}             # equipment_id -> metadata
_usage_logs: Dict[str, List[Dict[str, Any]]] = {}            # equipment_id -> [usage events]
_maintenance_rules: Dict[str, Dict[str, Any]] = {}           # rule_id -> {equipment_type, interval_hours, interval_days, checklist}
_service_tickets: Dict[str, Dict[str, Any]] = {}            # ticket_id -> record
_maintenance_history: Dict[str, List[Dict[str, Any]]] = {}   # equipment_id -> [maintenance records]


def _now_iso() -> str:
    return datetime.utcnow().isoformat()


# -----------------------
# Equipment registry
# -----------------------
def register_equipment(
    owner_id: str,
    equipment_type: str,
    model: str,
    serial_no: Optional[str] = None,
    capacity: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    eid = f"equip_{uuid.uuid4()}"
    rec = {
        "equipment_id": eid,
        "owner_id": owner_id,
        "equipment_type": equipment_type,
        "model": model,
        "serial_no": serial_no,
        "capacity": capacity or {},
        "metadata": metadata or {},
        "registered_at": _now_iso(),
        "active": True
    }
    with _lock:
        _equipment_store[eid] = rec
        _usage_logs.setdefault(eid, [])
        _maintenance_history.setdefault(eid, [])
    return rec


def get_equipment(equipment_id: str) -> Dict[str, Any]:
    return _equipment_store.get(equipment_id, {})


def list_equipment(owner_id: Optional[str] = None) -> List[Dict[str, Any]]:
    with _lock:
        items = list(_equipment_store.values())
    if owner_id:
        items = [i for i in items if i.get("owner_id") == owner_id]
    return items


# -----------------------
# Usage logging
# -----------------------
def log_usage(equipment_id: str, hours: float = 0.0, km: float = 0.0, cycles: int = 0, notes: Optional[str] = None, ts_iso: Optional[str] = None) -> Dict[str, Any]:
    if equipment_id not in _equipment_store:
        return {"error": "equipment_not_found"}
    entry = {
        "usage_id": f"usage_{uuid.uuid4()}",
        "equipment_id": equipment_id,
        "hours": float(hours),
        "km": float(km),
        "cycles": int(cycles),
        "notes": notes or "",
        "ts_iso": ts_iso or _now_iso()
    }
    with _lock:
        _usage_logs.setdefault(equipment_id, []).append(entry)
    return entry


def list_usage(equipment_id: str, limit: int = 200) -> List[Dict[str, Any]]:
    return list(_usage_logs.get(equipment_id, [])[-limit:])


def cumulative_usage_since(equipment_id: str, since_iso: Optional[str] = None) -> Dict[str, float]:
    hours = 0.0
    km = 0.0
    cycles = 0
    if equipment_id not in _usage_logs:
        return {"hours": 0.0, "km": 0.0, "cycles": 0}
    for u in _usage_logs.get(equipment_id, []):
        if since_iso:
            try:
                if datetime.fromisoformat(u.get("ts_iso")) <= datetime.fromisoformat(since_iso):
                    continue
            except Exception:
                pass
        hours += float(u.get("hours", 0.0))
        km += float(u.get("km", 0.0))
        cycles += int(u.get("cycles", 0))
    return {"hours": round(hours, 2), "km": round(km, 2), "cycles": cycles}


# -----------------------
# Maintenance rules
# -----------------------
def create_maintenance_rule(equipment_type: str, interval_hours: Optional[int] = None, interval_days: Optional[int] = None, checklist: Optional[List[str]] = None) -> Dict[str, Any]:
    rid = f"rule_{uuid.uuid4()}"
    rec = {
        "rule_id": rid,
        "equipment_type": equipment_type,
        "interval_hours": int(interval_hours) if interval_hours else None,
        "interval_days": int(interval_days) if interval_days else None,
        "checklist": checklist or [],
        "created_at": _now_iso()
    }
    with _lock:
        _maintenance_rules[rid] = rec
    return rec


def list_maintenance_rules(equipment_type: Optional[str] = None) -> List[Dict[str, Any]]:
    with _lock:
        rules = list(_maintenance_rules.values())
    if equipment_type:
        rules = [r for r in rules if r.get("equipment_type") == equipment_type]
    return rules


def assign_rule_to_equipment(equipment_id: str, rule_id: str) -> Dict[str, Any]:
    eq = _equipment_store.get(equipment_id)
    rule = _maintenance_rules.get(rule_id)
    if not eq:
        return {"error": "equipment_not_found"}
    if not rule:
        return {"error": "rule_not_found"}
    with _lock:
        eq.setdefault("maintenance", {})["rule_id"] = rule_id
        eq.setdefault("maintenance", {})["last_service_at"] = eq.setdefault("maintenance", {}).get("last_service_at")
        _equipment_store[equipment_id] = eq
    return eq


# -----------------------
# Predictive next service estimate
# -----------------------
def _get_last_service(equipment_id: str) -> Optional[Dict[str, Any]]:
    hist = _maintenance_history.get(equipment_id, [])
    if not hist:
        return None
    # assume maintenance record has 'performed_at' field
    return sorted(hist, key=lambda x: x.get("performed_at", ""), reverse=True)[0]


def estimate_next_service(equipment_id: str) -> Dict[str, Any]:
    """
    Heuristic:
     - Use assigned rule (interval_hours, interval_days)
     - Compute usage since last service; estimate hours remaining = interval_hours - usage_since_last
     - If interval_days is present, compute date-based next service as last_service_date + interval_days
     - Return both hour-based and date-based estimates, and a due flag if either is overdue
    """
    eq = _equipment_store.get(equipment_id)
    if not eq:
        return {"error": "equipment_not_found"}

    rule_id = eq.get("maintenance", {}).get("rule_id")
    rule = _maintenance_rules.get(rule_id) if rule_id else None

    last_service = _get_last_service(equipment_id)
    last_service_at_iso = last_service.get("performed_at") if last_service else None
    last_service_hours_total = last_service.get("odometer_hours") if last_service else 0.0

    # compute cumulative hours since last service
    usage_since = cumulative_usage_since(equipment_id, since_iso=last_service_at_iso)
    hours_used_since = usage_since.get("hours", 0.0)

    hours_remaining = None
    date_due_iso = None
    due = False

    if rule and rule.get("interval_hours"):
        interval = rule["interval_hours"]
        # if last_service recorded odometer_hours, compute remaining; else assume based on interval
        if last_service and last_service.get("odometer_hours") is not None:
            # odometer_hours records cumulative hours at service time
            odom_at_service = float(last_service.get("odometer_hours", 0.0))
            # total cumulative hours overall = odom_at_service + hours_used_since
            total_since = hours_used_since
            hours_remaining = max(0.0, interval - total_since)
            if hours_remaining <= 0:
                due = True
        else:
            # fallback: use usage_since as approximate and compute remaining as interval - usage_since
            hours_remaining = max(0.0, interval - hours_used_since)
            if hours_remaining <= 0:
                due = True

    if rule and rule.get("interval_days"):
        if last_service_at_iso:
            try:
                last_dt = datetime.fromisoformat(last_service_at_iso)
                date_due = last_dt + timedelta(days=rule["interval_days"])
                date_due_iso = date_due.isoformat()
                if datetime.utcnow() >= date_due:
                    due = True
            except Exception:
                date_due_iso = None
        else:
            # no last service date: next due is today + interval_days
            date_due_iso = (datetime.utcnow() + timedelta(days=rule["interval_days"])).isoformat()

    return {
        "equipment_id": equipment_id,
        "rule": rule,
        "last_service": last_service,
        "usage_since_last_service": usage_since,
        "hours_remaining": round(hours_remaining, 2) if hours_remaining is not None else None,
        "date_due_iso": date_due_iso,
        "due": due
    }


# -----------------------
# Service tickets
# -----------------------
def create_service_ticket(equipment_id: str, reported_by: str, issue: str, priority: str = "normal", metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if equipment_id not in _equipment_store:
        return {"error": "equipment_not_found"}
    tid = f"ticket_{uuid.uuid4()}"
    rec = {
        "ticket_id": tid,
        "equipment_id": equipment_id,
        "reported_by": reported_by,
        "issue": issue,
        "priority": priority,
        "status": "open",
        "assigned_to": None,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "metadata": metadata or {}
    }
    with _lock:
        _service_tickets[tid] = rec
    return rec


def update_ticket(ticket_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    with _lock:
        t = _service_tickets.get(ticket_id)
        if not t:
            return {"error": "ticket_not_found"}
        t.update(updates)
        t["updated_at"] = _now_iso()
        _service_tickets[ticket_id] = t
    return t


def list_tickets(equipment_id: Optional[str] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
    items = list(_service_tickets.values())
    if equipment_id:
        items = [i for i in items if i.get("equipment_id") == equipment_id]
    if status:
        items = [i for i in items if i.get("status") == status]
    return items


# -----------------------
# Record maintenance performed
# -----------------------
def record_maintenance_performed(equipment_id: str, performed_by: str, performed_at_iso: Optional[str] = None, odometer_hours: Optional[float] = None, notes: Optional[str] = None, checklist_done: Optional[List[str]] = None) -> Dict[str, Any]:
    if equipment_id not in _equipment_store:
        return {"error": "equipment_not_found"}
    rec = {
        "maintenance_id": f"maint_{uuid.uuid4()}",
        "equipment_id": equipment_id,
        "performed_by": performed_by,
        "performed_at": performed_at_iso or _now_iso(),
        "odometer_hours": float(odometer_hours) if odometer_hours is not None else None,
        "notes": notes or "",
        "checklist_done": checklist_done or []
    }
    with _lock:
        _maintenance_history.setdefault(equipment_id, []).append(rec)
    return rec


def maintenance_history(equipment_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    return list(_maintenance_history.get(equipment_id, [])[-limit:])


# -----------------------
# Utilities / Reports
# -----------------------
def equipment_due_for_service(owner_id: Optional[str] = None) -> List[Dict[str, Any]]:
    due_list = []
    with _lock:
        eqs = list(_equipment_store.values())
    if owner_id:
        eqs = [e for e in eqs if e.get("owner_id") == owner_id]
    for e in eqs:
        est = estimate_next_service(e["equipment_id"])
        if est.get("due"):
            due_list.append({"equipment": e, "estimate": est})
    return due_list


def equipment_summary(equipment_id: str) -> Dict[str, Any]:
    eq = _equipment_store.get(equipment_id)
    if not eq:
        return {"error": "equipment_not_found"}
    usage = cumulative_usage_since(equipment_id)
    next_service = estimate_next_service(equipment_id)
    history = maintenance_history(equipment_id)
    tickets = [t for t in list(_service_tickets.values()) if t.get("equipment_id") == equipment_id]
    return {
        "equipment": eq,
        "usage_summary": usage,
        "next_service": next_service,
        "maintenance_history": history,
        "service_tickets": tickets
    }
