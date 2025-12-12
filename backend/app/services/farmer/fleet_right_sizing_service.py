# backend/app/services/farmer/fleet_right_sizing_service.py

from datetime import datetime
from threading import Lock
from typing import Dict, Any, List, Optional, Tuple
import math

# reuse existing equipment intelligence
from app.services.farmer.equipment_service import (
    forecast_equipment_seasonal_workload,
    equipment_workload_pressure_score,
    compute_equipment_operating_cost,
    forecast_equipment_seasonal_workload as seasonal_forecast,
    _equipment_store,
    _store_lock
)

# If compute_equipment_profitability exists, we'll use it optionally
try:
    from app.services.farmer.equipment_service import compute_equipment_profitability
except Exception:
    compute_equipment_profitability = None


# In-memory recommendations store (optional)
_rightsizing_recommendations_store: Dict[str, Any] = {}
_rightsizing_lock = Lock()


def _gather_fleet_stats(unit_plans: List[Dict[str, Any]], season_months: int = 6) -> Dict[str, Any]:
    """
    Collects base stats: counts per equipment type, utilization, seasonal forecast per type.
    """
    with _store_lock:
        snapshot = {eid: rec.copy() for eid, rec in _equipment_store.items()}

    # current counts per type and list of equipment ids
    counts: Dict[str, List[str]] = {}
    cost_per_type: Dict[str, List[float]] = {}
    utilization_map: Dict[str, List[float]] = {}

    for eid, rec in snapshot.items():
        if rec.get("status") == "replaced":
            continue
        t = rec.get("type", "unknown").lower()
        counts.setdefault(t, []).append(eid)

        cost = compute_equipment_operating_cost(eid) or {}
        cph = cost.get("cost_per_hour")
        if cph is None:
            cph = 0.0
        cost_per_type.setdefault(t, []).append(cph)

        # compute utilization proxy via pressure score (lower pressure -> underutilised)
        p = equipment_workload_pressure_score(eid) or {}
        utilization_map.setdefault(t, []).append(100 - p.get("pressure_score", 40))  # higher = more free capacity

    # seasonal forecast aggregated per equipment type
    season = seasonal_forecast(unit_plans, season_months=season_months)
    monthly_load = season.get("monthly_load_summary", {})  # { 'YYYY-MM': { type: count } }

    # aggregate seasonal demand per type across months
    forecast_demand_per_type: Dict[str, int] = {}
    for month, tmap in monthly_load.items():
        for tp, cnt in tmap.items():
            forecast_demand_per_type[tp] = forecast_demand_per_type.get(tp, 0) + cnt

    # normalize demand into average per-month demand
    for tp in list(forecast_demand_per_type.keys()):
        forecast_demand_per_type[tp] = int(round(forecast_demand_per_type[tp] / max(1, season_months)))

    # build stats
    stats = {
        "fleet_snapshot": snapshot,
        "counts": {k: len(v) for k, v in counts.items()},
        "equipment_ids_by_type": counts,
        "avg_cost_per_hour_by_type": {k: (sum(v)/len(v) if v else 0.0) for k, v in cost_per_type.items()},
        "avg_free_capacity_pct_by_type": {k: (sum(v)/len(v) if v else 100.0) for k, v in utilization_map.items()},
        "forecast_monthly_demand_by_type": forecast_demand_per_type,
        "generated_at": datetime.utcnow().isoformat()
    }
    return stats


def analyze_right_sizing(
    unit_plans: List[Dict[str, Any]],
    season_months: int = 6,
    target_utilization_pct: int = 65,
    max_purchase_unit_cost: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Main right-sizing analyzer.
    - unit_plans: cropping plans used to predict demands
    - season_months: horizon for forecast
    - target_utilization_pct: desired fleet utilization (percentage)
    - max_purchase_unit_cost: optional map of equipment_type -> per-unit CAPEX for estimating buy cost

    Returns:
      {
        counts,
        forecast_monthly_demand_by_type,
        recommendations: [ { type, current_count, recommended_count, action, rationale, est_capex, est_opex_savings } ],
        details: { per_equipment_id: {...} }
      }
    """
    stats = _gather_fleet_stats(unit_plans, season_months=season_months)

    current_counts = stats["counts"]
    demand = stats["forecast_monthly_demand_by_type"]
    avg_cost = stats["avg_cost_per_hour_by_type"]
    free_capacity = stats["avg_free_capacity_pct_by_type"]
    equipment_ids_by_type = stats["equipment_ids_by_type"]

    recommendations = []
    details = {}

    for eq_type, required_per_month in demand.items():
        cur_count = current_counts.get(eq_type, 0)
        avg_free_pct = free_capacity.get(eq_type, 100.0)
        avg_cost_hour = avg_cost.get(eq_type, 0.0)

        # Estimate needed units: compute how many units required to cover demand at reasonable utilization.
        # Heuristic: assume 1 unit can handle `unit_capacity_per_month` tasks = baseline 20 tasks/month * utilization factor
        # We'll derive unit_capacity_per_month from current data if possible, otherwise use default 20.
        default_unit_capacity = 20
        # If we have current_count>0 and demand>0, compute capacity per unit as demand/current_count
        if cur_count > 0:
            unit_capacity_est = max(1, int(round(required_per_month / cur_count)))  # tasks per unit per month
            # invert to get estimated capacity per unit: better to assume default baseline
            unit_capacity_per_unit = max(default_unit_capacity, unit_capacity_est)
        else:
            unit_capacity_per_unit = default_unit_capacity

        # compute recommended_count to reach target_utilization
        # recommended_count = ceil(required_per_month / (unit_capacity_per_unit * target_utilization))
        # target_utilization expressed as fraction
        target_frac = max(0.1, min(0.95, target_utilization_pct / 100.0))
        rec_count = int(math.ceil(required_per_month / max(1, unit_capacity_per_unit * target_frac)))

        # Determine action
        if cur_count == 0 and rec_count > 0:
            action = "acquire"
        elif rec_count > cur_count:
            action = "acquire"
        elif rec_count < cur_count:
            action = "sell_or_redeploy"
        else:
            action = "hold"

        # estimate CAPEX if acquire
        est_capex = None
        if action == "acquire" and max_purchase_unit_cost:
            unit_capex = max_purchase_unit_cost.get(eq_type)
            if unit_capex:
                est_capex = round(unit_capex * max(0, rec_count - cur_count), 2)

        # estimate OPEX saving if selling excess units (rough): assume each sold unit reduces opex by avg CPH * utilization_hours_per_month
        est_opex_savings = None
        if action == "sell_or_redeploy" and cur_count > rec_count:
            # assume 160 hours/month usage per unit at current utilization estimate
            hours_per_month = 160 * (1 - (avg_free_pct / 100.0))
            est_opex_savings = round((cur_count - rec_count) * avg_cost_hour * hours_per_month, 2)

        rationale = [
            f"required_per_month={required_per_month}",
            f"unit_capacity_assumed={unit_capacity_per_unit}",
            f"current_count={cur_count}",
            f"target_utilization_pct={target_utilization_pct}"
        ]

        # details per equipment in this type (pressure & cost)
        member_details = []
        ids = equipment_ids_by_type.get(eq_type, [])
        for eid in ids:
            p = equipment_workload_pressure_score(eid) or {}
            c = compute_equipment_operating_cost(eid) or {}
            member_details.append({
                "equipment_id": eid,
                "pressure_score": p.get("pressure_score"),
                "cost_per_hour": c.get("cost_per_hour"),
                "health_score": (c.get("health_score") if "health_score" in c else None)
            })
            # store details in global mapping
            details[eid] = member_details[-1]

        recommendations.append({
            "equipment_type": eq_type,
            "current_count": cur_count,
            "recommended_count": rec_count,
            "action": action,
            "rationale": rationale,
            "est_capex_if_acquire": est_capex,
            "est_opex_savings_if_sell": est_opex_savings,
            "members": member_details
        })

    result = {
        "generated_at": datetime.utcnow().isoformat(),
        "season_months": season_months,
        "stats": stats,
        "recommendations": recommendations,
        "details": details
    }

    # cache results
    key = f"rightsizing_{datetime.utcnow().timestamp()}"
    with _rightsizing_lock:
        _rightsizing_recommendations_store[key] = result

    return result


def fetch_last_rightsizing(recent_n: int = 1) -> List[Dict[str, Any]]:
    with _rightsizing_lock:
        items = list(_rightsizing_recommendations_store.items())
    # return last N values
    items_sorted = sorted(items, key=lambda x: x[0], reverse=True)
    return [v for k, v in items_sorted[:recent_n]]
