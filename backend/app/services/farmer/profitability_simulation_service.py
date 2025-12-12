"""
Profitability Simulation Service (stub-ready)
---------------------------------------------

Simulates unit-level profitability based on projected yields, prices, and costs.
The logic is intentionally simple for now and can be replaced with a real
economic model later.

Inputs:
 - yield_kg: expected yield in kilograms
 - price_per_kg: expected selling price
 - variable_costs: dict of cost_name -> amount
 - fixed_costs: dict of cost_name -> amount
 - scenario: default | optimistic | pessimistic
 - unit_id: optional
 - notes: optional

Outputs:
 - gross_revenue
 - total_cost
 - net_profit
 - profit_per_kg
 - risk_adjusted_profit (stub)
"""

from typing import Dict, Any, Optional
from datetime import datetime
import uuid


# ---------------------------------------------------------------------
# In-memory store
# ---------------------------------------------------------------------
_sim_store: Dict[str, Dict[str, Any]] = {}


def _new_id() -> str:
    return str(uuid.uuid4())


def _now() -> str:
    return datetime.utcnow().isoformat()


# ---------------------------------------------------------------------
# Stub adjustment logic
# ---------------------------------------------------------------------
def _scenario_multiplier(scenario: Optional[str]) -> float:
    """
    Adjust profit by scenario assumption.
    """
    if not scenario:
        return 1.0
    s = scenario.lower()
    if s == "optimistic":
        return 1.15
    if s == "pessimistic":
        return 0.85
    return 1.0


def _risk_adjustment(net_profit: float, scenario: Optional[str]) -> float:
    """
    Fake risk-adjustment factor.
    """
    mult = _scenario_multiplier(scenario)
    adj = net_profit * mult * 0.95
    return round(adj, 2)


# ---------------------------------------------------------------------
# MAIN ENTRY
# ---------------------------------------------------------------------
def run_profitability_simulation(
    yield_kg: float,
    price_per_kg: float,
    variable_costs: Optional[Dict[str, float]] = None,
    fixed_costs: Optional[Dict[str, float]] = None,
    scenario: Optional[str] = None,
    unit_id: Optional[str] = None,
    notes: Optional[str] = None
) -> Dict[str, Any]:

    sim_id = _new_id()

    variable_costs = variable_costs or {}
    fixed_costs = fixed_costs or {}

    gross_revenue = yield_kg * price_per_kg
    total_variable = sum(variable_costs.values())
    total_fixed = sum(fixed_costs.values())
    total_cost = total_variable + total_fixed

    net_profit = gross_revenue - total_cost
    profit_per_kg = net_profit / yield_kg if yield_kg > 0 else 0

    risk_adjusted = _risk_adjustment(net_profit, scenario)

    record = {
        "id": sim_id,
        "unit_id": unit_id,
        "yield_kg": yield_kg,
        "price_per_kg": price_per_kg,
        "variable_costs": variable_costs,
        "fixed_costs": fixed_costs,
        "scenario": scenario,
        "generated_at": _now(),
        "results": {
            "gross_revenue": round(gross_revenue, 2),
            "total_cost": round(total_cost, 2),
            "net_profit": round(net_profit, 2),
            "profit_per_kg": round(profit_per_kg, 2),
            "risk_adjusted_profit": risk_adjusted
        },
        "notes": notes
    }

    _sim_store[sim_id] = record
    return record


def get_simulation(sim_id: str) -> Optional[Dict[str, Any]]:
    return _sim_store.get(sim_id)


def list_simulations(unit_id: Optional[str] = None) -> Dict[str, Any]:
    items = list(_sim_store.values())
    if unit_id:
        items = [i for i in items if i.get("unit_id") == unit_id]
    return {"count": len(items), "items": items}


def _clear_store():
    _sim_store.clear()
