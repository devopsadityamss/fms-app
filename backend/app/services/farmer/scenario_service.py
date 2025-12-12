# backend/app/services/farmer/scenario_service.py

"""
Scenario Comparison & What-If Planner (Feature 303 - Medium)

Capabilities:
 - Accept multiple scenarios (each scenario = list of actions, optional schedule override, cost/labour assumptions).
 - For each scenario, run a future-risk simulation (via future_risk_service) and estimate:
     - 3/7-day risk timeline (from future_risk_service)
     - estimated cost delta (heuristic or via finance_service)
     - labour requirement / shortages (via labour_service heuristics)
     - estimated yield impact (heuristic rule-based)
 - Produce a ranked comparison with an overall "benefit_score" and explainable factors.
 - Optionally convert a winning scenario into scheduled actions and execution records (best-effort).
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from threading import Lock
import math
import uuid

# Best-effort imports (if a service is missing we degrade gracefully)
try:
    from app.services.farmer.future_risk_service import simulate_future_risk
except Exception:
    simulate_future_risk = None

try:
    from app.services.farmer.finance_service import apply_subsidy_rule, query_ledger
except Exception:
    apply_subsidy_rule = None
    query_ledger = None

try:
    from app.services.farmer.labour_service import estimate_labor_required, list_laborers
except Exception:
    estimate_labor_required = None
    list_laborers = None

try:
    from app.services.farmer.schedule_service import generate_schedule
except Exception:
    generate_schedule = None

try:
    from app.services.farmer.execution_monitor_service import create_execution_from_action, create_execution_record
except Exception:
    create_execution_from_action = None
    create_execution_record = None

try:
    from app.services.farmer.adaptive_intelligence_service import get_modifiers_for_farmer
except Exception:
    get_modifiers_for_farmer = None

_lock = Lock()

def _now_iso():
    return datetime.utcnow().isoformat()

def _uid():
    return str(uuid.uuid4())

# -------------------------
# Heuristics / helpers
# -------------------------
def _estimate_action_cost(action: Dict[str,Any]) -> float:
    """
    Heuristic cost estimation for an action.
    If action contains 'estimated_cost' use it; else infer from category/priority.
    """
    if not isinstance(action, dict):
        return 0.0
    if action.get("details", {}).get("estimated_cost") is not None:
        try:
            return float(action["details"]["estimated_cost"])
        except Exception:
            pass
    # fallback heuristics
    cat = (action.get("category") or "").lower()
    pr = int(action.get("priority", 50) or 50)
    base = 0.0
    if "irrig" in cat or "water" in cat:
        base = 200.0
    elif "fertil" in cat or "fert" in cat:
        base = 500.0
    elif "spray" in cat or "pest" in cat:
        base = 800.0
    elif "labour" in cat or "tasks" in cat:
        base = 300.0
    elif "equipment" in cat:
        base = 1000.0
    else:
        base = 150.0
    # scale by priority (higher priority more expensive likely)
    scale = 1.0 + (pr - 50) / 200.0
    return round(base * scale, 2)

def _estimate_labour_hours(action: Dict[str,Any]) -> float:
    """
    Estimate labour hours required for an action using provided details or heuristics.
    """
    det = action.get("details", {}) or {}
    if det.get("estimated_hours") is not None:
        try:
            return float(det.get("estimated_hours"))
        except Exception:
            pass
    # heuristic by category
    cat = (action.get("category") or "").lower()
    if "harvest" in cat:
        return 8.0
    if "weeding" in cat or "weeds" in cat:
        return 6.0
    if "sowing" in cat or "transplant" in cat:
        return 6.0
    if "spray" in cat or "pesticide" in cat:
        return 4.0
    if "irrig" in cat:
        return 2.0
    return 3.0

def _estimate_yield_impact(action: Dict[str,Any]) -> float:
    """
    Rough percent yield delta (positive or negative) that applying this action may cause over baseline.
    Heuristic: high-priority stage actions give +1..8% depending on category.
    """
    cat = (action.get("category") or "").lower()
    pr = int(action.get("priority",50) or 50)
    impact = 0.0
    if "fertil" in cat:
        impact = 3.0 + (pr - 50) / 20.0  # fertilizer can have decent effect
    elif "irrig" in cat:
        impact = 2.0 + (pr - 50) / 30.0
    elif "spray" in cat or "pest" in cat:
        impact = 4.0 + (pr - 50) / 15.0
    elif "harvest" in cat:
        impact = 0.5
    elif "labour" in cat:
        impact = 1.0
    else:
        impact = 0.5
    # clamp - allow small negative if low-priority risky action
    return round(max(-5.0, min(20.0, impact)), 2)

def _sum_action_costs(actions: List[Dict[str,Any]]) -> float:
    return round(sum(_estimate_action_cost(a) for a in actions), 2)

def _sum_action_labour_hours(actions: List[Dict[str,Any]]) -> float:
    return round(sum(_estimate_labour_hours(a) for a in actions), 2)

# -------------------------
# Scenario model
# -------------------------
# A scenario input structure:
# {
#   "id": "scenario-id",
#   "label": "Spray now",
#   "actions": [ {action dict from action_recommendation OR custom}, ... ],
#   "schedule_override": {optional schedule dict},
#   "assume_execute": bool (assume actions will be executed),
#   "note": "optional text"
# }
#
# Service outputs per scenario:
# {
#   "id","label","cost_estimate","labour_hours","yield_impact_pct",
#   "risk_simulation": <simulate_future_risk() result>,
#   "benefit_score": numeric,
#   "explain": [...strings...]
# }
#

def _score_scenario(cost: float, yield_pct: float, avg_risk_delta: float, labour_hours: float, farmer_modifiers: Optional[Dict[str,Any]] = None) -> float:
    """
    Compute a benefit score combining yield benefit, cost penalty, risk reduction, and labour feasibility.
    Higher is better.
    Basic formula (heuristic):
      score = w_y * yield_pct - w_cost * log(1+cost) - w_risk * avg_risk_delta - w_labour * (labour_hours / 8)
    We scale into 0..100 range at the end.
    """
    w_y = 6.0
    w_cost = 0.6
    w_risk = 4.0
    w_labour = 1.0

    # apply farmer-specific modifier if present (reduce cost sensitivity for high-capacity farmers)
    if farmer_modifiers:
        paf = float(farmer_modifiers.get("priority_adjustment_factor", 1.0))
        # if priority_adjustment_factor high -> value actions more
        w_y *= paf
        w_cost *= max(0.4, 1.0 / paf)

    # compute
    from math import log
    score_raw = (w_y * yield_pct) - (w_cost * math.log(1.0 + float(cost))) - (w_risk * float(avg_risk_delta)) - (w_labour * (float(labour_hours) / 8.0))
    # normalize roughly to 0..100: apply tanh-like scaling
    score_norm = 50.0 + (score_raw)  # baseline 50
    # clamp
    return max(0.0, min(100.0, round(score_norm, 2)))

# -------------------------
# Runner / comparator
# -------------------------
def run_single_scenario(
    unit_id: Optional[int],
    farmer_id: Optional[str],
    scenario: Dict[str,Any],
    days: int = 7,
    crop: Optional[str] = None,
    stage: Optional[str] = None,
    weather_forecast_override: Optional[List[Dict[str,Any]]] = None
) -> Dict[str,Any]:
    """
    Execute simulation for one scenario and return summary.
    """
    sid = scenario.get("id") or _uid()
    label = scenario.get("label") or f"scenario_{sid}"
    actions = scenario.get("actions", []) or []
    schedule_override = scenario.get("schedule_override")
    assume_execute = bool(scenario.get("assume_execute", False))

    # cost & labour heuristics
    total_cost = _sum_action_costs(actions)
    total_labour_hours = _sum_action_labour_hours(actions)
    # yield heuristic: sum of per-action estimated yield impact (approx additive)
    yield_impacts = [_estimate_yield_impact(a) for a in actions]
    total_yield_pct = round(sum(yield_impacts), 2)

    # obtain farmer modifiers if available
    farmer_mods = {}
    try:
        if farmer_id and get_modifiers_for_farmer:
            farmer_mods = get_modifiers_for_farmer(farmer_id) or {}
    except Exception:
        farmer_mods = {}

    # run risk simulation (pass schedule_override and simulate_execute_plan based on assume_execute)
    risk_sim = None
    try:
        if simulate_future_risk:
            risk_sim = simulate_future_risk(
                unit_id=unit_id,
                days=days,
                farmer_id=farmer_id,
                crop=crop,
                stage=stage,
                weather_forecast_override=weather_forecast_override,
                schedule_override=schedule_override,
                behaviour_modifier=None,
                simulate_execute_plan=assume_execute
            )
    except Exception:
        risk_sim = None

    # compute average risk delta vs baseline (if risk_sim available)
    avg_risk_delta = 0.0
    if risk_sim and isinstance(risk_sim, dict):
        days_list = risk_sim.get("days", [])
        if days_list:
            risks = [d.get("risk",0.0) for d in days_list]
            avg_risk = sum(risks)/len(risks)
            # try to get seed risk from summary
            seed = risk_sim.get("summary", {}).get("seed_risk", risks[0] if risks else 0.0)
            avg_risk_delta = round(avg_risk - float(seed or 0.0), 2)

    # estimate labour shortages (heuristic): if estimated hours > number of laborers * 8 * plan_days factor
    labourers_count = 1
    try:
        if farmer_id and list_laborers:
            lablist = list_laborers(farmer_id)
            labourers_count = max(1, len(lablist))
    except Exception:
        labourers_count = 1
    # capacity heuristic for the scenario period (days)
    labour_capacity_hours = labourers_count * 8.0 * max(1, days)
    labour_shortage_hours = max(0.0, total_labour_hours - labour_capacity_hours)

    # cost estimation improvement: attempt to use finance_service to check subsidies or ledger impacts (best-effort)
    finance_notes = []
    try:
        # if apply_subsidy_rule is available and scenario supplies subsidy_rule_id in metadata, simulate application
        for a in actions:
            rid = (a.get("details") or {}).get("subsidy_rule_id")
            if rid and apply_subsidy_rule and a.get("details",{}).get("applies_to_expense_entry"):
                # can't apply since we don't have expense entry id; skip but note
                finance_notes.append(f"Subsidy rule {rid} noted (manual apply needed)")
    except Exception:
        pass

    # compute benefit score
    benefit_score = _score_scenario(total_cost, total_yield_pct, avg_risk_delta, total_labour_hours, farmer_mods)

    explain = [
        f"Estimated cost: {total_cost}",
        f"Estimated labour hours: {total_labour_hours} (labourers: {labourers_count})",
        f"Estimated yield change: {total_yield_pct}%",
        f"Average risk delta vs seed over {days} days: {avg_risk_delta}",
        f"Labour shortage hours: {labour_shortage_hours}"
    ] + finance_notes

    return {
        "id": sid,
        "label": label,
        "actions_count": len(actions),
        "actions": actions,
        "cost_estimate": total_cost,
        "labour_hours": total_labour_hours,
        "labour_shortage_hours": labour_shortage_hours,
        "yield_impact_pct": total_yield_pct,
        "risk_simulation": risk_sim,
        "benefit_score": benefit_score,
        "explain": explain,
        "assume_execute": assume_execute,
        "schedule_override": schedule_override,
        "generated_at": _now_iso()
    }

def compare_scenarios(
    unit_id: Optional[int],
    farmer_id: Optional[str],
    scenarios: List[Dict[str,Any]],
    days: int = 7,
    crop: Optional[str] = None,
    stage: Optional[str] = None,
    weather_forecast_override: Optional[List[Dict[str,Any]]] = None
) -> Dict[str,Any]:
    """
    Runs multiple scenarios and returns a comparison summary with ranking.
    """
    results = []
    for s in scenarios:
        try:
            r = run_single_scenario(unit_id, farmer_id, s, days=days, crop=crop, stage=stage, weather_forecast_override=weather_forecast_override)
            results.append(r)
        except Exception as e:
            results.append({"id": s.get("id","unknown"), "error": str(e)})

    # rank by benefit_score (higher better)
    ranked = sorted([r for r in results if r.get("benefit_score") is not None], key=lambda x: x["benefit_score"], reverse=True)
    best = ranked[0] if ranked else None

    comparison = {
        "unit_id": unit_id,
        "farmer_id": farmer_id,
        "generated_at": _now_iso(),
        "days": days,
        "scenarios": results,
        "ranked": ranked,
        "recommended": (best.get("id") if best else None),
        "best": best
    }
    return comparison

# -------------------------
# Commit scenario -> schedule & executions (best-effort)
# -------------------------
def commit_scenario_as_schedule_and_executions(
    unit_id: Optional[int],
    farmer_id: Optional[str],
    scenario: Dict[str,Any],
    scheduled_at_iso: Optional[str] = None,
    window_hours: Optional[int] = None
) -> Dict[str,Any]:
    """
    Convert scenario into scheduled execution records and (optionally) a schedule.
    Creates execution records using execution_monitor_service.create_execution_from_action or create_execution_record if available.
    Returns created records summary.
    """
    created = []
    actions = scenario.get("actions", []) or []
    # try to generate a schedule (best-effort)
    schedule = None
    try:
        if generate_schedule and unit_id is not None:
            schedule = generate_schedule(unit_id=unit_id, farmer_id=farmer_id, crop=scenario.get("crop"), stage=scenario.get("stage"))
    except Exception:
        schedule = scenario.get("schedule_override")

    for a in actions:
        try:
            if create_execution_from_action:
                rec = create_execution_from_action(a, str(unit_id), farmer_id, scheduled_at_iso=scheduled_at_iso, window_hours=window_hours)
            else:
                # fallback to low-level create_execution_record if available
                if create_execution_record:
                    rec = create_execution_record(unit_id=str(unit_id), farmer_id=farmer_id, action_title=a.get("action"), category=a.get("category","action"), priority=int(a.get("priority",50)), scheduled_at_iso=scheduled_at_iso, window_hours=window_hours, metadata={"scenario_id": scenario.get("id")})
                else:
                    rec = {"error": "no_execution_api_available", "action": a}
            created.append(rec)
        except Exception as e:
            created.append({"error": str(e), "action": a})

    return {"created_count": len(created), "created": created, "schedule": schedule, "generated_at": _now_iso()}
