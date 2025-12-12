# backend/app/services/farmer/fuel_analytics_service.py

from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, Any, List, Optional

from app.services.farmer.equipment_service import (
    compute_equipment_operating_cost,
    equipment_workload_pressure_score,
    compute_breakdown_probability,
    _equipment_store,
    _store_lock
)
from app.services.farmer.operator_behavior_service import (
    compute_operator_behavior,
    _operator_usage_log
)

# ------------------------------------------------------------------------------------
# In-memory fuel log store
# ------------------------------------------------------------------------------------
_fuel_logs: List[Dict[str, Any]] = []
_fuel_lock = Lock()


def log_fuel_usage(
    equipment_id: str,
    liters: float,
    cost: float,
    operator_id: Optional[str] = None,
    timestamp: Optional[str] = None
):
    """
    Log a fuel event. This may be:
    - refill (+ liters)
    - consumption (- liters)
    """
    entry = {
        "equipment_id": equipment_id,
        "liters": liters,
        "cost": cost,
        "operator_id": operator_id,
        "timestamp": timestamp or datetime.utcnow().isoformat()
    }
    with _fuel_lock:
        _fuel_logs.append(entry)
    return entry


# ------------------------------------------------------------------------------------
# Helper: fetch logs for an equipment
# ------------------------------------------------------------------------------------
def _get_fuel_logs_for_equipment(equipment_id: str, lookback_days: int = 90):
    cutoff = datetime.utcnow() - timedelta(days=lookback_days)
    results = []
    with _fuel_lock:
        for e in _fuel_logs:
            ts = datetime.fromisoformat(e["timestamp"])
            if e["equipment_id"] == equipment_id and ts >= cutoff:
                results.append(e)
    return results


# ------------------------------------------------------------------------------------
# Core: Fuel Analytics
# ------------------------------------------------------------------------------------
def analyze_fuel_usage(equipment_id: str, lookback_days: int = 90) -> Dict[str, Any]:
    """
    Computes:
      - avg hourly burn rate
      - expected burn rate (from cost)
      - deviation %
      - operator link analysis
      - waste probability
    """

    logs = _get_fuel_logs_for_equipment(equipment_id, lookback_days=lookback_days)

    if not logs:
        return {
            "equipment_id": equipment_id,
            "status": "no_fuel_data",
            "avg_hourly_fuel": 0,
            "expected_hourly_fuel": 0,
            "deviation_pct": 0,
            "waste_probability": 0,
            "operator_influence": None
        }

    # Get cost signals (fuel_cost is a proxy)
    cost = compute_equipment_operating_cost(equipment_id) or {}
    fuel_cost = cost.get("fuel_cost", 0)
    hours = cost.get("total_hours", 1)

    expected_hourly = max(0.5, fuel_cost / max(1, hours))
    actual_liters = sum(e["liters"] for e in logs if e["liters"] < 0) * -1  # negative = consumption
    refill_liters = sum(e["liters"] for e in logs if e["liters"] > 0)

    # Compute actual hourly rate (if hours logged)
    actual_hourly = 0
    if hours > 0:
        actual_hourly = actual_liters / hours

    deviation_pct = 0
    if expected_hourly > 0:
        deviation_pct = int(((actual_hourly - expected_hourly) / expected_hourly) * 100)

    # Fuel waste probability (heuristic)
    waste_probability = 0
    if deviation_pct > 60:
        waste_probability = 80
    elif deviation_pct > 30:
        waste_probability = 50
    elif deviation_pct > 10:
        waste_probability = 20

    # Operator influence: determine which operator has largest deviation
    operator_map = {}
    for e in logs:
        op = e.get("operator_id")
        if not op:
            continue
        operator_map.setdefault(op, 0)
        operator_map[op] += max(0, e["liters"])

    op_influence = None
    if operator_map:
        op_influence = sorted(operator_map.items(), key=lambda x: x[1], reverse=True)[0]

    return {
        "equipment_id": equipment_id,
        "avg_hourly_fuel": round(actual_hourly, 2),
        "expected_hourly_fuel": round(expected_hourly, 2),
        "deviation_pct": deviation_pct,
        "total_fuel_consumed": round(actual_liters, 2),
        "total_fuel_refilled": round(refill_liters, 2),
        "waste_probability": waste_probability,
        "operator_influence": op_influence,
        "analyzed_at": datetime.utcnow().isoformat()
    }


# ------------------------------------------------------------------------------------
# Predictive Fuel Theft Detection
# ------------------------------------------------------------------------------------
def detect_fuel_theft(equipment_id: str, lookback_days: int = 60) -> Dict[str, Any]:
    """
    Detects:
      - sudden tank drops
      - mismatch between hours vs consumption
      - repeated low driver score
      - suspicious refill patterns
    """

    logs = _get_fuel_logs_for_equipment(equipment_id, lookback_days=lookback_days)
    if not logs:
        return {
            "equipment_id": equipment_id,
            "status": "no_data",
            "theft_probability": 0,
            "anomalies": []
        }

    anomalies = []
    theft_score = 0

    # 1) Sudden tank drops (consumption > expected)
    for e in logs:
        if e["liters"] < 0 and abs(e["liters"]) > 40:  # hardcoded threshold
            anomalies.append({"type": "sudden_drop", "event": e})
            theft_score += 20

    # 2) Refill > tank capacity
    with _store_lock:
        eq = _equipment_store.get(equipment_id)
    tank_cap = eq.get("tank_capacity", 60) if eq else 60

    for e in logs:
        if e["liters"] > tank_cap:
            anomalies.append({"type": "refill_exceeds_capacity", "event": e})
            theft_score += 30

    # 3) Operator-based anomalies
    op_scores = {}
    for e in logs:
        op = e.get("operator_id")
        if not op:
            continue
        op_scores[op] = compute_operator_behavior(op).get("final_behavior_score", 50)

    low_score_ops = [op for op, s in op_scores.items() if s < 40]
    if low_score_ops:
        anomalies.append({"type": "operator_risk", "operators": low_score_ops})
        theft_score += 25

    # 4) Workload mismatch (fuel usage too high compared to workload)
    pressure = equipment_workload_pressure_score(equipment_id) or {}
    if pressure.get("pressure_score", 30) < 20:
        # low workload but high deviation = suspicious
        analytics = analyze_fuel_usage(equipment_id, lookback_days)
        if analytics["deviation_pct"] > 30:
            anomalies.append({"type": "usage_mismatch", "details": analytics})
            theft_score += 25

    theft_probability = min(100, theft_score)

    return {
        "equipment_id": equipment_id,
        "theft_probability": theft_probability,
        "anomalies": anomalies,
        "checked_at": datetime.utcnow().isoformat()
    }


# ------------------------------------------------------------------------------------
# Fleet Fuel Analytics
# ------------------------------------------------------------------------------------
def fleet_fuel_dashboard() -> Dict[str, Any]:
    results = []

    with _store_lock:
        eq_ids = list(_equipment_store.keys())

    for eid in eq_ids:
        ana = analyze_fuel_usage(eid)
        theft = detect_fuel_theft(eid)
        results.append({
            "equipment_id": eid,
            "fuel_analytics": ana,
            "theft_risk": theft.get("theft_probability", 0)
        })

    # Sort worst offenders at top
    results.sort(key=lambda x: (x["fuel_analytics"].get("deviation_pct", 0), x["theft_risk"]), reverse=True)

    return {
        "count": len(results),
        "fuel_dashboard": results,
        "generated_at": datetime.utcnow().isoformat()
    }
