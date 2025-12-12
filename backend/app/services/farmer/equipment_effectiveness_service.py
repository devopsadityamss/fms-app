# backend/app/services/farmer/equipment_effectiveness_service.py

from datetime import datetime
from threading import Lock
from typing import Dict, Any, List, Optional

# reuse existing services
from app.services.farmer.equipment_service import (
    compute_equipment_operating_cost,
    compute_equipment_health,
    equipment_workload_pressure_score,
    get_equipment_suitability_score,   # if you named differently, replace import
    _equipment_store,
    _store_lock
)
from app.services.farmer.operator_behavior_service import (
    compute_operator_behavior
)
from app.services.farmer.fuel_analytics_service import (
    analyze_fuel_usage
)

_effectiveness_cache_lock = Lock()
_effectiveness_cache: Dict[str, Any] = {}

def compute_equipment_effectiveness_for_crop(
    equipment_id: str,
    crop: str,
    unit_id: Optional[str] = None,
    weight_config: Optional[Dict[str, float]] = None
) -> Optional[Dict[str, Any]]:
    """
    Returns a crop-specific effectiveness score for an equipment (0-100).
    Factors:
      - suitability (0..100)  -> weight default 0.30
      - fuel efficiency (inverse of liters_per_hour) -> weight 0.20
      - cost per hour (lower better) -> weight 0.15
      - health/uptime -> weight 0.15
      - workload pressure (lower pressure better) -> weight 0.10
      - operator behavior (if available) -> weight 0.10

    weight_config allows overriding weights, e.g. {"suitability":0.4, "fuel":0.2, ...}
    """

    with _store_lock:
        if equipment_id not in _equipment_store:
            return None
        eq = _equipment_store[equipment_id]

    # defaults
    weights = {
        "suitability": 0.30,
        "fuel_eff": 0.20,
        "cost": 0.15,
        "health": 0.15,
        "pressure": 0.10,
        "operator": 0.10
    }
    if weight_config:
        for k, v in weight_config.items():
            if k in weights:
                weights[k] = float(v)

    # 1) Suitability (0-100)
    try:
        suit = get_equipment_suitability_score(equipment_id, crop, "") or {}
        suit_score = suit.get("suitability_score", 50)
        suit_label = suit.get("label")
    except Exception:
        suit_score = 50
        suit_label = None

    # 2) Fuel efficiency: lower liters_per_hour better -> normalize to 0..100
    fuel = analyze_fuel_usage(equipment_id) or {}
    avg_hourly_fuel = fuel.get("avg_hourly_fuel")
    # Determine a reasonable normalization range: 0.5 L/hr (excellent) -> 8 L/hr (poor)
    if avg_hourly_fuel is None or avg_hourly_fuel <= 0:
        fuel_score = 60
    else:
        low = 0.5
        high = 8.0
        val = max(low, min(high, avg_hourly_fuel))
        # map so lower val -> higher score
        fuel_score = int((1 - ((val - low) / (high - low))) * 100)

    # 3) Cost per hour: lower is better
    cost = compute_equipment_operating_cost(equipment_id) or {}
    cph = cost.get("cost_per_hour", None)
    if cph is None:
        cost_score = 60
    else:
        # normalize: 0..200 -> map to 0..100, lower better
        val = min(max(0, cph), 200)
        cost_score = int((1 - (val / 200.0)) * 100)

    # 4) Health / uptime
    health = compute_equipment_health(equipment_id) or {}
    health_score = health.get("health_score", 70)
    if health_score is None:
        health_score = 70

    # 5) Workload pressure: lower pressure is better
    pressure = equipment_workload_pressure_score(equipment_id) or {}
    pressure_score_raw = pressure.get("pressure_score", 40)
    pressure_score = int((1 - (pressure_score_raw / 100.0)) * 100)

    # 6) Operator influence: find best/worst operator if present on equipment
    operator_bonus = 0
    try:
        last_ops = eq.get("last_known_operators", []) or []
        op_scores = []
        for op in last_ops:
            b = compute_operator_behavior(op) or {}
            op_scores.append(b.get("final_behavior_score", 50))
        if op_scores:
            avg_op = sum(op_scores) / len(op_scores)
            # map avg_op (0..100) directly to 0..100 (higher is better)
            operator_score = int(avg_op)
        else:
            operator_score = 60
    except Exception:
        operator_score = 60

    # Compose weighted score
    final_raw = (
        suit_score * weights["suitability"] +
        fuel_score * weights["fuel"] +
        cost_score * weights["cost"] +
        health_score * weights["health"] +
        pressure_score * weights["pressure"] +
        operator_score * weights["operator"]
    )

    final_score = int(round(min(100, max(0, final_raw))))

    # Category
    if final_score >= 80:
        category = "excellent"
    elif final_score >= 60:
        category = "good"
    elif final_score >= 40:
        category = "fair"
    else:
        category = "poor"

    # Recommendations (explainable)
    recs = []
    if suit_score < 50:
        recs.append("Suitability low for this crop — avoid assignment or consider attachments.")
    if fuel_score < 40:
        recs.append("High fuel consumption — check engine tuning / operator behavior.")
    if cost_score < 40:
        recs.append("High operating cost — consider alternative equipment for low-margin crops.")
    if health_score < 50:
        recs.append("Equipment health low — prioritize maintenance before high-value crop operations.")
    if pressure_score < 40:
        recs.append("High fleet pressure — avoid assigning to peak season critical tasks unless necessary.")
    if not recs:
        recs.append("Equipment is suitable for this crop under current conditions.")

    result = {
        "equipment_id": equipment_id,
        "crop": crop,
        "unit_id": unit_id,
        "scores": {
            "suitability": suit_score,
            "fuel_efficiency": fuel_score,
            "cost": cost_score,
            "health": health_score,
            "pressure": pressure_score,
            "operator": operator_score
        },
        "weights_used": weights,
        "final_effectiveness_score": final_score,
        "category": category,
        "recommendations": recs,
        "explainability": {
            "suitability_label": suit_label,
            "avg_hourly_fuel": fuel.get("avg_hourly_fuel"),
            "cost_per_hour": cph
        },
        "computed_at": datetime.utcnow().isoformat()
    }

    # optional cache keyed by equipment+crop+unit
    key = f"{equipment_id}::{crop}::{unit_id}"
    with _effectiveness_cache_lock:
        _effectiveness_cache[key] = result

    return result

def fleet_crop_effectiveness_ranking(
    crop: str,
    unit_plans: Optional[List[Dict[str, Any]]] = None,
    top_n: int = 20,
    weight_config: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Computes effectiveness for all equipment for the given crop and returns ranking.
    """
    results = []
    with _store_lock:
        eq_ids = list(_equipment_store.keys())

    for eid in eq_ids:
        r = compute_equipment_effectiveness_for_crop(eid, crop, unit_id=None, weight_config=weight_config)
        if r:
            results.append(r)

    results.sort(key=lambda x: x["final_effectiveness_score"], reverse=True)
    return {
        "crop": crop,
        "count": len(results),
        "ranking": results[:top_n],
        "generated_at": datetime.utcnow().isoformat()
    }
