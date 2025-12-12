# backend/app/services/farmer/operator_behavior_service.py

from datetime import datetime
from threading import Lock
from typing import Dict, Any, List, Optional

# Use existing equipment intelligence functions
from app.services.farmer.equipment_service import (
    compute_breakdown_probability,
    forecast_equipment_downtime,
    compute_equipment_operating_cost,
    _equipment_store,
    _store_lock
)

# Store all operator records
_operator_store: Dict[str, Dict[str, Any]] = {}
_operator_lock = Lock()

# Relationship: operator usage logs
_operator_usage_log: List[Dict[str, Any]] = []
_usage_lock = Lock()


# -------------------------------------------------------
# Register an operator
# -------------------------------------------------------
def add_operator(operator_id: str, name: str, phone: Optional[str] = None):
    record = {
        "operator_id": operator_id,
        "name": name,
        "phone": phone,
        "created_at": datetime.utcnow().isoformat()
    }
    with _operator_lock:
        _operator_store[operator_id] = record
    return record


# -------------------------------------------------------
# Log operator equipment usage
# -------------------------------------------------------
def log_operator_usage(operator_id: str, equipment_id: str, hours: float, task_type: str):
    entry = {
        "operator_id": operator_id,
        "equipment_id": equipment_id,
        "hours": hours,
        "task_type": task_type,
        "logged_at": datetime.utcnow().isoformat()
    }
    with _usage_lock:
        _operator_usage_log.append(entry)
    return entry


# -------------------------------------------------------
# Compute Operator Behavior Score
# -------------------------------------------------------
def compute_operator_behavior(operator_id: str) -> Dict[str, Any]:
    """
    Computes behavior score for operator:
      - fuel efficiency
      - breakdown impact
      - maintenance burden
      - machine stress (usage intensity)
      - downtime contribution
      - safe/unsafe patterns
    """

    with _operator_lock:
        op = _operator_store.get(operator_id)

    if not op:
        return {"operator_id": operator_id, "status": "operator_not_found"}

    # Get usage logs
    with _usage_lock:
        logs = [u for u in _operator_usage_log if u["operator_id"] == operator_id]

    if not logs:
        return {
            "operator_id": operator_id,
            "behavior_score": 50,
            "label": "insufficient_data",
            "usage_hours": 0,
            "recommendations": ["Not enough usage data to evaluate behavior."]
        }

    # Aggregate equipment IDs used
    eq_ids = list(set(log["equipment_id"] for log in logs))

    # -------------------------------------------------------
    # 1) Fuel efficiency scoring
    # -------------------------------------------------------
    total_cost = 0
    fuel_efficiency_score = 80  # good baseline

    for eid in eq_ids:
        cost = compute_equipment_operating_cost(eid) or {}
        fuel_cost = cost.get("fuel_cost", 0)
        total_cost += fuel_cost

    if total_cost > 5000:
        fuel_efficiency_score = 50
    if total_cost > 9000:
        fuel_efficiency_score = 30

    # -------------------------------------------------------
    # 2) Breakdown impact
    # -------------------------------------------------------
    breakdown_scores = []
    for eid in eq_ids:
        b = compute_breakdown_probability(eid) or {}
        breakdown_scores.append(b.get("breakdown_probability", 20))

    avg_breakdown_prob = sum(breakdown_scores) / len(breakdown_scores)

    if avg_breakdown_prob >= 60:
        breakdown_impact_score = 30
    elif avg_breakdown_prob >= 40:
        breakdown_impact_score = 50
    else:
        breakdown_impact_score = 80

    # -------------------------------------------------------
    # 3) Usage intensity (hard usage)
    # -------------------------------------------------------
    total_hours = sum(float(l["hours"]) for l in logs if l.get("hours"))
    if total_hours < 10:
        usage_intensity_score = 80
    elif total_hours < 50:
        usage_intensity_score = 60
    else:
        usage_intensity_score = 40  # heavy operator, more likely to stress machines

    # -------------------------------------------------------
    # 4) Downtime contribution
    # -------------------------------------------------------
    downtime_scores = []
    for eid in eq_ids:
        d = forecast_equipment_downtime(eid, horizon_days=30) or {}
        downtime_scores.append(d.get("downtime_score", 30))

    avg_downtime_risk = sum(downtime_scores) / len(downtime_scores)

    if avg_downtime_risk > 70:
        downtime_contribution_score = 30
    elif avg_downtime_risk > 40:
        downtime_contribution_score = 50
    else:
        downtime_contribution_score = 80

    # -------------------------------------------------------
    # 5) Maintenance burden proxy
    # -------------------------------------------------------
    maintenance_burden_score = 80
    if avg_breakdown_prob > 60 or avg_downtime_risk > 70:
        maintenance_burden_score = 40

    # -------------------------------------------------------
    # FINAL SCORE (0–100)
    # -------------------------------------------------------
    final_score = int(
        fuel_efficiency_score * 0.25 +
        breakdown_impact_score * 0.25 +
        usage_intensity_score * 0.15 +
        downtime_contribution_score * 0.20 +
        maintenance_burden_score * 0.15
    )

    # label
    if final_score >= 75:
        label = "excellent"
    elif final_score >= 55:
        label = "average"
    else:
        label = "poor"

    # recommendations
    recs = []

    if final_score < 55:
        recs.append("Operator shows signs of hard usage; provide training.")
    if avg_breakdown_prob > 50:
        recs.append("High breakdown association — assign this operator to newer equipment only with monitoring.")
    if avg_downtime_risk > 60:
        recs.append("Avoid assigning this operator to high-priority tasks; downtime contribution risk is high.")
    if fuel_efficiency_score < 50:
        recs.append("Fuel inefficiency detected — monitor throttle usage and idle time.")
    if not recs:
        recs.append("Operator performs efficiently with low machine stress.")

    return {
        "operator_id": operator_id,
        "operator_name": op.get("name"),
        "usage_hours": total_hours,
        "equipment_used": eq_ids,
        "fuel_efficiency_score": fuel_efficiency_score,
        "breakdown_impact_score": breakdown_impact_score,
        "usage_intensity_score": usage_intensity_score,
        "downtime_contribution_score": downtime_contribution_score,
        "maintenance_burden_score": maintenance_burden_score,
        "final_behavior_score": final_score,
        "label": label,
        "recommendations": recs,
        "computed_at": datetime.utcnow().isoformat()
    }


# -------------------------------------------------------
# Fleet-Level Operator Ranking
# -------------------------------------------------------

def fleet_operator_behavior_ranking() -> Dict[str, Any]:
    results = []

    with _operator_lock:
        ids = list(_operator_store.keys())

    for oid in ids:
        results.append(compute_operator_behavior(oid))

    results.sort(key=lambda x: x.get("final_behavior_score", 0), reverse=True)

    return {
        "count": len(results),
        "operators": results,
        "generated_at": datetime.utcnow().isoformat()
    }
