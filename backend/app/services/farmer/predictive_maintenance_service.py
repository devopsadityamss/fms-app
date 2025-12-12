# backend/app/services/farmer/predictive_maintenance_service.py

from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, Any, List, Optional
import uuid

# Reuse intel & parts services
from app.services.farmer.equipment_service import (
    forecast_equipment_downtime,
    generate_maintenance_schedule,
    _equipment_store,
    _store_lock
)
from app.services.farmer.spare_parts_service import (
    forecast_parts_for_equipment,
    list_low_stock_parts,
    record_part_consumption,
    _parts_store,
    _parts_lock
)
# technicians & operators service (operator service exists)
try:
    from app.services.farmer.operator_behavior_service import _operator_store
except Exception:
    _operator_store = {}

# In-memory maintenance orders store
_maintenance_orders: Dict[str, Dict[str, Any]] = {}
_maintenance_lock = Lock()

# Simple in-memory technician availability (tech_id -> list of unavailable date ranges)
_technician_availability: Dict[str, List[Dict[str, str]]] = {}
_tech_lock = Lock()

# Defaults
DEFAULT_MAINT_WINDOW_DAYS = 7
DEFAULT_LABOR_HOURS = 4


def register_technician(tech_id: str, name: str, skills: Optional[List[str]] = None):
    with _tech_lock:
        _technician_availability.setdefault(tech_id, [])
    return {"tech_id": tech_id, "name": name, "skills": skills or []}


def block_technician_period(tech_id: str, start_iso: str, end_iso: str):
    with _tech_lock:
        lst = _technician_availability.setdefault(tech_id, [])
        lst.append({"start": start_iso, "end": end_iso})
        _technician_availability[tech_id] = lst
    return {"tech_id": tech_id, "blocked_start": start_iso, "blocked_end": end_iso}


def _tech_is_available(tech_id: str, start_dt: datetime, end_dt: datetime) -> bool:
    with _tech_lock:
        ranges = _technician_availability.get(tech_id, [])
    for r in ranges:
        try:
            s = datetime.fromisoformat(r["start"])
            e = datetime.fromisoformat(r["end"])
            if not (end_dt < s or start_dt > e):
                return False
        except Exception:
            continue
    return True


def _find_available_technician(start_dt: datetime, end_dt: datetime, preferred_skills: Optional[List[str]] = None) -> Optional[str]:
    with _tech_lock:
        techs = list(_technician_availability.keys())
    # simple round-robin: pick first available
    for tid in techs:
        if _tech_is_available(tid, start_dt, end_dt):
            return tid
    return None


def propose_maintenance_for_equipment(equipment_id: str, horizon_days: int = 30) -> Optional[Dict[str, Any]]:
    """
    Propose a single maintenance order for equipment based on downtime forecast and parts forecast.
    Returns maintenance proposal dict (not confirmed).
    """
    with _store_lock:
        if equipment_id not in _equipment_store:
            return None
        eq = _equipment_store[equipment_id]

    # 1) Downtime forecast to determine urgency
    downtime = forecast_equipment_downtime(equipment_id, horizon_days=horizon_days) or {}
    downtime_score = downtime.get("downtime_score", 20)
    days_until_maint = downtime.get("signals", {}).get("days_until_maintenance_due")
    if days_until_maint is None:
        # fallback: schedule in next DEFAULT_MAINT_WINDOW_DAYS
        days_until_maint = DEFAULT_MAINT_WINDOW_DAYS

    # suggested window: if overdue (days_until_maint<0) -> as soon as possible (today + 1)
    if days_until_maint < 0:
        tentative_date = datetime.utcnow() + timedelta(days=1)
    else:
        tentative_date = datetime.utcnow() + timedelta(days=min(days_until_maint, DEFAULT_MAINT_WINDOW_DAYS))

    # 2) Parts forecast for equipment to list required parts (recommended)
    parts_forecast = forecast_parts_for_equipment(equipment_id, horizon_months=2)
    parts_needed = []
    for p in parts_forecast.get("parts", []):
        if p.get("required_reorder_qty", 0) > 0:
            # include minimal qty needed (1) if stock is zero
            parts_needed.append({
                "part_id": p["part_id"],
                "required_qty": p["required_reorder_qty"],
                "current_stock": p["current_stock"]
            })

    # if no parts predicted, create a conservative checklist (oil filter, engine oil)
    if not parts_needed:
        parts_needed = [{"part_id": "oil_filter_generic", "required_qty": 1, "current_stock": 0},
                        {"part_id": "engine_oil_generic", "required_qty": 6, "current_stock": 0}]

    # 3) Estimate labor hours (depend on downtime_score)
    labor_hours = DEFAULT_LABOR_HOURS
    if downtime_score >= 70:
        labor_hours = DEFAULT_LABOR_HOURS * 2
    elif downtime_score >= 40:
        labor_hours = int(DEFAULT_LABOR_HOURS * 1.5)

    # 4) Find available technician for tentative window (prefer next 3 days)
    # attempt to schedule at morning (09:00) for 1 day
    start_dt = tentative_date.replace(hour=9, minute=0, second=0, microsecond=0)
    end_dt = start_dt + timedelta(hours=labor_hours)
    assigned_tech = _find_available_technician(start_dt, end_dt)

    proposal = {
        "proposal_id": str(uuid.uuid4()),
        "equipment_id": equipment_id,
        "equipment": {"id": equipment_id, "name": eq.get("name")},
        "proposed_start_iso": start_dt.isoformat(),
        "proposed_end_iso": end_dt.isoformat(),
        "labor_hours": labor_hours,
        "parts_needed": parts_needed,
        "downtime_score": downtime_score,
        "priority": "high" if downtime_score >= 70 else ("medium" if downtime_score >= 40 else "low"),
        "assigned_technician_id": assigned_tech,
        "status": "proposed",
        "created_at": datetime.utcnow().isoformat()
    }

    return proposal


def batch_propose_maintenance(equipment_ids: Optional[List[str]] = None, horizon_days: int = 30) -> Dict[str, Any]:
    """
    Generate proposals for a list of equipment (or whole fleet if equipment_ids None).
    """
    proposals = []
    with _store_lock:
        ids = equipment_ids or list(_equipment_store.keys())

    for eid in ids:
        p = propose_maintenance_for_equipment(eid, horizon_days=horizon_days)
        if p:
            proposals.append(p)

    return {
        "count": len(proposals),
        "proposals": sorted(proposals, key=lambda x: x["downtime_score"], reverse=True),
        "generated_at": datetime.utcnow().isoformat()
    }


def confirm_maintenance_order(proposal: Dict[str, Any]) -> Dict[str, Any]:
    """
    Confirm a proposed maintenance order: reserve parts (decrement stock) and block technician calendar.
    """
    order_id = proposal.get("proposal_id") or str(uuid.uuid4())
    with _maintenance_lock:
        if order_id in _maintenance_orders:
            raise Exception("order_already_exists")
    # reserve parts (reduce stock if available; otherwise set required flag)
    parts_reserved = []
    for p in proposal.get("parts_needed", []):
        part_id = p.get("part_id")
        qty = int(p.get("required_qty", 0))
        with _parts_lock:
            part = _parts_store.get(part_id)
            if not part:
                # create placeholder with zero stock
                _parts_store[part_id] = {
                    "part_id": part_id,
                    "name": part_id,
                    "quantity": 0,
                    "min_stock_threshold": 1,
                    "consumption_history": []
                }
                part = _parts_store[part_id]
            current = int(part.get("quantity", 0))
            if current >= qty:
                part["quantity"] = current - qty
                # record consumption
                record_part_consumption(part_id, proposal["equipment_id"], qty)
                parts_reserved.append({"part_id": part_id, "reserved_qty": qty, "status": "reserved"})
            else:
                # partial or no availability
                reserved = min(current, qty)
                part["quantity"] = max(0, current - reserved)
                if reserved > 0:
                    record_part_consumption(part_id, proposal["equipment_id"], reserved)
                parts_reserved.append({"part_id": part_id, "reserved_qty": reserved, "status": "partial_or_backorder"})

    # block technician calendar if assigned
    tech_id = proposal.get("assigned_technician_id")
    try:
        if tech_id:
            start_iso = proposal["proposed_start_iso"]
            end_iso = proposal["proposed_end_iso"]
            block_technician_period(tech_id, start_iso, end_iso)
    except Exception:
        pass

    order = proposal.copy()
    order["order_id"] = order_id
    order["parts_reserved"] = parts_reserved
    order["status"] = "confirmed"
    order["confirmed_at"] = datetime.utcnow().isoformat()

    with _maintenance_lock:
        _maintenance_orders[order_id] = order

    return order


def list_maintenance_orders(status: Optional[str] = None) -> Dict[str, Any]:
    with _maintenance_lock:
        items = list(_maintenance_orders.values())
    if status:
        items = [i for i in items if i.get("status") == status]
    return {"count": len(items), "orders": items}


def cancel_maintenance_order(order_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
    with _maintenance_lock:
        rec = _maintenance_orders.get(order_id)
        if not rec:
            return {"error": "order_not_found"}
        rec["status"] = "cancelled"
        rec["cancelled_at"] = datetime.utcnow().isoformat()
        if reason:
            rec["cancel_reason"] = reason
    return {"success": True, "order_id": order_id}
