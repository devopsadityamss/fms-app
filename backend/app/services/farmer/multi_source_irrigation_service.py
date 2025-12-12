# backend/app/services/farmer/multi_source_irrigation_service.py

"""
Multi-Source Irrigation Planning Engine
---------------------------------------
Supports:
 - Registering multiple water sources per unit (borewell, canal, tank, pond, well)
 - Source capacity, availability, recharge rate
 - Cost per liter (energy, pumping cost)
 - Prioritized allocation plan
 - Daily water distribution plan
 - Season summary
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
import uuid

_sources: Dict[str, Dict[str, Any]] = {}
_sources_by_unit: Dict[str, List[str]] = {}

_plans: Dict[str, Dict[str, Any]] = {}
_plans_by_unit: Dict[str, List[str]] = {}


def _now():
    return datetime.utcnow().isoformat()


# -------------------------------------------------------------------------
# WATER SOURCE REGISTRATION
# -------------------------------------------------------------------------
def add_water_source(
    unit_id: str,
    name: str,
    source_type: str,         # borewell | canal | tank | pond | well
    capacity_liters: float,
    available_liters: float,
    cost_per_liter: float,    # pumping or delivery cost
    recharge_rate_lph: Optional[float] = 0.0,
    priority: int = 1,
    metadata: Optional[Dict[str, Any]] = None
):
    sid = f"ws_{uuid.uuid4()}"
    rec = {
        "source_id": sid,
        "unit_id": unit_id,
        "name": name,
        "type": source_type,
        "capacity_liters": float(capacity_liters),
        "available_liters": float(available_liters),
        "cost_per_liter": float(cost_per_liter),
        "recharge_rate_lph": float(recharge_rate_lph or 0.0),
        "priority": int(priority),
        "metadata": metadata or {},
        "created_at": _now()
    }
    _sources[sid] = rec
    _sources_by_unit.setdefault(unit_id, []).append(sid)
    return rec


def list_water_sources(unit_id: str):
    return [_sources[s] for s in _sources_by_unit.get(unit_id, [])]


# -------------------------------------------------------------------------
# MULTI-SOURCE ALLOCATION ALGORITHM
# -------------------------------------------------------------------------

def _allocate_sources(required_liters: float, sources: List[Dict[str, Any]]):
    """
    Allocates water based on:
      1. Highest priority first
      2. Then lowest cost per liter
      3. Then available storage
    """
    sources_sorted = sorted(sources, key=lambda s: (s["priority"], s["cost_per_liter"]))

    allocations = []
    remaining = required_liters

    for s in sources_sorted:
        if remaining <= 0:
            break

        use = min(remaining, s["available_liters"])
        allocations.append({
            "source_id": s["source_id"],
            "name": s["name"],
            "liters": round(use, 2),
            "cost_per_liter": s["cost_per_liter"]
        })
        remaining -= use

    return allocations, remaining


# -------------------------------------------------------------------------
# DAILY PLAN
# -------------------------------------------------------------------------
def generate_daily_multi_source_plan(
    unit_id: str,
    date_iso: str,
    required_liters: float
):
    sources = list_water_sources(unit_id)
    if not sources:
        return {"unit_id": unit_id, "status": "no_sources_registered"}

    allocations, leftover = _allocate_sources(required_liters, sources)

    pid = f"plan_{uuid.uuid4()}"
    plan = {
        "plan_id": pid,
        "unit_id": unit_id,
        "date": date_iso,
        "required_liters": required_liters,
        "allocations": allocations,
        "leftover_unallocated_liters": round(leftover, 2),
        "status": "partial" if leftover > 0 else "complete",
        "created_at": _now()
    }
    _plans[pid] = plan
    _plans_by_unit.setdefault(unit_id, []).append(pid)
    return plan


# -------------------------------------------------------------------------
# PLAN LISTING
# -------------------------------------------------------------------------
def list_plans(unit_id: str):
    ids = _plans_by_unit.get(unit_id, [])
    return [_plans[i] for i in ids]


# -------------------------------------------------------------------------
# SUMMARY
# -------------------------------------------------------------------------
def multi_source_summary(unit_id: str):
    plans = list_plans(unit_id)
    total_req = sum(p["required_liters"] for p in plans)
    total_used = 0

    source_totals = {}

    for p in plans:
        for alloc in p["allocations"]:
            total_used += alloc["liters"]
            sid = alloc["source_id"]
            source_totals[sid] = source_totals.get(sid, 0) + alloc["liters"]

    return {
        "unit_id": unit_id,
        "total_required_liters": round(total_req, 2),
        "total_allocated_liters": round(total_used, 2),
        "source_breakdown": [
            {
                "source_id": sid,
                "name": _sources[sid]["name"],
                "total_liters": round(amt, 2)
            }
            for sid, amt in source_totals.items()
        ],
        "timestamp": _now()
    }
