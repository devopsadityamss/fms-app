# backend/app/services/farmer/lubricant_wear_service.py

from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, Any, List, Optional

# reuse existing services / stores
from app.services.farmer.equipment_service import (
    compute_equipment_operating_cost,
    compute_equipment_health,
    generate_maintenance_schedule,
    _equipment_store,
    _store_lock
)
from app.services.farmer.operator_behavior_service import (
    compute_operator_behavior
)

# in-memory lubricant/oil usage store (per equipment)
_lubricant_usage_store: Dict[str, List[Dict[str, Any]]] = {}
_lubricant_lock = Lock()

# helper defaults
_DEFAULT_OIL_CHANGE_INTERVAL_HOURS = 250  # default hours between oil changes
_DEFAULT_OIL_USAGE_LITERS_PER_CHANGE = 6  # typical liters used per oil change (example)
_DEFAULT_FORECAST_MONTHS = 6


# ---------------------------
# CRUD: record lubricant usage (after maintenance)
# ---------------------------
def record_lubricant_usage(
    equipment_id: str,
    liters_used: float,
    performed_at: Optional[str] = None,
    notes: Optional[str] = None
) -> Dict[str, Any]:
    """
    Record a lubricant/oil usage event (typically recorded when oil change / service performed).
    """
    event = {
        "equipment_id": equipment_id,
        "liters_used": float(liters_used),
        "performed_at": performed_at or datetime.utcnow().isoformat(),
        "notes": notes
    }
    with _lubricant_lock:
        lst = _lubricant_usage_store.get(equipment_id, [])
        lst.append(event)
        _lubricant_usage_store[equipment_id] = lst
    return event


def list_lubricant_usage(equipment_id: str) -> List[Dict[str, Any]]:
    with _lubricant_lock:
        return _lubricant_usage_store.get(equipment_id, [])


# ---------------------------
# Forecast lubricant consumption for an equipment
# ---------------------------
def forecast_lubricant_consumption(
    equipment_id: str,
    horizon_months: int = _DEFAULT_FORECAST_MONTHS,
    lookback_days: int = 365,
    safety_buffer_pct: float = 0.20
) -> Optional[Dict[str, Any]]:
    """
    Forecasts lubricant / oil usage for the next `horizon_months` months.
    Uses:
      - historical lubricant change events (liters per change)
      - operating hours & avg monthly usage (from compute_equipment_operating_cost)
      - default intervals if no history
      - operator behavior (may increase consumption)
    Returns:
      {
        equipment_id,
        horizon_months,
        avg_liters_per_change,
        avg_hours_between_changes,
        forecast_total_liters,
        suggested_reorder_qty,
        recommended_check_interval_hours,
        generated_at
      }
    """

    # verify equipment present
    with _store_lock:
        if equipment_id not in _equipment_store:
            return None
        eq = _equipment_store[equipment_id]

    # get historical lubricant events
    with _lubricant_lock:
        events = list(_lubricant_usage_store.get(equipment_id, []))

    # compute historical averages (liters per change, hours between changes)
    liters_per_change_list = []
    change_datetimes = []
    for e in events:
        try:
            liters_per_change_list.append(float(e.get("liters_used", 0)))
            change_datetimes.append(datetime.fromisoformat(e.get("performed_at")))
        except Exception:
            continue

    avg_liters_per_change = None
    avg_hours_between_changes = None

    if liters_per_change_list:
        avg_liters_per_change = round(sum(liters_per_change_list) / len(liters_per_change_list), 2)

    if len(change_datetimes) >= 2:
        # sort and compute hours delta average
        change_datetimes.sort()
        deltas = []
        for i in range(1, len(change_datetimes)):
            delta_hours = (change_datetimes[i] - change_datetimes[i - 1]).total_seconds() / 3600.0
            deltas.append(delta_hours)
        if deltas:
            avg_hours_between_changes = int(sum(deltas) / len(deltas))

    # fallback to defaults using operating hours
    cost = compute_equipment_operating_cost(equipment_id) or {}
    total_hours = cost.get("total_hours", 0) or 0

    if avg_hours_between_changes is None:
        avg_hours_between_changes = _DEFAULT_OIL_CHANGE_INTERVAL_HOURS

    if avg_liters_per_change is None:
        avg_liters_per_change = _DEFAULT_OIL_USAGE_LITERS_PER_CHANGE

    # adjust by operator behavior: poor operators increase consumption by up to 15%
    # find top operator for this equipment by scanning operator logs (best-effort via operator_behavior)
    operator_influence_multiplier = 1.0
    try:
        # attempt to infer operator impact by checking operator behavior of most used operators
        # this is soft: if compute_operator_behavior is unavailable it will be ignored
        # we'll scan operator logs indirectly via equipment store (if stored there)
        ops = eq.get("last_known_operators", []) or []
        worst_behavior = None
        for op in ops:
            b = compute_operator_behavior(op)
            score = b.get("final_behavior_score", None)
            if score is None:
                continue
            if worst_behavior is None or score < worst_behavior:
                worst_behavior = score
        if worst_behavior is not None:
            if worst_behavior < 40:
                operator_influence_multiplier = 1.12
            elif worst_behavior < 55:
                operator_influence_multiplier = 1.06
    except Exception:
        operator_influence_multiplier = 1.0

    # forecast logic:
    # estimate hours per month from operating cost hours or derive from total_hours distributed across months
    avg_hours_per_month = 0
    # if total_hours is present, assume it's accumulated over the life - use a conservative 12-month normalization
    if total_hours and total_hours > 0:
        avg_hours_per_month = max(1.0, total_hours / max(1.0, 12.0))
    else:
        # fallback: assume 30 hours/month
        avg_hours_per_month = 30.0

    # calculate expected number of oil changes in horizon
    # hours_in_horizon = avg_hours_per_month * horizon_months
    hours_in_horizon = avg_hours_per_month * horizon_months
    # number_of_changes = hours_in_horizon / avg_hours_between_changes
    expected_changes = hours_in_horizon / max(1.0, avg_hours_between_changes)
    expected_changes = max(0.0, expected_changes)

    # total liters = expected_changes * avg_liters_per_change * operator multiplier * safety buffer
    total_liters = expected_changes * avg_liters_per_change * operator_influence_multiplier
    buffer_qty = total_liters * safety_buffer_pct
    forecast_total_liters = round(total_liters + buffer_qty, 2)

    # reorder suggestion: suggest reorder quantity (integers)
    suggested_reorder_qty = int(max(0, round(forecast_total_liters)))

    # recommended_check_interval_hours: smaller of avg_hours_between_changes reduced by operator factor
    recommended_check_interval_hours = int(max(50, avg_hours_between_changes / operator_influence_multiplier))

    return {
        "equipment_id": equipment_id,
        "horizon_months": horizon_months,
        "avg_liters_per_change": avg_liters_per_change,
        "avg_hours_between_changes": avg_hours_between_changes,
        "avg_hours_per_month": round(avg_hours_per_month, 1),
        "expected_changes": round(expected_changes, 2),
        "forecast_total_liters": forecast_total_liters,
        "safety_buffer_pct": safety_buffer_pct,
        "suggested_reorder_qty_liters": suggested_reorder_qty,
        "recommended_check_interval_hours": recommended_check_interval_hours,
        "operator_influence_multiplier": round(operator_influence_multiplier, 3),
        "generated_at": datetime.utcnow().isoformat()
    }


# ---------------------------
# Engine Wear Prediction
# ---------------------------
def predict_engine_wear(
    equipment_id: str,
    horizon_months: int = 6
) -> Optional[Dict[str, Any]]:
    """
    Predict engine wear risk and approximate Remaining Useful Life (RUL) in months.
    Uses:
      - equipment age (if available)
      - total operating hours
      - health score
      - maintenance history (next due / overdue)
      - lubricant change regularity (events)
      - operator behavior
    Returns:
      {
        equipment_id,
        engine_wear_score (0-100) higher = more wear,
        estimated_rul_months,
        key_drivers: [...],
        recommendations
      }
    """

    with _store_lock:
        if equipment_id not in _equipment_store:
            return None
        eq = _equipment_store[equipment_id]

    # basic signals
    age_years = None
    try:
        year = eq.get("year")
        if year:
            age_years = max(0, datetime.utcnow().year - int(year))
    except Exception:
        age_years = None

    # hours and cost info
    cost = compute_equipment_operating_cost(equipment_id) or {}
    total_hours = cost.get("total_hours", 0) or 0
    avg_hours_per_month = (total_hours / 12.0) if total_hours else 30.0

    # health score
    health = compute_equipment_health(equipment_id) or {}
    health_score = health.get("health_score", 70)

    # maintenance proximity
    maint = generate_maintenance_schedule(equipment_id) or {}
    days_until_maint = None
    try:
        nd = maint.get("next_maintenance_date")
        if isinstance(nd, str):
            days_until_maint = (datetime.fromisoformat(nd).date() - datetime.utcnow().date()).days
    except Exception:
        days_until_maint = None

    # lubricant irregularity: frequent oil changes (too frequent) or too few changes increases wear
    with _lubricant_lock:
        events = list(_lubricant_usage_store.get(equipment_id, []))

    # compute last change gap in hours (approx)
    last_change_hours = None
    if events:
        # approximate hours since last change using total_hours estimate
        # we don't have precise per-event hours; use event timestamps to estimate frequency instead
        try:
            last_event = max(events, key=lambda x: x.get("performed_at", ""))
            last_event_date = datetime.fromisoformat(last_event["performed_at"]).date()
            days_since_last = (datetime.utcnow().date() - last_event_date).days
            last_change_hours = int(days_since_last * 8)  # rough: assume 8 working hours/day
        except Exception:
            last_change_hours = None

    # operator influence
    operator_multiplier = 1.0
    try:
        ops = eq.get("last_known_operators", []) or []
        worst = None
        for op in ops:
            b = compute_operator_behavior(op)
            s = b.get("final_behavior_score", None)
            if s is None:
                continue
            if worst is None or s < worst:
                worst = s
        if worst is not None:
            if worst < 40:
                operator_multiplier = 1.25
            elif worst < 55:
                operator_multiplier = 1.1
    except Exception:
        operator_multiplier = 1.0

    # Base wear score derivation (0-100)
    wear_score = 0

    # age contributes
    if age_years is not None:
        if age_years >= 10:
            wear_score += 25
        elif age_years >= 6:
            wear_score += 15
        elif age_years >= 3:
            wear_score += 5

    # hours contribute
    if total_hours >= 10000:
        wear_score += 25
    elif total_hours >= 5000:
        wear_score += 15
    elif total_hours >= 2000:
        wear_score += 5

    # poor health amplifies wear
    if health_score < 40:
        wear_score += 25
    elif health_score < 60:
        wear_score += 10

    # overdue maintenance
    if days_until_maint is not None:
        if days_until_maint < 0:
            wear_score += 20
        elif days_until_maint <= 7:
            wear_score += 10

    # lubricant irregularity
    if last_change_hours is not None:
        if last_change_hours > (_DEFAULT_OIL_CHANGE_INTERVAL_HOURS * 1.5):
            # very long gap
            wear_score += 15
        elif last_change_hours < (_DEFAULT_OIL_CHANGE_INTERVAL_HOURS * 0.5):
            # too frequent changes (could indicate underlying issue) -> small penalty
            wear_score += 5

    # operator multiplier
    wear_score = int(min(100, wear_score * operator_multiplier))

    # Estimate Remaining Useful Life (RUL) in months (simple mapping)
    # higher wear_score -> lower RUL
    if wear_score >= 80:
        rul_months = 6
    elif wear_score >= 60:
        rul_months = 12
    elif wear_score >= 40:
        rul_months = 24
    else:
        rul_months = 48

    # drive key drivers list
    drivers = []
    if age_years is not None:
        drivers.append(f"age_years={age_years}")
    drivers.append(f"total_hours={int(total_hours)}")
    drivers.append(f"health_score={health_score}")
    if days_until_maint is not None:
        drivers.append(f"days_until_maintenance={days_until_maint}")
    if last_change_hours is not None:
        drivers.append(f"hours_since_last_oil_change={last_change_hours}")
    if operator_multiplier > 1.0:
        drivers.append(f"operator_multiplier={operator_multiplier}")

    recommendations = []
    if wear_score >= 60:
        recommendations.append("Consider major engine inspection and prepare a replacement plan within 12 months.")
        recommendations.append("Prioritize preventive maintenance and check lubrication system.")
    elif wear_score >= 40:
        recommendations.append("Increase preventive maintenance frequency and monitor oil quality.")
    else:
        recommendations.append("Standard maintenance cycle adequate; continue monitoring.")

    return {
        "equipment_id": equipment_id,
        "engine_wear_score": wear_score,
        "estimated_rul_months": rul_months,
        "key_drivers": drivers,
        "recommendations": recommendations,
        "generated_at": datetime.utcnow().isoformat()
    }


# ---------------------------
# Fleet-level forecast helpers
# ---------------------------
def fleet_lubricant_forecast(horizon_months: int = _DEFAULT_FORECAST_MONTHS) -> Dict[str, Any]:
    results = []
    with _store_lock:
        ids = list(_equipment_store.keys())

    for eid in ids:
        fc = forecast_lubricant_consumption(eid, horizon_months=horizon_months)
        if fc:
            results.append(fc)

    results.sort(key=lambda x: x["forecast_total_liters"], reverse=True)
    return {"horizon_months": horizon_months, "count": len(results), "fleet_forecast": results, "generated_at": datetime.utcnow().isoformat()}


def fleet_engine_wear(horizon_months: int = 12) -> Dict[str, Any]:
    results = []
    with _store_lock:
        ids = list(_equipment_store.keys())

    for eid in ids:
        p = predict_engine_wear(eid, horizon_months=horizon_months)
        if p:
            results.append(p)

    results.sort(key=lambda x: x["engine_wear_score"], reverse=True)
    return {"horizon_months": horizon_months, "count": len(results), "fleet_engine_wear": results, "generated_at": datetime.utcnow().isoformat()}
