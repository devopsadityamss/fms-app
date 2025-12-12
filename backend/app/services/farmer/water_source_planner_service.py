# backend/app/services/farmer/water_source_planner_service.py

"""
Feature 323 — Multi-Source Irrigation Planner

Goal:
  - Given an irrigation demand (liters) for a unit and a time window,
    decide how much water to pull from each available source:
      * tanks (on-farm storage)
      * borewell/pump
      * canal/municipal (metered, possibly cheaper)
      * trucked water (expensive emergency)
  - Respect constraints: tank usable volume, pump max rate, permitted draw limits, min reserve levels
  - Optimize by objective: cost-minimization, sustainability (prefer stored/renewable), or energy-minimization
  - Return mix (liters per source), estimated cost, energy estimate, warnings

Design notes:
  - In-memory, deterministic greedy optimizer (good for offline/edge devices)
  - Best-effort imports from other services but safe if missing
"""

from datetime import datetime
from threading import Lock
from typing import Dict, Any, List, Optional, Tuple
import uuid

_lock = Lock()

# defensive imports (best-effort)
try:
    from app.services.farmer.water_service import estimate_consumption, get_readings as tank_readings, list_tanks, get_tank
except Exception:
    list_tanks = lambda farmer_id: []
    get_tank = lambda tank_id: {}
    estimate_consumption = lambda *args, **kwargs: {}

try:
    from app.services.farmer.borewell_service import list_borewells, get_borewell
except Exception:
    list_borewells = lambda farmer_id: []
    get_borewell = lambda bid: {}

try:
    from app.services.farmer.water_energy_service import estimate_energy_from_flow_and_duration
except Exception:
    estimate_energy_from_flow_and_duration = lambda *args, **kwargs: {"estimated_kwh": None, "estimated_cost": None}

# Simple source registry per unit (optional). We keep it ephemeral here.
_source_registry: Dict[str, List[Dict[str, Any]]] = {}  # unit_id -> list of sources

def _now_iso():
    return datetime.utcnow().isoformat()

def _uid(prefix="src"):
    return f"{prefix}_{uuid.uuid4()}"

# -----------------------
# Source registration (optional helpers)
# -----------------------
def register_source_for_unit(unit_id: str, source_type: str, source_id: Optional[str], capacity_liters: Optional[float] = None, cost_per_1000l: Optional[float] = None, max_rate_lph: Optional[float] = None, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Register an available source for a unit.
    source_type: 'tank' | 'borewell' | 'canal' | 'trucked' | 'other'
    source_id: optional id linking to tank/pump/borewell
    capacity_liters: usable volume available (for tank or truck)
    cost_per_1000l: in currency units (e.g., INR per 1000 liters); None means unknown
    max_rate_lph: maximum withdrawal rate in L/h (pump or truck unloading)
    """
    rec = {
        "registry_id": _uid("src"),
        "unit_id": unit_id,
        "source_type": source_type,
        "source_id": source_id,
        "capacity_liters": float(capacity_liters) if capacity_liters is not None else None,
        "cost_per_1000l": float(cost_per_1000l) if cost_per_1000l is not None else None,
        "max_rate_lph": float(max_rate_lph) if max_rate_lph is not None else None,
        "metadata": metadata or {},
        "added_at": _now_iso()
    }
    with _lock:
        _source_registry.setdefault(unit_id, []).append(rec)
    return rec

def list_registered_sources(unit_id: str) -> List[Dict[str, Any]]:
    return _source_registry.get(unit_id, [])

# -----------------------
# Helper: probe available sources automatically (best-effort)
# -----------------------
def _probe_sources(unit_id: str, farmer_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Build candidate sources list using:
      - tanks belonging to farmer (capacity & current level)
      - borewells linked to farmer (assume capacity via pump rate)
      - canal: default unlimited but with cost if known (policy)
      - fallback: trucked water (expensive)
    This is best-effort and may be overridden by explicit registered sources.
    """
    sources = []

    # 1) Tanks (prefer local tank first)
    try:
        tanks = list_tanks(farmer_id) if farmer_id else []
        for t in tanks:
            # compute usable liters from estimated level
            est = get_tank(t.get("tank_id"))
            # t may have capacity_liters
            cap = float(t.get("capacity_liters") or 0.0)
            # estimate current level via water_service. We'll probe estimate_current_level if available in metadata
            level_pct = t.get("metadata", {}).get("estimated_pct")
            if level_pct is None:
                # try to derive from get_tank(...) or metadata
                level_pct = t.get("metadata", {}).get("level_pct")
            usable = None
            if level_pct is not None:
                try:
                    usable = cap * (float(level_pct)/100.0)
                except Exception:
                    usable = None
            sources.append({
                "source_type": "tank",
                "source_id": t.get("tank_id"),
                "label": f"Tank:{t.get('name')}",
                "capacity_liters": usable if usable is not None else cap,
                "cost_per_1000l": 0.0,  # storing/collected on-farm -> zero marginal cost
                "max_rate_lph": t.get("metadata", {}).get("max_rate_lph") or None,
                "priority": 10  # prefer tanks (sustainability)
            })
    except Exception:
        pass

    # 2) Borewells (pump withdrawal)
    try:
        wells = list_borewells(farmer_id) if farmer_id else []
        for b in wells:
            # assume no fixed capacity but a safe maximum withdrawal per day via pump metadata
            max_rate = b.get("metadata", {}).get("pump_max_lph") or b.get("metadata", {}).get("max_rate_lph") or 5000
            # cost: energy only (we don't calculate energy here but later we will)
            sources.append({
                "source_type": "borewell",
                "source_id": b.get("borewell_id"),
                "label": f"Borewell:{b.get('name')}",
                "capacity_liters": None,  # essentially limited by pump/runtime & sustainability
                "cost_per_1000l": None,   # energy-driven; unknown here
                "max_rate_lph": max_rate,
                "priority": 20
            })
    except Exception:
        pass

    # 3) Canal / municipal - assume available but possibly metered cost
    sources.append({
        "source_type": "canal",
        "source_id": None,
        "label": "Canal/Municipal",
        "capacity_liters": None,  # effectively unlimited for planning but subject to constraints in metadata
        "cost_per_1000l": None,   # unknown unless provided (e.g., subsidy)
        "max_rate_lph": None,
        "priority": 30
    })

    # 4) Trucked water (emergency, expensive)
    sources.append({
        "source_type": "trucked",
        "source_id": None,
        "label": "Trucked Water",
        "capacity_liters": None,
        "cost_per_1000l": 200.0,  # high default (INR/1000L); caller may override
        "max_rate_lph": 5000,
        "priority": 100
    })

    # override with registered explicit sources if any
    reg = _source_registry.get(unit_id, [])
    if reg:
        # merge: registered ones first (higher priority)
        # convert to standard shape
        explicit = []
        for r in reg:
            explicit.append({
                "source_type": r.get("source_type"),
                "source_id": r.get("source_id"),
                "label": r.get("metadata", {}).get("label") or f"{r.get('source_type')}:{r.get('source_id') or r.get('registry_id')}",
                "capacity_liters": r.get("capacity_liters"),
                "cost_per_1000l": r.get("cost_per_1000l"),
                "max_rate_lph": r.get("max_rate_lph"),
                "priority": 5
            })
        # explicit first, then probe list
        sources = explicit + sources

    return sources

# -----------------------
# Core planner (greedy optimizer)
# -----------------------
def plan_sources_for_demand(
    unit_id: str,
    farmer_id: Optional[str],
    demand_liters: float,
    by_when_iso: Optional[str] = None,
    objective: str = "cost",  # "cost" | "sustainability" | "energy"
    min_tank_reserve_pct: float = 10.0,
    prefer_tank_pct: float = 0.6
) -> Dict[str, Any]:
    """
    Returns a proposed allocation among sources to meet demand_liters.
    Strategy:
      - gather candidate sources
      - rank by objective (cost then priority)
      - greedily allocate while respecting capacity & max_rate constraints
    """
    demand = float(demand_liters or 0.0)
    if demand <= 0:
        return {"error": "invalid_demand", "unit_id": unit_id}

    candidates = _probe_sources(unit_id, farmer_id=farmer_id)

    # if objective= sustainability, prefer tanks & borewell with low energy; if cost prefer cheapest per 1000L
    # For sources without explicit cost, estimate via energy or set neutral large cost to de-prioritize if objective cost
    enriched = []
    for s in candidates:
        s2 = s.copy()
        # fill missing capacity: None -> treat as very large for planning but respect max_rate
        s2["capacity_liters"] = s2.get("capacity_liters")
        # cost per 1000l: if present use, else estimate via energy for borewell (best-effort)
        if s2.get("cost_per_1000l") is None:
            if s2["source_type"] == "tank":
                s2["cost_per_1000l"] = 0.0
            elif s2["source_type"] == "borewell":
                # approximate energy cost per 1000L via energy estimator with heuristic
                # assume pumping 1000L takes X kWh -> call estimate_energy_from_flow_and_duration with liters=1000
                try:
                    e = estimate_energy_from_flow_and_duration(liters=1000.0)
                    est_cost = e.get("estimated_cost")
                except Exception:
                    est_cost = None
                s2["cost_per_1000l"] = est_cost if est_cost is not None else 20.0
            elif s2["source_type"] == "canal":
                # assume cheap source if no cost known
                s2["cost_per_1000l"] = 5.0
            else:
                s2["cost_per_1000l"] = 200.0
        enriched.append(s2)

    # ranking key depends on objective
    if objective == "cost":
        # sort by cost_per_1000l then priority
        enriched.sort(key=lambda x: (x.get("cost_per_1000l", 1e6), x.get("priority", 100)))
    elif objective == "sustainability":
        # prefer tanks -> borewell -> canal -> trucked
        order = {"tank": 0, "borewell": 1, "canal": 2, "trucked": 3}
        enriched.sort(key=lambda x: (order.get(x.get("source_type"), 10), x.get("priority", 100)))
    else:
        # energy: prefer sources with lower estimated energy (use cost as proxy)
        enriched.sort(key=lambda x: (x.get("cost_per_1000l", 1e6), x.get("priority", 100)))

    allocation = []
    remaining = demand
    warnings: List[str] = []

    for s in enriched:
        if remaining <= 0:
            break
        cap = s.get("capacity_liters")
        max_rate = s.get("max_rate_lph")
        take = None
        # if cap is None, treat as unlimited for allocation but cap by remaining
        if cap is None:
            take = remaining
        else:
            # respect reserve if tank
            if s.get("source_type") == "tank" and cap is not None:
                # enforce reserve
                reserve = (min_tank_reserve_pct / 100.0) * cap
                usable = max(0.0, cap - reserve)
                take = min(usable, remaining)
                if take <= 0:
                    warnings.append(f"tank_{s.get('source_id')} below reserve")
                    continue
            else:
                take = min(cap, remaining)
        # also respect max_rate if by_when_iso provided and time window short: conservative check
        if by_when_iso and max_rate:
            try:
                # compute hours available until by_when
                now = datetime.utcnow()
                by_when = datetime.fromisoformat(by_when_iso)
                hours = max(0.001, (by_when - now).total_seconds() / 3600.0)
                possible_by_rate = max_rate * hours
                if take > possible_by_rate:
                    # cap take by possible_by_rate
                    take = possible_by_rate
                    warnings.append(f"capped {s.get('label')} allocation by max_rate over time window")
            except Exception:
                pass

        # allocate
        alloc = float(round(take, 2))
        allocation.append({
            "source_type": s.get("source_type"),
            "source_id": s.get("source_id"),
            "label": s.get("label"),
            "allocated_liters": alloc,
            "cost_per_1000l": s.get("cost_per_1000l"),
            "max_rate_lph": s.get("max_rate_lph")
        })
        remaining = round(max(0.0, remaining - alloc), 2)

    if remaining > 0:
        # unable to meet demand fully; mark trucked water recommendation
        allocation.append({
            "source_type": "trucked",
            "source_id": None,
            "label": "Trucked Water (emergency)",
            "allocated_liters": remaining,
            "cost_per_1000l": 200.0
        })
        warnings.append("demand_not_fulfilled; recommended trucked water")
        remaining = 0.0

    # compute cost & energy estimate
    total_cost = 0.0
    total_energy_kwh = 0.0
    for a in allocation:
        liters = a.get("allocated_liters", 0) or 0
        cost_p1000 = a.get("cost_per_1000l") or 0.0
        total_cost += (liters / 1000.0) * cost_p1000
        # estimate energy for pump sources (borewell) best-effort
        if a.get("source_type") == "borewell":
            try:
                # estimate energy to pump these liters
                e = estimate_energy_from_flow_and_duration(liters=liters)
                kwh = e.get("estimated_kwh") or 0.0
                total_energy_kwh += kwh
            except Exception:
                pass

    plan = {
        "unit_id": unit_id,
        "farmer_id": farmer_id,
        "demand_liters": demand,
        "allocated": allocation,
        "estimated_total_cost": round(total_cost, 2),
        "estimated_total_energy_kwh": round(total_energy_kwh, 4),
        "warnings": warnings,
        "generated_at": _now_iso()
    }

    return plan
