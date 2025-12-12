# backend/app/services/farmer/emissions_service.py

from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, Any, List, Optional

# reuse fuel logs and equipment store
from app.services.farmer.fuel_analytics_service import _fuel_logs, _fuel_lock
from app.services.farmer.equipment_service import _equipment_store, _store_lock, compute_equipment_operating_cost

# -----------------------------
# Emission factors (defaults)
# Values are heuristic defaults (kg CO2 per litre)
# Diesel ≈ 2.68 kg CO2/L, Petrol ≈ 2.31 kg CO2/L (commonly used factors)
# Allow override by providing emission_factors param.
# -----------------------------
_DEFAULT_EMISSION_FACTORS = {
    "diesel_l_per_l": 2.68,
    "petrol_l_per_l": 2.31,
    # if you store liters of other fuels, add mapping here (e.g., "bio_diesel_l_per_l": 2.0)
}

# small in-memory cache lock
_emissions_cache_lock = Lock()
_emissions_cache: Dict[str, Any] = {}


def _gather_fuel_logs_for_equipment(equipment_id: str, lookback_days: int = 90) -> List[Dict[str, Any]]:
    cutoff = datetime.utcnow() - timedelta(days=lookback_days)
    with _fuel_lock:
        logs = [e for e in _fuel_logs if e.get("equipment_id") == equipment_id and datetime.fromisoformat(e["timestamp"]) >= cutoff]
    return logs


def estimate_emissions_from_fuel(
    liters: float,
    fuel_type: str = "diesel",
    emission_factors: Optional[Dict[str, float]] = None
) -> float:
    """
    Estimate kg CO2 from liters using emission factors.
    Returns: kg CO2
    """
    ef = emission_factors or _DEFAULT_EMISSION_FACTORS
    key = f"{fuel_type}_l_per_l" if not fuel_type.endswith("_l_per_l") else fuel_type
    factor = ef.get(key)
    if factor is None:
        # default to diesel factor if unknown
        factor = ef.get("diesel_l_per_l", 2.68)
    return liters * float(factor)


def equipment_emissions_from_logs(
    equipment_id: str,
    lookback_days: int = 90,
    emission_factors: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Aggregate emissions for a single equipment from fuel logs.
    Returns breakdown (kg CO2) by fuel type and total (kg + tonnes).
    """
    logs = _gather_fuel_logs_for_equipment(equipment_id, lookback_days=lookback_days)
    if not logs:
        return {
            "equipment_id": equipment_id,
            "status": "no_fuel_logs",
            "lookback_days": lookback_days,
            "total_kg_co2": 0.0,
            "total_tonnes_co2": 0.0,
            "by_fuel_type": {},
            "generated_at": datetime.utcnow().isoformat()
        }

    by_type: Dict[str, float] = {}
    total_kg = 0.0

    for e in logs:
        # assume e.liters is signed (consumption negative), but use absolute liters refuel/consumed
        liters = abs(float(e.get("liters", 0)))
        # prefer fuel_type field if provided in log; else default to 'diesel'
        fuel_type = e.get("fuel_type") or e.get("fuel") or "diesel"
        # normalize short forms (allow 'petrol' and 'diesel')
        fuel_type = str(fuel_type).lower()

        kg = estimate_emissions_from_fuel(liters, fuel_type=fuel_type, emission_factors=emission_factors)
        by_type[fuel_type] = by_type.get(fuel_type, 0.0) + kg
        total_kg += kg

    return {
        "equipment_id": equipment_id,
        "lookback_days": lookback_days,
        "total_kg_co2": round(total_kg, 2),
        "total_tonnes_co2": round(total_kg / 1000.0, 3),
        "by_fuel_type": {k: round(v, 2) for k, v in by_type.items()},
        "samples": len(logs),
        "generated_at": datetime.utcnow().isoformat()
    }


def equipment_emissions_estimate_from_hours(
    equipment_id: str,
    lookback_days: int = 90,
    emission_factors: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    When fuel logs are missing, estimate emissions using operating cost and assumed liters-per-cost
    (heuristic): use compute_equipment_operating_cost -> fuel_cost and total_hours to derive liters estimate.
    This returns the same shape as equipment_emissions_from_logs but flags estimate_method.
    """
    with _store_lock:
        if equipment_id not in _equipment_store:
            return {"equipment_id": equipment_id, "status": "equipment_not_found"}

    cost = compute_equipment_operating_cost(equipment_id) or {}
    fuel_cost = cost.get("fuel_cost", 0.0)
    total_hours = cost.get("total_hours", 0) or 0

    # fallback assumptions
    assumed_price_per_liter = 100.0  # INR per liter (very rough); frontend should pass real price if known
    # if cost data exists and fuel_cost>0, estimate liters via fuel_cost / price_per_liter
    estimated_liters = 0.0
    if fuel_cost and fuel_cost > 0:
        # price per liter unknown — use 100 unless user has better data (API supports override)
        estimated_liters = fuel_cost / assumed_price_per_liter
    else:
        # fallback: use hours -> liters via default liters/hour assumption (e.g., 3 L/hr)
        default_lph = 3.0
        estimated_liters = (total_hours / max(1, 1)) * default_lph

    kg = estimate_emissions_from_fuel(estimated_liters, fuel_type="diesel", emission_factors=emission_factors)

    return {
        "equipment_id": equipment_id,
        "status": "estimated_from_cost_or_hours",
        "estimated_liters": round(estimated_liters, 2),
        "estimated_kg_co2": round(kg, 2),
        "estimated_tonnes_co2": round(kg / 1000.0, 3),
        "generated_at": datetime.utcnow().isoformat()
    }


def equipment_task_level_emissions(
    equipment_id: str,
    task_events: List[Dict[str, Any]],
    emission_factors: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Accept a list of task events for the equipment:
      task_events: [ { task_id, start_iso, end_iso, liters_used (optional), fuel_type(optional), estimated_hours(optional) }, ... ]
    Returns per-task emissions estimates and totals.
    """
    per_task = []
    total_kg = 0.0

    for t in task_events:
        liters = t.get("liters_used")
        fuel_type = (t.get("fuel_type") or "diesel").lower()
        if liters is None:
            # derive liters from estimated_hours and default liters_per_hour or equipment cost
            est_hours = float(t.get("estimated_hours", 0) or 0)
            if est_hours and est_hours > 0:
                # try to estimate lph from equipment operating cost
                cost = compute_equipment_operating_cost(equipment_id) or {}
                fuel_cost = cost.get("fuel_cost", 0.0)
                total_hours = cost.get("total_hours", 0) or 0
                lph = 3.0
                if total_hours and fuel_cost and fuel_cost > 0:
                    # crude: fuel liters = fuel_cost / assumed_price -> derive lph = liters / total_hours
                    assumed_price = 100.0
                    liters_total = fuel_cost / assumed_price
                    lph = liters_total / max(1.0, total_hours)
                liters = est_hours * lph
            else:
                liters = 0.0

        kg = estimate_emissions_from_fuel(abs(float(liters)), fuel_type=fuel_type, emission_factors=emission_factors)
        total_kg += kg
        per_task.append({
            "task_id": t.get("task_id"),
            "liters_used": round(float(liters), 2),
            "kg_co2": round(kg, 2),
            "tonnes_co2": round(kg / 1000.0, 3)
        })

    return {
        "equipment_id": equipment_id,
        "tasks": per_task,
        "total_kg_co2": round(total_kg, 2),
        "total_tonnes_co2": round(total_kg / 1000.0, 3),
        "generated_at": datetime.utcnow().isoformat()
    }


def fleet_emissions_summary(
    lookback_days: int = 90,
    emission_factors: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Aggregates emissions across the fleet using fuel logs when available, otherwise estimates from hours.
    Returns fleet totals and top-N emitters.
    """
    results = []
    total_kg = 0.0

    with _store_lock:
        ids = list(_equipment_store.keys())

    for eid in ids:
        ann = equipment_emissions_from_logs(eid, lookback_days=lookback_days, emission_factors=emission_factors)
        if ann.get("status") == "no_fuel_logs":
            ann = equipment_emissions_estimate_from_hours(eid, lookback_days=lookback_days, emission_factors=emission_factors)
        kg = ann.get("total_kg_co2") or ann.get("estimated_kg_co2") or 0.0
        results.append({"equipment_id": eid, "kg_co2": kg, "details": ann})
        total_kg += kg

    results.sort(key=lambda x: x["kg_co2"], reverse=True)

    return {
        "lookback_days": lookback_days,
        "fleet_total_kg_co2": round(total_kg, 2),
        "fleet_total_tonnes_co2": round(total_kg / 1000.0, 3),
        "top_emitters": results[:50],
        "generated_at": datetime.utcnow().isoformat()
    }
