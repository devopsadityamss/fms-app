# backend/app/services/farmer/equipment_service.py

"""
Equipment & Machinery Management (Phase 1)

Implements:
- Add equipment (feature #201)
- Internal memory store (temporary, no DB)
"""

from datetime import datetime
from typing import Dict, Any
import uuid
from threading import Lock
from typing import List
from datetime import timedelta
from typing import List, Optional

# In-memory equipment store
_equipment_store: Dict[str, Dict[str, Any]] = {}
_store_lock = Lock()


def add_equipment(
    name: str,
    type: str,
    manufacturer: str = "",
    model: str = "",
    year: int = None,
    assigned_unit_id: int = None,
) -> Dict[str, Any]:
    """
    Add new equipment to system.
    No DB used yet — stored only in memory.
    """

    equipment_id = str(uuid.uuid4())
    record = {
        "id": equipment_id,
        "name": name,
        "type": type,
        "manufacturer": manufacturer,
        "model": model,
        "year": year,
        "assigned_unit_id": assigned_unit_id,
        "created_at": datetime.utcnow(),
    }

    with _store_lock:
        _equipment_store[equipment_id] = record

    return record


def list_equipment() -> Dict[str, Any]:
    """
    Return all equipment records.
    """
    with _store_lock:
        items = list(_equipment_store.values())
    return {"count": len(items), "items": items}


def get_equipment(equipment_id: str) -> Dict[str, Any]:
    """
    Get equipment record by ID.
    """
    with _store_lock:
        return _equipment_store.get(equipment_id)
def update_equipment(
    equipment_id: str,
    name: str = None,
    type: str = None,
    manufacturer: str = None,
    model: str = None,
    year: int = None,
    assigned_unit_id: int = None,
) -> Dict[str, Any]:
    """
    Update equipment details (Feature #202)
    Only updates fields provided (partial update).
    """
    with _store_lock:
        rec = _equipment_store.get(equipment_id)
        if not rec:
            return None

        if name is not None:
            rec["name"] = name
        if type is not None:
            rec["type"] = type
        if manufacturer is not None:
            rec["manufacturer"] = manufacturer
        if model is not None:
            rec["model"] = model
        if year is not None:
            rec["year"] = year
        if assigned_unit_id is not None:
            rec["assigned_unit_id"] = assigned_unit_id

        rec["updated_at"] = datetime.utcnow()

    return rec

def delete_equipment(equipment_id: str) -> bool:
    """
    Delete equipment from in-memory store (Feature #203).
    Returns True if deleted, False if not found.
    """
    with _store_lock:
        if equipment_id in _equipment_store:
            del _equipment_store[equipment_id]
            return True
        return False

def compute_equipment_health(equipment_id: str) -> Dict[str, Any]:
    """
    Computes an equipment health score (0–100) based on:
    - age (year)
    - usage (mock)
    - wear factor (mock)
    - model reliability (mock)
    
    Pure mock logic for now. Will be replaced with real calculations later.
    """
    with _store_lock:
        rec = _equipment_store.get(equipment_id)

        if not rec:
            return None

    # ----- AGE FACTOR -----
    year = rec.get("year")
    if year:
        age = max(0, datetime.utcnow().year - year)
    else:
        age = 5  # assume mid-age if unknown

    age_penalty = min(40, age * 3)

    # ----- USAGE FACTOR (mocked) -----
    usage_hours = rec.get("usage_hours", 200)  # placeholder
    usage_penalty = min(30, usage_hours / 100)

    # ----- WEAR FACTOR -----
    wear_factor = rec.get("wear_factor", 1)  # default no wear
    wear_penalty = min(20, wear_factor * 5)

    # ----- MODEL RELIABILITY (mock) -----
    model = rec.get("model", "").lower()
    reliability_bonus = 5 if "premium" in model else 0

    # ----- FINAL HEALTH SCORE -----
    base_score = 100 - (age_penalty + usage_penalty + wear_penalty)
    final_score = max(0, min(100, base_score + reliability_bonus))

    return {
        "equipment_id": equipment_id,
        "health_score": int(final_score),
        "details": {
            "age_years": age,
            "usage_hours": usage_hours,
            "wear_factor": wear_factor,
            "reliability_bonus": reliability_bonus,
            "age_penalty": age_penalty,
            "usage_penalty": usage_penalty,
            "wear_penalty": wear_penalty,
        },
        "calculated_at": datetime.utcnow(),
    }

def generate_maintenance_schedule(equipment_id: str) -> Dict[str, Any]:
    """
    Predictive maintenance schedule engine.
    Uses age, usage, wear factor to calculate:
    - next maintenance due date
    - recommended tasks
    - priority level
    """

    with _store_lock:
        rec = _equipment_store.get(equipment_id)
        if not rec:
            return None

    # Extract metadata
    year = rec.get("year", datetime.utcnow().year - 5)
    age = datetime.utcnow().year - year

    usage_hours = rec.get("usage_hours", 200)
    wear_factor = rec.get("wear_factor", 1)

    # ----- MAINTENANCE INTERVAL -----
    # Rule: every 6 months or every ~300 hours (mock logic)
    base_interval_days = 180
    usage_penalty_days = int(usage_hours / 2)  # more hours → shorter interval
    wear_penalty_days = wear_factor * 10

    interval = max(30, base_interval_days - usage_penalty_days - wear_penalty_days)

    # Mock last maintenance date
    last_maintenance = rec.get("last_maintenance_at", datetime.utcnow())
    if isinstance(last_maintenance, str):
        last_maintenance = datetime.fromisoformat(last_maintenance)

    next_due = last_maintenance + timedelta(days=interval)
    days_left = (next_due - datetime.utcnow()).days

    # ----- PRIORITY RULES -----
    if days_left < 0:
        priority = "overdue"
    elif days_left <= 15:
        priority = "high"
    elif days_left <= 45:
        priority = "medium"
    else:
        priority = "low"

    # ----- RECOMMENDED TASKS -----
    tasks = ["General inspection", "Lubrication", "Clean filters"]

    if "tractor" in rec["type"].lower():
        tasks += ["Engine oil change", "Hydraulic check"]

    if wear_factor > 1:
        tasks.append("Replace worn parts")

    if usage_hours > 300:
        tasks.append("Full service recommended (high usage)")

    return {
        "equipment_id": equipment_id,
        "next_maintenance_date": next_due,
        "days_left": days_left,
        "priority": priority,
        "recommended_tasks": tasks,
        "calculated_at": datetime.utcnow(),
        "details": {
            "age_years": age,
            "usage_hours": usage_hours,
            "wear_factor": wear_factor,
            "base_interval_days": base_interval_days,
            "computed_interval_days": interval
        },
    }

def get_maintenance_reminders(equipment_id: str, days_ahead: int = 30) -> Dict[str, Any]:
    """
    Returns a reminder object for a single equipment:
    - if overdue
    - if due within `days_ahead`
    - otherwise 'ok'
    """
    with _store_lock:
        rec = _equipment_store.get(equipment_id)
        if not rec:
            return None

    schedule = generate_maintenance_schedule(equipment_id)
    if not schedule:
        return None

    next_due = schedule.get("next_maintenance_date")
    if isinstance(next_due, str):
        next_due = datetime.fromisoformat(next_due)

    days_left = schedule.get("days_left", (next_due - datetime.utcnow()).days)

    if days_left < 0:
        status = "overdue"
        message = f"Maintenance overdue by {-days_left} days."
    elif days_left <= days_ahead:
        status = "due_soon"
        message = f"Maintenance due in {days_left} days."
    else:
        status = "ok"
        message = f"Next maintenance in {days_left} days."

    return {
        "equipment_id": equipment_id,
        "status": status,
        "days_left": days_left,
        "message": message,
        "next_maintenance_date": next_due,
        "recommended_tasks": schedule.get("recommended_tasks", []),
        "priority": schedule.get("priority"),
        "calculated_at": datetime.utcnow(),
    }


def get_all_maintenance_reminders(days_ahead: int = 30) -> Dict[str, Any]:
    """
    Returns reminders for all equipment in the in-memory store.
    Useful for admin dashboards to list upcoming/overdue maintenances.
    """
    reminders: List[Dict[str, Any]] = []
    with _store_lock:
        equipment_ids = list(_equipment_store.keys())

    for eid in equipment_ids:
        rem = get_maintenance_reminders(eid, days_ahead=days_ahead)
        if rem:
            reminders.append(rem)

    # Optionally sort: overdue first, then high priority, then due_soon
    def sort_key(r):
        status_order = {"overdue": 0, "due_soon": 1, "ok": 2}
        prio_map = {"overdue": 0, "high": 0, "medium": 1, "low": 2}
        return (status_order.get(r["status"], 3), prio_map.get(r.get("priority", "low"), 2), r["days_left"])

    reminders.sort(key=sort_key)
    return {"count": len(reminders), "reminders": reminders}

def mark_equipment_maintenance_done(
    equipment_id: str,
    performed_at: datetime = None,
    notes: str = ""
) -> Dict[str, Any]:
    """
    Marks maintenance as completed for the equipment.
    - Updates last_maintenance_at
    - Resets wear_factor a bit (mock)
    - Resets usage hours a bit (mock)
    - Stores maintenance logs in-memory (expandable)

    Returns the updated equipment record & next schedule.
    """

    if performed_at is None:
        performed_at = datetime.utcnow()

    with _store_lock:
        rec = _equipment_store.get(equipment_id)
        if not rec:
            return None

        # Update last maintenance date
        rec["last_maintenance_at"] = performed_at.isoformat()

        # Reset or reduce wear factor (mock logic)
        wear = rec.get("wear_factor", 1)
        rec["wear_factor"] = max(1, wear - 0.5)

        # Reduce usage hours a bit (maintenance effect)
        usage = rec.get("usage_hours", 200)
        rec["usage_hours"] = max(0, usage - 50)

        # Add maintenance history log
        history_entry = {
            "performed_at": performed_at.isoformat(),
            "notes": notes,
            "usage_hours_before": usage,
            "wear_factor_before": wear,
        }

        if "maintenance_history" not in rec:
            rec["maintenance_history"] = []

        rec["maintenance_history"].append(history_entry)

    # Return updated record + new schedule
    new_schedule = generate_maintenance_schedule(equipment_id)
    return {
        "equipment": rec,
        "next_schedule": new_schedule,
        "maintenance_recorded_at": performed_at,
    }

def get_major_service_alerts(equipment_id: str) -> Dict[str, Any]:
    """
    Major Service Due Alert Engine (Feature #209)

    Considers:
    - Health score
    - Usage hours
    - Wear factor
    - Time since last maintenance
    - Next maintenance schedule
    - Age-based major service cycles

    Returns high-level alerts and breakdown risk.
    """

    with _store_lock:
        rec = _equipment_store.get(equipment_id)
        if not rec:
            return None

    # Get health score
    health = compute_equipment_health(equipment_id)
    health_score = health["health_score"]

    # Usage and wear
    usage_hours = rec.get("usage_hours", 200)
    wear_factor = rec.get("wear_factor", 1)

    # Maintenance schedule
    schedule = generate_maintenance_schedule(equipment_id)
    days_left = schedule.get("days_left", 0)

    # Determine if equipment is old enough for major service
    year = rec.get("year", datetime.utcnow().year - 5)
    age = datetime.utcnow().year - year
    major_service_cycle_years = 3   # mock rule

    alerts = []
    risk_score = 0

    # ---------------------------
    # HEALTH-BASED ALERTS
    # ---------------------------
    if health_score <= 40:
        alerts.append("Very low equipment health. Major service required.")
        risk_score += 40
    elif health_score <= 60:
        alerts.append("Low health detected. Recommend checking engine & hydraulics.")
        risk_score += 20

    # ---------------------------
    # USAGE-BASED ALERTS
    # ---------------------------
    if usage_hours >= 500:
        alerts.append("High usage hours. Full service recommended.")
        risk_score += 25
    elif usage_hours >= 300:
        alerts.append("Moderate usage. Inspect engine & moving parts.")
        risk_score += 10

    # ---------------------------
    # WEAR FACTOR-BASED ALERTS
    # ---------------------------
    if wear_factor > 2:
        alerts.append("Severe wear detected. Replace worn components immediately.")
        risk_score += 35
    elif wear_factor > 1.5:
        alerts.append("Medium wear detected. Check belt/chain tension & alignment.")
        risk_score += 15

    # ---------------------------
    # MAINTENANCE SCHEDULE ALERTS
    # ---------------------------
    if days_left < 0:
        alerts.append("Major service overdue.")
        risk_score += 30
    elif days_left <= 10:
        alerts.append(f"Major service due soon (in {days_left} days).")
        risk_score += 10

    # ---------------------------
    # AGE-BASED MAJOR SERVICE
    # ---------------------------
    if age % major_service_cycle_years == 0:
        alerts.append("Annual major service cycle reached.")
        risk_score += 20

    # Final risk cap
    risk_score = min(100, risk_score)

    return {
        "equipment_id": equipment_id,
        "major_service_alerts": alerts,
        "risk_score": risk_score,
        "health_score": health_score,
        "usage_hours": usage_hours,
        "wear_factor": wear_factor,
        "days_until_next_service": days_left,
        "calculated_at": datetime.utcnow(),
    }

def log_fuel_usage(
    equipment_id: str,
    liters: float,
    cost: float = 0.0,
    usage_hours: float = 0.0,
    filled_at: datetime = None
) -> Dict[str, Any]:
    """
    Logs fuel usage for equipment.
    - liters: Fuel filled/used
    - cost: Total cost for this refuel/usage
    - usage_hours: Hours used during this fuel cycle
    """

    if filled_at is None:
        filled_at = datetime.utcnow()

    with _store_lock:
        rec = _equipment_store.get(equipment_id)
        if not rec:
            return None

        if "fuel_history" not in rec:
            rec["fuel_history"] = []

        entry = {
            "liters": liters,
            "cost": cost,
            "usage_hours": usage_hours,
            "filled_at": filled_at.isoformat()
        }

        rec["fuel_history"].append(entry)

        # Update usage hours on equipment
        prev_usage = rec.get("usage_hours", 0)
        rec["usage_hours"] = prev_usage + usage_hours

    return entry


def get_fuel_usage_history(equipment_id: str) -> Dict[str, Any]:
    """
    Returns all logged fuel usage for the equipment.
    """
    with _store_lock:
        rec = _equipment_store.get(equipment_id)
        if not rec:
            return None

        return {
            "equipment_id": equipment_id,
            "count": len(rec.get("fuel_history", [])),
            "history": rec.get("fuel_history", [])
        }


def compute_fuel_efficiency(equipment_id: str) -> Dict[str, Any]:
    """
    Computes fuel efficiency metrics:
    - liters per hour
    - cost per liter
    - average cost per hour
    - abnormal usage alerts (mock)
    """

    with _store_lock:
        rec = _equipment_store.get(equipment_id)
        if not rec:
            return None

        history = rec.get("fuel_history", [])
        if not history:
            return {
                "equipment_id": equipment_id,
                "efficiency_score": None,
                "message": "No fuel logs available",
            }

    total_liters = sum(h["liters"] for h in history)
    total_cost = sum(h["cost"] for h in history)
    total_hours = sum(h["usage_hours"] for h in history)

    if total_hours == 0:
        return {
            "equipment_id": equipment_id,
            "efficiency_score": None,
            "message": "No usage hours recorded",
        }

    liters_per_hour = total_liters / total_hours
    cost_per_liter = total_cost / total_liters if total_liters > 0 else 0
    cost_per_hour = total_cost / total_hours

    # Detect abnormal fuel usage (mock logic)
    alerts = []
    if liters_per_hour > 5:
        alerts.append("High fuel consumption detected.")
    elif liters_per_hour < 1:
        alerts.append("Very low consumption — verify data.")

    # Efficiency score (mock)
    efficiency_score = max(0, min(100, int(100 - (liters_per_hour * 10))))

    return {
        "equipment_id": equipment_id,
        "fuel_efficiency": {
            "liters_per_hour": round(liters_per_hour, 2),
            "cost_per_liter": round(cost_per_liter, 2),
            "cost_per_hour": round(cost_per_hour, 2),
            "efficiency_score": efficiency_score,
            "alerts": alerts,
        },
        "calculated_at": datetime.utcnow(),
    }

def compute_breakdown_probability(equipment_id: str) -> Dict[str, Any]:
    """
    Compute a breakdown probability (0-100) based on multiple signals:
    - low health -> higher risk
    - high usage_hours -> higher risk
    - high wear_factor -> higher risk
    - overdue maintenance -> higher risk
    - poor fuel efficiency -> higher risk
    - missing/low spare parts -> higher risk
    Returns a dict with score, component breakdown and recommendations.
    """

    # local imports to avoid circular import at module load
    from app.services.farmer.spare_parts_service import get_parts_for_equipment
    # compute existing signals
    rec = None
    with _store_lock:
        rec = _equipment_store.get(equipment_id)
        if not rec:
            return None

    health_obj = compute_equipment_health(equipment_id) or {}
    health_score = health_obj.get("health_score", 80)

    usage_hours = rec.get("usage_hours", 0)
    wear_factor = rec.get("wear_factor", 1)

    # maintenance schedule
    schedule = generate_maintenance_schedule(equipment_id) or {}
    days_left = schedule.get("days_left", 999)

    # fuel efficiency (may return message if no data)
    fuel_eff = compute_fuel_efficiency(equipment_id) or {}
    liters_per_hour = None
    if "fuel_efficiency" in fuel_eff and fuel_eff["fuel_efficiency"].get("liters_per_hour") is not None:
        liters_per_hour = fuel_eff["fuel_efficiency"]["liters_per_hour"]

    # parts assigned / availability
    parts_info = get_parts_for_equipment(equipment_id) or {}
    missing_parts = 0
    low_stock_parts = 0
    for item in parts_info.get("items", []):
        part = item.get("part")
        if not part:
            missing_parts += 1
        else:
            if part.get("quantity", 0) <= part.get("min_stock_threshold", 1):
                low_stock_parts += 1

    # Major service alerts influence
    major_alerts = get_major_service_alerts(equipment_id) or {}
    major_alert_count = len(major_alerts.get("major_service_alerts", []))

    # Compose risk factors (normalized to 0-100)
    # health contribution (lower health -> higher risk)
    health_risk = max(0, 100 - health_score)  # 0..100

    # usage contribution: scale usage_hours into 0..30
    usage_risk = min(30, int((usage_hours / 1000) * 30))  # 0..30

    # wear contribution: wear_factor * scale
    wear_risk = min(25, int((wear_factor - 1) * 12)) if wear_factor > 1 else 0  # 0..25

    # maintenance contribution:
    if days_left < 0:
        maintenance_risk = 30
    elif days_left <= 7:
        maintenance_risk = 20
    elif days_left <= 30:
        maintenance_risk = 10
    else:
        maintenance_risk = 0

    # fuel contribution:
    fuel_risk = 0
    if liters_per_hour is not None:
        if liters_per_hour > 6:
            fuel_risk = 15
        elif liters_per_hour > 4:
            fuel_risk = 8

    # parts contribution:
    parts_risk = 0
    parts_risk += min(20, missing_parts * 10)  # missing parts are costly
    parts_risk += min(15, low_stock_parts * 5)

    # major-alerts add risk
    major_risk = min(20, major_alert_count * 8)

    # Weighted sum (tunable)
    total = (
        health_risk * 0.30 +
        usage_risk * 0.15 +
        wear_risk * 0.15 +
        maintenance_risk * 0.15 +
        fuel_risk * 0.10 +
        parts_risk * 0.10 +
        major_risk * 0.05
    )

    unified = int(min(100, total))

    # Recommendations
    recommendations = []
    if unified >= 80:
        recommendations.append("Critical risk: stop use and schedule immediate major service.")
    elif unified >= 60:
        recommendations.append("High risk: schedule deep inspection and replace critical parts.")
    elif unified >= 40:
        recommendations.append("Moderate risk: monitor closely, consider preventive maintenance.")
    else:
        recommendations.append("Low risk: normal operations continue, follow routine maintenance.")

    if missing_parts > 0 or low_stock_parts > 0:
        recommendations.append("Check spare parts: missing or low stock could cause delays during repair.")

    if days_left < 0:
        recommendations.append("Maintenance overdue — service immediately to reduce breakdown risk.")

    if liters_per_hour and liters_per_hour > 6:
        recommendations.append("High fuel consumption observed — inspect engine & fuel system.")

    return {
        "equipment_id": equipment_id,
        "breakdown_probability": unified,
        "breakdown_components": {
            "health_risk": health_risk,
            "usage_risk": usage_risk,
            "wear_risk": wear_risk,
            "maintenance_risk": maintenance_risk,
            "fuel_risk": fuel_risk,
            "parts_risk": parts_risk,
            "major_alert_risk": major_risk,
        },
        "details": {
            "health_score": health_score,
            "usage_hours": usage_hours,
            "wear_factor": wear_factor,
            "days_until_next_service": days_left,
            "liters_per_hour": liters_per_hour,
            "missing_parts": missing_parts,
            "low_stock_parts": low_stock_parts,
            "major_service_alerts": major_alerts.get("major_service_alerts", []),
        },
        "recommendations": recommendations,
        "calculated_at": datetime.utcnow(),
    }

def list_high_risk_equipment(threshold: int = 60) -> Dict[str, Any]:
    """
    Returns a list of equipment whose breakdown risk >= threshold.
    Default threshold: 60 (high-risk).
    """

    results = []

    with _store_lock:
        equipment_ids = list(_equipment_store.keys())

    for eid in equipment_ids:
        risk_info = compute_breakdown_probability(eid)
        if not risk_info:
            continue
        score = risk_info.get("breakdown_probability", 0)

        if score >= threshold:
            results.append({
                "equipment_id": eid,
                "breakdown_probability": score,
                "recommendations": risk_info.get("recommendations", []),
                "details": risk_info.get("details", {}),
            })

    # Sort highest risk first
    results.sort(key=lambda x: x["breakdown_probability"], reverse=True)

    return {
        "threshold": threshold,
        "count": len(results),
        "high_risk_equipment": results,
        "timestamp": datetime.utcnow(),
    }

def compute_equipment_utilization(equipment_id: str) -> Optional[Dict[str, Any]]:
    """
    Computes utilization analytics for the equipment.
    Uses:
    - usage_hours (from fuel logs + manual updates)
    - estimated daily usage pattern (mock)
    - underutilized / overused status
    - utilization score (0–100)
    """

    with _store_lock:
        rec = _equipment_store.get(equipment_id)
        if not rec:
            return None

    usage_hours = rec.get("usage_hours", 0)

    # Estimate usage duration period (mock)
    created_at = rec.get("created_at")
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at)

    days_active = max(1, (datetime.utcnow() - created_at).days)

    avg_daily_usage = usage_hours / days_active

    # Detect idle time
    # Mock rule: <0.5 hr/day -> idle
    if avg_daily_usage < 0.5:
        idle_status = "mostly_idle"
    elif avg_daily_usage < 2:
        idle_status = "light_use"
    else:
        idle_status = "heavy_use"

    # Utilization score depends on ideal usage range (0.5–4 hours/day)
    if avg_daily_usage < 0.5:
        utilization_score = int(avg_daily_usage * 20)  # very low usage
    elif avg_daily_usage > 5:
        utilization_score = max(0, 100 - int((avg_daily_usage - 5) * 20))
    else:
        utilization_score = min(100, int((avg_daily_usage / 4) * 100))

    # Overuse/underuse flags
    alerts = []

    if avg_daily_usage < 0.3:
        alerts.append("Equipment is severely underutilized.")
    elif avg_daily_usage < 1:
        alerts.append("Equipment is lightly utilized.")
    elif avg_daily_usage > 6:
        alerts.append("Equipment appears to be overused — check for wear.")
    elif avg_daily_usage > 4:
        alerts.append("High daily usage — increased maintenance recommended.")

    # Mock usage heatmap
    heatmap = {
        "morning": round(avg_daily_usage * 0.3, 2),
        "afternoon": round(avg_daily_usage * 0.5, 2),
        "evening": round(avg_daily_usage * 0.2, 2),
    }

    return {
        "equipment_id": equipment_id,
        "usage_hours_total": usage_hours,
        "days_active": days_active,
        "avg_daily_usage": round(avg_daily_usage, 2),
        "utilization_score": utilization_score,
        "usage_status": idle_status,
        "alerts": alerts,
        "usage_heatmap": heatmap,
        "calculated_at": datetime.utcnow(),
    }


def compute_all_equipment_utilization() -> Dict[str, Any]:
    """
    Returns utilization summary for all equipment.
    Useful for dashboards.
    """

    summary = []

    with _store_lock:
        equipment_ids = list(_equipment_store.keys())

    for eid in equipment_ids:
        util = compute_equipment_utilization(eid)
        if util:
            summary.append(util)

    # Sort by utilization score descending
    summary.sort(key=lambda x: x["utilization_score"], reverse=True)

    return {
        "count": len(summary),
        "utilization_summary": summary,
        "timestamp": datetime.utcnow(),
    }

def compute_idle_status(equipment_id: str) -> Optional[Dict[str, Any]]:
    """
    Computes idle status of equipment based on:
    - last maintenance date
    - last fuel usage
    - usage_hours pattern
    - avg daily usage from utilization function
    """

    with _store_lock:
        rec = _equipment_store.get(equipment_id)
        if not rec:
            return None

    util = compute_equipment_utilization(equipment_id)
    if not util:
        return None

    avg_daily_usage = util["avg_daily_usage"]
    days_active = util["days_active"]

    # Determine last known activity
    last_activity = None

    # Check maintenance
    if "last_maintenance_at" in rec:
        try:
            last_activity = datetime.fromisoformat(rec["last_maintenance_at"])
        except:
            pass

    # Check fuel history
    fuel_history = rec.get("fuel_history", [])
    if fuel_history:
        last_fuel_time = datetime.fromisoformat(fuel_history[-1]["filled_at"])
        if not last_activity or last_fuel_time > last_activity:
            last_activity = last_fuel_time

    # If absolutely nothing, assume created_at
    if not last_activity:
        created_at = rec.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        last_activity = created_at

    idle_days = (datetime.utcnow() - last_activity).days

    # Determine idle score
    if idle_days >= 30:
        idle_score = 90
        idle_status = "critically_idle"
    elif idle_days >= 14:
        idle_score = 70
        idle_status = "idle"
    elif idle_days >= 7:
        idle_score = 40
        idle_status = "partially_idle"
    else:
        idle_score = 10
        idle_status = "active"

    # Recommendations
    recommendations = []
    if idle_days >= 30:
        recommendations.append("Equipment unused for 30+ days — consider inspection before next use.")
        recommendations.append("Reassign or rotate usage to avoid deterioration.")
    elif idle_days >= 14:
        recommendations.append("Equipment is idle. Consider scheduled weekly rotation or lending.")
    elif idle_days >= 7:
        recommendations.append("Lightly idle — track usage next week.")

    # Underutilization suggestion
    if avg_daily_usage < 0.5:
        recommendations.append("Underutilized — consider assigning to more tasks.")

    return {
        "equipment_id": equipment_id,
        "idle_days": idle_days,
        "idle_score": idle_score,
        "idle_status": idle_status,
        "avg_daily_usage": avg_daily_usage,
        "last_activity_at": last_activity,
        "recommendations": recommendations,
        "calculated_at": datetime.utcnow(),
    }


def list_idle_equipment(min_idle_days: int = 7) -> Dict[str, Any]:
    """
    Lists all equipment that are idle for at least `min_idle_days`.
    Default: 7 days
    """

    result = []

    with _store_lock:
        equipment_ids = list(_equipment_store.keys())

    for eid in equipment_ids:
        idle_info = compute_idle_status(eid)
        if not idle_info:
            continue

        if idle_info["idle_days"] >= min_idle_days:
            result.append(idle_info)

    # Sort by idle days descending
    result.sort(key=lambda x: x["idle_days"], reverse=True)

    return {
        "min_idle_days": min_idle_days,
        "count": len(result),
        "idle_equipment": result,
        "timestamp": datetime.utcnow(),
    }

_worker_operations: Dict[str, List[Dict[str, Any]]] = {}
_worker_lock = Lock()


def assign_worker_to_equipment(
    worker_id: str,
    equipment_id: str,
    start_time: datetime = None,
    notes: str = ""
) -> Optional[Dict[str, Any]]:
    """
    Assigns a worker to equipment and logs operation start.
    """

    with _store_lock:
        eq = _equipment_store.get(equipment_id)
        if not eq:
            return None

    if start_time is None:
        start_time = datetime.utcnow()

    entry = {
        "worker_id": worker_id,
        "equipment_id": equipment_id,
        "start_time": start_time.isoformat(),
        "end_time": None,
        "duration_hours": None,
        "notes": notes,
        "completed": False,
    }

    with _worker_lock:
        if equipment_id not in _worker_operations:
            _worker_operations[equipment_id] = []
        _worker_operations[equipment_id].append(entry)

    return entry


def complete_worker_operation(
    worker_id: str,
    equipment_id: str,
    end_time: datetime = None
) -> Optional[Dict[str, Any]]:
    """
    Completes a worker's operation and calculates duration.
    Also updates equipment usage hours.
    """

    with _worker_lock:
        ops = _worker_operations.get(equipment_id, [])
        # find ongoing operation
        active = None
        for op in ops:
            if op["worker_id"] == worker_id and not op["completed"]:
                active = op
                break

        if not active:
            return None

    if end_time is None:
        end_time = datetime.utcnow()

    start = datetime.fromisoformat(active["start_time"])
    duration = (end_time - start).total_seconds() / 3600
    duration = round(duration, 2)

    active["end_time"] = end_time.isoformat()
    active["duration_hours"] = duration
    active["completed"] = True

    # Update equipment usage hours
    with _store_lock:
        eq = _equipment_store.get(equipment_id)
        if eq:
            prev = eq.get("usage_hours", 0)
            eq["usage_hours"] = prev + duration

    return active


def get_worker_assignments(equipment_id: str) -> Dict[str, Any]:
    """
    Returns all worker operations for a specific equipment.
    """
    with _worker_lock:
        ops = _worker_operations.get(equipment_id, [])
        return {
            "equipment_id": equipment_id,
            "count": len(ops),
            "operations": ops
        }


def list_all_worker_operations() -> Dict[str, Any]:
    """
    Returns all worker-equipment operation logs.
    """
    all_ops = []

    with _worker_lock:
        for eq_ops in _worker_operations.values():
            all_ops.extend(eq_ops)

    return {
        "count": len(all_ops),
        "operations": all_ops
    }

def compute_equipment_operating_cost(equipment_id: str) -> Optional[Dict[str, Any]]:
    """
    Computes operating cost breakdown for equipment (mock).
    - fuel: sum of fuel_history costs
    - parts: sum of consumption_history * unit_price
    - labor: estimate from worker operations or default labor_cost_per_hour * hours
    - maintenance: estimate from maintenance_history (mock)
    Returns:
      {
        equipment_id,
        total_fuel_cost,
        total_parts_cost,
        total_labor_cost,
        total_maintenance_cost,
        total_operating_cost,
        usage_hours,
        cost_per_hour,
        breakdown: {...}
      }

    Notes:
    - This is a heuristic estimator (no DB). Fields not present default sensibly.
    """
    with _store_lock:
        rec = _equipment_store.get(equipment_id)
        if not rec:
            return None

    # ----- Fuel cost -----
    fuel_hist = rec.get("fuel_history", [])
    total_fuel_cost = sum((entry.get("cost") or 0.0) for entry in fuel_hist)

    # ----- Parts cost -----
    parts_cost = 0.0
    part_assigns = {}
    # try to sum consumption_history amounts * unit_price
    try:
        from app.services.farmer.spare_parts_service import list_parts, get_part
    except Exception:
        get_part = None

    # If spare parts store exists, iterate consumption_history on parts
    # fallback: if equipment has maintenance_history with 'parts_cost' use that
    if get_part:
        # iterate all parts and sum consumption entries that reference this equipment (best-effort)
        parts_info = []
        # list_parts returns items; avoid calling list_parts() heavy - instead try to inspect assignment store
        # Simplified approach: if part records exist, sum their consumption_history (not linked to equipment)
        try:
            all_parts = list_parts().get("items", [])
            for p in all_parts:
                for ch in p.get("consumption_history", []):
                    # consumption_history entries do not include equipment_id in our model,
                    # so we aggregate all parts consumption as farm-wide part cost and allocate proportionally.
                    parts_cost += ch.get("quantity", 0) * (p.get("unit_price", 0.0) or 0.0)
        except Exception:
            parts_cost = 0.0

    # If equipment has maintenance_history with estimated costs, sum them
    maintenance_hist = rec.get("maintenance_history", [])
    total_maintenance_cost = 0.0
    for m in maintenance_hist:
        # we may have added no explicit costs — accept a `estimated_cost` field if present
        total_maintenance_cost += float(m.get("estimated_cost", 0.0))

    # ----- Labor cost estimate -----
    # Prefer explicit labor_cost_per_hour on equipment, else default value
    labor_cost_per_hour = float(rec.get("labor_cost_per_hour", 10.0))  # currency per hour default
    usage_hours = float(rec.get("usage_hours", 0.0))
    # If worker operations exist, respect recorded durations (sum)
    try:
        # _worker_operations defined in this service file
        total_logged_hours = 0.0
        with _worker_lock:
            ops = _worker_operations.get(equipment_id, [])
            for op in ops:
                if op.get("duration_hours"):
                    total_logged_hours += float(op["duration_hours"])
        # if logged hours present, prefer that (otherwise fallback to usage_hours)
        hours_for_labor = total_logged_hours if total_logged_hours > 0 else usage_hours
    except Exception:
        hours_for_labor = usage_hours

    total_labor_cost = round(hours_for_labor * labor_cost_per_hour, 2)

    # ----- Total operating cost -----
    total_operating_cost = round(total_fuel_cost + parts_cost + total_labor_cost + total_maintenance_cost, 2)

    cost_per_hour = None
    if hours_for_labor > 0:
        cost_per_hour = round(total_operating_cost / hours_for_labor, 2)
    else:
        cost_per_hour = None

    return {
        "equipment_id": equipment_id,
        "total_fuel_cost": round(total_fuel_cost, 2),
        "total_parts_cost": round(parts_cost, 2),
        "total_labor_cost": round(total_labor_cost, 2),
        "total_maintenance_cost": round(total_maintenance_cost, 2),
        "total_operating_cost": total_operating_cost,
        "usage_hours": usage_hours,
        "hours_used_for_calculation": hours_for_labor,
        "cost_per_hour": cost_per_hour,
        "breakdown": {
            "fuel_cost": round(total_fuel_cost, 2),
            "parts_cost": round(parts_cost, 2),
            "labor_cost": round(total_labor_cost, 2),
            "maintenance_cost": round(total_maintenance_cost, 2),
        },
        "calculated_at": datetime.utcnow(),
    }


def estimate_equipment_depreciation(equipment_id: str, years: int = 5, method: str = "straight_line") -> Optional[Dict[str, Any]]:
    """
    Estimate depreciation schedule for the equipment.
    - Expects equipment record to have 'purchase_price' and 'purchase_date' optionally.
    - Method: 'straight_line' or 'declining_balance' (simple stub)
    Returns:
      {
        equipment_id,
        purchase_price,
        years,
        method,
        annual_schedule: [ { year: 1, depreciation: x, book_value: y }, ... ],
        total_depreciation,
      }
    """

    with _store_lock:
        rec = _equipment_store.get(equipment_id)
        if not rec:
            return None

    purchase_price = float(rec.get("purchase_price", 0.0))
    purchase_date = rec.get("purchase_date")
    if isinstance(purchase_date, str):
        try:
            purchase_date = datetime.fromisoformat(purchase_date)
        except Exception:
            purchase_date = None

    if purchase_price <= 0:
        # fallback: estimate purchase_price from mock (e.g., 1000 for small equipment)
        purchase_price = float(rec.get("estimated_purchase_price", 1000.0))

    schedule = []
    book_value = purchase_price
    total_depr = 0.0

    if method == "straight_line":
        annual = round(purchase_price / max(1, years), 2)
        for y in range(1, years + 1):
            book_value = round(book_value - annual, 2)
            total_depr += annual
            schedule.append({"year": y, "depreciation": annual, "book_value": max(0.0, book_value)})
    else:
        # simple declining balance: 1.5 / years factor
        rate = min(0.5, 1.5 / max(1, years))
        for y in range(1, years + 1):
            depr = round(book_value * rate, 2)
            book_value = round(book_value - depr, 2)
            total_depr += depr
            schedule.append({"year": y, "depreciation": depr, "book_value": max(0.0, book_value)})

    return {
        "equipment_id": equipment_id,
        "purchase_price": purchase_price,
        "years": years,
        "method": method,
        "annual_schedule": schedule,
        "total_depreciation": round(total_depr, 2),
        "estimated_book_value": round(book_value, 2),
        "calculated_at": datetime.utcnow(),
    }


def compute_equipment_roi(equipment_id: str, analysis_period_years: int = 1) -> Optional[Dict[str, Any]]:
    """
    Compute a mock ROI for the equipment over the analysis_period_years.
    Heuristic used:
      - Estimate "revenue attributable to equipment" as:
          productivity_proxy_per_hour * hours_used
        where productivity_proxy_per_hour is a configurable field (default 10 currency/hr)
      - Subtract operating costs + depreciation for the period to get estimated profit
      - ROI = (estimated_profit / (purchase_price + operating_costs_for_period)) * 100
    Returns:
      {
        equipment_id,
        estimated_revenue,
        operating_costs,
        depreciation_for_period,
        estimated_profit,
        roi_percent,
        explanation
      }

    NOTE: This is a heuristic placeholder for UI and analysis; replace with real allocation later.
    """

    with _store_lock:
        rec = _equipment_store.get(equipment_id)
        if not rec:
            return None

    # Operating costs (annualized to period)
    cost_summary = compute_equipment_operating_cost(equipment_id)
    if not cost_summary:
        return None

    # purchase price / depreciation
    purchase_price = float(rec.get("purchase_price", rec.get("estimated_purchase_price", 1000.0)))

    # Productivity proxy (value generated per hour of equipment use). Default 10 currency/hr.
    productivity_per_hour = float(rec.get("productivity_value_per_hour", 10.0))

    # hours used in analysis period: approximate by usage_hours * (period_years fraction)
    # If equipment usage_hours is cumulative since creation, assume uniform distribution and prorate
    total_usage_hours = float(rec.get("usage_hours", 0.0))
    # Simple heuristic: assume usage_hours is for lifetime; calculate proportion for analysis period (1 year)
    # If created within last year, compute approximate hours_in_period = min(total_usage_hours, total_usage_hours)
    hours_in_period = total_usage_hours if analysis_period_years >= 1 else total_usage_hours * (analysis_period_years / 1.0)
    # A safer fallback: if total_usage_hours == 0, use recorded worker ops duration
    if hours_in_period <= 0:
        try:
            with _worker_lock:
                ops = _worker_operations.get(equipment_id, [])
                hours_in_period = sum(op.get("duration_hours", 0) for op in ops)
        except Exception:
            hours_in_period = 0

    estimated_revenue = round(hours_in_period * productivity_per_hour, 2)

    # Operating costs for period: prorate operating cost
    total_operating_cost = float(cost_summary.get("total_operating_cost", 0.0))
    # If lifetime usage_hours present, prorate by hours_in_period / total_usage_hours; else assume full
    if float(rec.get("usage_hours", 0.0)) > 0:
        operating_costs_period = round(total_operating_cost * (hours_in_period / max(1.0, float(rec.get("usage_hours", 0.0)))), 2)
    else:
        operating_costs_period = total_operating_cost

    # Depreciation for the period (use straight_line default across 5 years)
    depr_summary = estimate_equipment_depreciation(equipment_id, years=5, method="straight_line")
    # sum first `analysis_period_years` years depreciation
    depr_for_period = 0.0
    if depr_summary and depr_summary.get("annual_schedule"):
        years_to_sum = min(len(depr_summary["annual_schedule"]), max(1, int(analysis_period_years)))
        depr_for_period = sum(item["depreciation"] for item in depr_summary["annual_schedule"][:years_to_sum])

    estimated_profit = round(estimated_revenue - (operating_costs_period + depr_for_period), 2)

    denom = (purchase_price + operating_costs_period)
    roi_percent = None
    if denom and denom != 0:
        roi_percent = round((estimated_profit / denom) * 100, 2)
    else:
        roi_percent = None

    explanation = (
        f"Estimated revenue uses productivity proxy {productivity_per_hour}/hr * {hours_in_period} hrs. "
        f"Operating costs for period (prorated): {operating_costs_period}. "
        f"Depreciation for period: {depr_for_period}."
    )

    return {
        "equipment_id": equipment_id,
        "analysis_period_years": analysis_period_years,
        "estimated_revenue": estimated_revenue,
        "operating_costs": operating_costs_period,
        "depreciation": depr_for_period,
        "estimated_profit": estimated_profit,
        "purchase_price": purchase_price,
        "roi_percent": roi_percent,
        "explanation": explanation,
        "calculated_at": datetime.utcnow(),
    }

# Knowledge base: crop → stage → required equipment types
_CROP_EQUIP_KB = {
    "wheat": {
        "land_preparation": ["tractor", "cultivator", "rotavator"],
        "sowing": ["seed drill", "tractor"],
        "irrigation": ["water_pump"],
        "fertilization": ["sprayer", "tractor"],
        "weed_control": ["sprayer", "tractor"],
        "harvesting": ["combine harvester", "reaper"]
    },
    "rice": {
        "land_preparation": ["tractor", "rotavator", "puddler"],
        "transplanting": ["rice transplanter"],
        "irrigation": ["water_pump"],
        "crop_protection": ["boom sprayer", "tractor"],
        "harvesting": ["paddy harvester"]
    },
    "maize": {
        "land_preparation": ["tractor", "cultivator"],
        "sowing": ["planter", "tractor"],
        "fertilization": ["sprayer", "tractor"],
        "harvesting": ["combine harvester"]
    }
}


def get_equipment_suitability_score(equipment_id: str, crop: str, stage: str) -> Optional[Dict[str, Any]]:
    """
    Computes a suitability score (0–100) of equipment for a given crop and stage.
    Factors:
    - required equipment types match
    - health score
    - idle status
    - seasonal usage (mock)
    """

    with _store_lock:
        eq = _equipment_store.get(equipment_id)
        if not eq:
            return None

    crop = crop.lower()
    stage = stage.lower()

    if crop not in _CROP_EQUIP_KB or stage not in _CROP_EQUIP_KB[crop]:
        return {
            "equipment_id": equipment_id,
            "crop": crop,
            "stage": stage,
            "suitability_score": None,
            "message": "No suitability rules found for crop/stage."
        }

    required_types = _CROP_EQUIP_KB[crop][stage]
    eq_type = eq.get("type", "").lower()

    # Type match score
    if eq_type in required_types:
        type_score = 50
    else:
        type_score = 10  # still allow partial use if farmer improvises

    # Health Influence
    health = compute_equipment_health(equipment_id)
    health_score = health.get("health_score", 70)
    health_weight = health_score * 0.2  # 20%

    # Idle Influence
    idle = compute_idle_status(equipment_id)
    idle_days = idle.get("idle_days", 0)

    if idle_days < 7:
        idle_score = 20
    elif idle_days < 20:
        idle_score = 10
    else:
        idle_score = 0

    final_score = int(min(100, type_score + health_weight + idle_score))

    label = "poor"
    if final_score >= 80:
        label = "ideal"
    elif final_score >= 60:
        label = "good"
    elif final_score >= 40:
        label = "moderate"

    return {
        "equipment_id": equipment_id,
        "crop": crop,
        "stage": stage,
        "suitability_score": final_score,
        "label": label,
        "details": {
            "required_types": required_types,
            "equipment_type": eq_type,
            "health_score": health_score,
            "idle_days": idle_days,
            "type_match_score": type_score,
            "idle_score": idle_score
        },
        "calculated_at": datetime.utcnow()
    }


def recommend_equipment_for_crop(crop: str, stage: str) -> Dict[str, Any]:
    """
    Recommends BEST equipment for a specific crop & stage based on suitability score.
    """

    crop = crop.lower()
    stage = stage.lower()

    results = []

    if crop not in _CROP_EQUIP_KB:
        return {"crop": crop, "stage": stage, "recommendations": [], "message": "Unknown crop"}

    with _store_lock:
        equipment_ids = list(_equipment_store.keys())

    for eid in equipment_ids:
        score = get_equipment_suitability_score(eid, crop, stage)
        if score and score.get("suitability_score") is not None:
            results.append(score)

    results.sort(key=lambda x: x["suitability_score"], reverse=True)

    return {
        "crop": crop,
        "stage": stage,
        "count": len(results),
        "recommendations": results[:5],  # top 5
        "timestamp": datetime.utcnow()
    }

# Default stage durations (days) if not provided by user
_DEFAULT_STAGE_DURATIONS = {
    # stages across common crops (approximate durations, adjustable)
    "land_preparation": 7,
    "sowing": 3,
    "transplanting": 5,
    "irrigation": 1,
    "fertilization": 2,
    "weed_control": 2,
    "crop_protection": 2,
    "harvesting": 7,
    "planting": 3,
    "flowering": 14,
    "vegetative": 21,
    "maturity": 21
}

def _iso(d):
    if isinstance(d, (str,)):
        return d
    return d.isoformat()

def _date_range(start_date, days):
    return [(start_date + timedelta(days=i)) for i in range(days)]

def predict_equipment_demand(
    unit_plans: List[Dict[str, Any]],
    horizon_days: int = 90,
    stage_durations: Dict[str, int] = None
) -> Dict[str, Any]:
    """
    Predict equipment demand from unit_plans over horizon_days.

    unit_plans: list of dicts with:
        {
            "unit_id": int or str,
            "crop": "wheat",
            "start_date": "YYYY-MM-DD" (date when timeline begins for this crop),
            # optionally:
            "stage_start_overrides": {"land_preparation": "YYYY-MM-DD", ...}
            "stages": [ "land_preparation", "sowing", ... ]  # optional explicit stages order
        }

    Returns:
        {
          "horizon_start": iso,
          "horizon_days": n,
          "date_equipment_map": { "YYYY-MM-DD": { "tractor": 3, "sprayer": 1, ... }, ... },
          "unit_schedule": {
              "<unit_id>": [ { "stage": "...", "start_date": iso, "end_date": iso, "required_equipment": [...] }, ... ]
          },
          "summary": { "most_needed_types": [...], "peak_day": "YYYY-MM-DD", ... }
        }
    """
    if stage_durations is None:
        stage_durations = _DEFAULT_STAGE_DURATIONS

    # horizon start is today
    horizon_start = datetime.utcnow().date()
    horizon_end = horizon_start + timedelta(days=horizon_days)

    # initialize date map
    date_equipment_map: Dict[str, Dict[str, int]] = {}
    for d in _date_range(horizon_start, horizon_days + 1):
        date_equipment_map[d.isoformat()] = {}

    unit_schedule: Dict[str, List[Dict[str, Any]]] = {}

    # aggregate required equipment types across units/stages into date_equipment_map
    for plan in unit_plans:
        unit_id = str(plan.get("unit_id", "unknown"))
        crop = plan.get("crop", "").lower()
        start_date_raw = plan.get("start_date")
        # parse start_date (fallback to today)
        try:
            if isinstance(start_date_raw, str):
                start_date = datetime.fromisoformat(start_date_raw).date()
            elif isinstance(start_date_raw, datetime):
                start_date = start_date_raw.date()
            elif isinstance(start_date_raw, (date := None)) and hasattr(start_date_raw, "isoformat"):
                start_date = start_date_raw
            else:
                start_date = horizon_start
        except Exception:
            start_date = horizon_start

        # stages order: either provided or from KB if available
        stages = plan.get("stages")
        if not stages:
            if crop in _CROP_EQUIP_KB:
                stages = list(_CROP_EQUIP_KB[crop].keys())
            else:
                # fallback generic lifecycle
                stages = ["land_preparation", "sowing", "vegetative", "maturity", "harvesting"]

        # compute schedule for unit
        schedule_list = []

        # allow explicit stage_start_overrides
        overrides = plan.get("stage_start_overrides", {})

        cursor_date = start_date
        for stage in stages:
            # if override start date provided for this stage, use it
            if stage in overrides:
                try:
                    cursor_date = datetime.fromisoformat(overrides[stage]).date()
                except Exception:
                    pass

            duration_days = stage_durations.get(stage, stage_durations.get(stage.lower(), 3))
            stage_start = cursor_date
            stage_end = stage_start + timedelta(days=max(0, int(duration_days) - 1))

            # required equipment from KB for this crop/stage
            required = []
            if crop in _CROP_EQUIP_KB and stage in _CROP_EQUIP_KB[crop]:
                required = _CROP_EQUIP_KB[crop][stage]
            elif crop in _CROP_EQUIP_KB and stage.lower() in _CROP_EQUIP_KB[crop]:
                required = _CROP_EQUIP_KB[crop][stage.lower()]

            # write schedule entry
            entry = {
                "stage": stage,
                "start_date": stage_start.isoformat(),
                "end_date": stage_end.isoformat(),
                "required_equipment": required,
                "unit_id": unit_id,
                "crop": crop
            }
            schedule_list.append(entry)

            # map equipment requirement to each date in stage window (within horizon)
            for single_day in _date_range(stage_start, (stage_end - stage_start).days + 1):
                if horizon_start <= single_day <= horizon_end:
                    day_key = single_day.isoformat()
                    if day_key not in date_equipment_map:
                        date_equipment_map[day_key] = {}
                    for eq_type in required:
                        date_equipment_map[day_key][eq_type] = date_equipment_map[day_key].get(eq_type, 0) + 1

            # advance cursor
            cursor_date = stage_end + timedelta(days=1)

        unit_schedule[unit_id] = schedule_list

    # compute summary: most needed types and peak day
    aggregate_counts: Dict[str, int] = {}
    peak_day = None
    peak_total = 0
    for day, mapping in date_equipment_map.items():
        total = sum(mapping.values())
        if total > peak_total:
            peak_total = total
            peak_day = day
        for k, v in mapping.items():
            aggregate_counts[k] = aggregate_counts.get(k, 0) + v

    most_needed = sorted(aggregate_counts.items(), key=lambda x: x[1], reverse=True)

    # compare against available farmer-owned equipment counts (quick check)
    # build inventory counts by type from _equipment_store
    available_counts: Dict[str, int] = {}
    with _store_lock:
        for eid, rec in _equipment_store.items():
            if rec.get("status") == "replaced":
                continue
            etype = rec.get("type", "unknown").lower()
            available_counts[etype] = available_counts.get(etype, 0) + 1

    shortages: List[Dict[str, Any]] = []
    # inspect the peak day mapping for shortages
    if peak_day:
        peak_map = date_equipment_map.get(peak_day, {})
        for etype, needed in peak_map.items():
            have = available_counts.get(etype.lower(), 0)
            if have < needed:
                shortages.append({"equipment_type": etype, "needed": needed, "available": have})

    return {
        "horizon_start": horizon_start.isoformat(),
        "horizon_end": horizon_end.isoformat(),
        "horizon_days": horizon_days,
        "date_equipment_map": date_equipment_map,
        "unit_schedule": unit_schedule,
        "aggregate_counts": aggregate_counts,
        "most_needed_types": most_needed,
        "peak_day": peak_day,
        "peak_total_demand": peak_total,
        "available_equipment_counts": available_counts,
        "shortages_at_peak": shortages,
        "generated_at": datetime.utcnow().isoformat(),
    }

def aggregate_weekly_equipment_demand(demand_map: Dict[str, Dict[str, int]]) -> Dict[str, Any]:
    """
    Converts date_equipment_map (daily) into weekly buckets:
    {
      "week_1": {
        "start": "YYYY-MM-DD",
        "end": "YYYY-MM-DD",
        "equipment_totals": { "tractor": 5, "sprayer": 2 },
        "peak_equipment": { "tractor": 3 }
      },
      ...
    }
    """

    if not demand_map:
        return {}

    # Sort days
    sorted_dates = sorted(demand_map.keys())

    def week_of(date_obj):
        return date_obj.isocalendar()[1]  # ISO week number

    weekly = {}

    for iso_day in sorted_dates:
        day_obj = datetime.fromisoformat(iso_day).date()
        wk = week_of(day_obj)

        week_key = f"week_{wk}"

        if week_key not in weekly:
            weekly[week_key] = {
                "start": iso_day,
                "end": iso_day,
                "equipment_totals": {},
                "days": []
            }

        # Update week start/end
        if iso_day < weekly[week_key]["start"]:
            weekly[week_key]["start"] = iso_day
        if iso_day > weekly[week_key]["end"]:
            weekly[week_key]["end"] = iso_day

        # Add daily mapping
        weekly[week_key]["days"].append({iso_day: demand_map[iso_day]})

        # Accumulate equipment totals
        for eq_type, count in demand_map[iso_day].items():
            weekly[week_key]["equipment_totals"][eq_type] = \
                weekly[week_key]["equipment_totals"].get(eq_type, 0) + count

    # Add peak equipment type for each week
    for wk, info in weekly.items():
        totals = info["equipment_totals"]
        if totals:
            peak_type = max(totals.items(), key=lambda x: x[1])
            info["peak_equipment"] = {peak_type[0]: peak_type[1]}
        else:
            info["peak_equipment"] = {}

        # Remove raw days list if frontend doesn’t need full detail
        # (optional but kept for now)
    
    return weekly

def benchmark_equipment_performance(equipment_id: str) -> Optional[Dict[str, Any]]:
    """
    Computes a performance benchmark score based on:
    - fuel efficiency
    - health score
    - maintenance frequency
    - breakdown probability
    - ROI
    - idle status

    Score: 0–100
    Categories:
        excellent / good / average / poor / critical
    """

    with _store_lock:
        eq = _equipment_store.get(equipment_id)
        if not eq:
            return None

    # ======= HEALTH SCORE =======
    health = compute_equipment_health(equipment_id)
    health_score = health.get("health_score", 70)

    # ======= FUEL EFFICIENCY =======
    fuel = compute_fuel_efficiency(equipment_id)
    if fuel and "fuel_efficiency" in fuel:
        fph = fuel["fuel_efficiency"].get("liters_per_hour") or None
    else:
        fph = None
    
    # Score fuel efficiency (lower is better)
    fuel_score = 50  # baseline
    if fph:
        if fph <= 3:
            fuel_score = 90
        elif fph <= 4:
            fuel_score = 75
        elif fph <= 6:
            fuel_score = 60
        else:
            fuel_score = 40

    # ======= BREAKDOWN PROBABILITY =======
    breakdown = compute_breakdown_probability(equipment_id)
    breakdown_prob = breakdown.get("breakdown_probability", 20)
    breakdown_score = max(0, 100 - breakdown_prob)

    # ======= IDLE & UTILIZATION =======
    util = compute_equipment_utilization(equipment_id)
    avg_usage = util.get("avg_daily_usage", 1)
    idle = compute_idle_status(equipment_id)
    idle_days = idle.get("idle_days", 0)

    # Idle penalty
    if idle_days >= 30:
        util_score = 40
    elif idle_days >= 14:
        util_score = 60
    else:
        util_score = 80

    # ======= ROI PERFORMANCE =======
    roi = compute_equipment_roi(equipment_id, analysis_period_years=1)
    roi_percent = roi.get("roi_percent")
    roi_score = 70
    if roi_percent is not None:
        if roi_percent >= 50:
            roi_score = 95
        elif roi_percent >= 30:
            roi_score = 85
        elif roi_percent >= 10:
            roi_score = 70
        elif roi_percent >= 0:
            roi_score = 50
        else:
            roi_score = 30

    # ======= FINAL WEIGHTED SCORE =======
    final_score = int(
        health_score * 0.25 +
        fuel_score * 0.15 +
        breakdown_score * 0.20 +
        util_score * 0.20 +
        roi_score * 0.20
    )

    # category
    if final_score >= 85:
        category = "excellent"
    elif final_score >= 70:
        category = "good"
    elif final_score >= 55:
        category = "average"
    elif final_score >= 40:
        category = "poor"
    else:
        category = "critical"

    # ======= RECOMMENDATIONS =======

    recommendations = []

    if fph and fph > 6:
        recommendations.append("Fuel consumption is high — check engine tuning & filters.")

    if idle_days >= 14:
        recommendations.append("Equipment has been idle too long — consider rotation or reassigning tasks.")

    if breakdown_prob >= 60:
        recommendations.append("High breakdown risk — schedule preventive maintenance immediately.")

    if roi_percent is not None and roi_percent < 0:
        recommendations.append("Negative ROI — reduce operating cost or evaluate replacement.")

    if health_score < 60:
        recommendations.append("Overall health is low — address issues before peak season.")

    return {
        "equipment_id": equipment_id,
        "performance_score": final_score,
        "category": category,
        "health_score": health_score,
        "fuel_efficiency_lph": fph,
        "breakdown_probability": breakdown_prob,
        "avg_daily_usage": avg_usage,
        "idle_days": idle_days,
        "roi_percent": roi_percent,
        "recommendations": recommendations,
        "calculated_at": datetime.utcnow().isoformat()
    }


def fleet_performance_benchmark():
    """
    Returns sorted performance benchmarks for all equipment.
    """
    results = []
    with _store_lock:
        eq_ids = list(_equipment_store.keys())

    for eid in eq_ids:
        perf = benchmark_equipment_performance(eid)
        if perf:
            results.append(perf)

    # sort best → worst
    results.sort(key=lambda x: x["performance_score"], reverse=True)

    return {
        "count": len(results),
        "fleet_benchmark": results,
        "timestamp": datetime.utcnow().isoformat()
    }

def recommend_equipment_replacement(equipment_id: str) -> Optional[Dict[str, Any]]:
    """
    Heuristic replacement recommendation engine.

    Factors considered:
      - age (years) and major-service cycle
      - health_score (lower → more likely to replace)
      - breakdown_probability (higher → replace)
      - cost_per_hour vs productivity (from compute_equipment_operating_cost)
      - maintenance cost trend (sum of maintenance_history.estimated_cost if present)
      - ROI (negative/low → replace)
      - spare parts scarcity (high → replace sooner)

    Returns:
      {
        equipment_id,
        recommendation: "replace"/"service"/"monitor",
        urgency: "immediate"/"high"/"medium"/"low",
        months_to_replace: int (estimate),
        rationale: [...],
        scores: {...},
        calculated_at: ISO
      }
    """

    with _store_lock:
        rec = _equipment_store.get(equipment_id)
        if not rec:
            return None

    now = datetime.utcnow()

    # Age
    year = rec.get("year")
    age_years = None
    if year:
        try:
            age_years = max(0, now.year - int(year))
        except:
            age_years = None

    # Health
    health = compute_equipment_health(equipment_id) or {}
    health_score = health.get("health_score", 70)

    # Breakdown probability
    breakdown = compute_breakdown_probability(equipment_id) or {}
    breakdown_prob = breakdown.get("breakdown_probability", 20)

    # Operating cost and cost_per_hour
    cost_summary = compute_equipment_operating_cost(equipment_id) or {}
    cost_per_hour = cost_summary.get("cost_per_hour")
    total_operating_cost = cost_summary.get("total_operating_cost", 0.0)

    # Maintenance cost trend (sum of estimated_cost in maintenance_history)
    maintenance_hist = rec.get("maintenance_history", [])
    maint_cost_sum = 0.0
    for m in maintenance_hist:
        try:
            maint_cost_sum += float(m.get("estimated_cost", 0.0))
        except:
            pass

    # ROI
    roi = compute_equipment_roi(equipment_id, analysis_period_years=1) or {}
    roi_percent = roi.get("roi_percent")

    # Spare parts scarcity: check assigned parts and global parts store
    try:
        from app.services.farmer.spare_parts_service import get_parts_for_equipment
        parts_info = get_parts_for_equipment(equipment_id) or {}
        low_stock_parts = 0
        missing_parts = 0
        for item in parts_info.get("items", []):
            p = item.get("part")
            if not p:
                missing_parts += 1
            else:
                if p.get("quantity", 0) <= p.get("min_stock_threshold", 1):
                    low_stock_parts += 1
    except Exception:
        low_stock_parts = 0
        missing_parts = 0

    # Heuristic scoring to decide replacement urgency
    # Start with neutral score and add penalties that push toward replacement
    score = 100  # higher = healthier / less need for replacement

    # Age penalty (older equipment is more likely to be replaced)
    if age_years is not None:
        if age_years >= 8:
            score -= 30
        elif age_years >= 5:
            score -= 15
        elif age_years >= 3:
            score -= 5

    # Health penalty
    if health_score < 40:
        score -= 30
    elif health_score < 60:
        score -= 15
    elif health_score < 75:
        score -= 5

    # Breakdown penalty
    if breakdown_prob >= 70:
        score -= 30
    elif breakdown_prob >= 50:
        score -= 15
    elif breakdown_prob >= 30:
        score -= 5

    # Maintenance costs penalty
    if maint_cost_sum > 1000:  # tune: high cumulative maintenance
        score -= 15
    elif maint_cost_sum > 500:
        score -= 8

    # Low ROI penalty
    if roi_percent is not None:
        if roi_percent < 0:
            score -= 25
        elif roi_percent < 5:
            score -= 10
        elif roi_percent < 15:
            score -= 3

    # Spare parts scarcity penalty
    score -= min(20, missing_parts * 15 + low_stock_parts * 5)

    # Cost efficiency penalty (very high cost_per_hour suggests replacement consideration)
    if cost_per_hour is not None:
        if cost_per_hour > 100:
            score -= 15
        elif cost_per_hour > 50:
            score -= 8

    # Clamp
    score = max(0, min(100, int(score)))

    # Map score to recommendation & urgency
    # Lower score → more urgent to replace
    if score <= 20:
        recommendation = "replace"
        urgency = "immediate"
        months_to_replace = 0
    elif score <= 40:
        recommendation = "replace"
        urgency = "high"
        months_to_replace = 1  # within 1 month
    elif score <= 60:
        recommendation = "service"
        urgency = "medium"
        months_to_replace = 3
    elif score <= 80:
        recommendation = "monitor"
        urgency = "low"
        months_to_replace = 6
    else:
        recommendation = "no_action"
        urgency = "low"
        months_to_replace = 12

    # Build rationale messages
    rationale = []
    if age_years is not None:
        rationale.append(f"age_years={age_years}")

    rationale.append(f"health_score={health_score}")
    rationale.append(f"breakdown_probability={breakdown_prob}")
    rationale.append(f"maintenance_costs_total={round(maint_cost_sum,2)}")
    if roi_percent is not None:
        rationale.append(f"roi_percent={roi_percent}")
    if missing_parts > 0 or low_stock_parts > 0:
        rationale.append(f"parts_low_or_missing: missing={missing_parts}, low={low_stock_parts}")
    if cost_per_hour is not None:
        rationale.append(f"cost_per_hour={cost_per_hour}")

    explanation = (
        "Recommendation derived from composite score. Lower score indicates higher replacement need. "
        "Tune thresholds in code if you want different behavior."
    )

    return {
        "equipment_id": equipment_id,
        "recommendation": recommendation,
        "urgency": urgency,
        "months_to_replace": months_to_replace,
        "replacement_score": score,
        "rationale": rationale,
        "explanation": explanation,
        "calculated_at": datetime.utcnow().isoformat()
    }


def fleet_replacement_recommendations(threshold_urgency: str = "medium") -> Dict[str, Any]:
    """
    Scan fleet and return replacement suggestions.
    threshold_urgency: 'immediate'|'high'|'medium'|'low' - filters results
    """

    urgency_rank = {"immediate": 0, "high": 1, "medium": 2, "low": 3}
    if threshold_urgency not in urgency_rank:
        threshold_urgency = "medium"

    results = []
    with _store_lock:
        eq_ids = list(_equipment_store.keys())

    for eid in eq_ids:
        rec = recommend_equipment_replacement(eid)
        if not rec:
            continue
        # Include equipment meta
        equip_meta = _equipment_store.get(eid, {})
        rec_payload = {
            "equipment_id": eid,
            "name": equip_meta.get("name"),
            "type": equip_meta.get("type"),
            "recommendation": rec["recommendation"],
            "urgency": rec["urgency"],
            "months_to_replace": rec["months_to_replace"],
            "replacement_score": rec["replacement_score"],
            "rationale": rec["rationale"]
        }
        # Filter by urgency threshold
        if urgency_rank.get(rec["urgency"], 3) <= urgency_rank[threshold_urgency]:
            results.append(rec_payload)

    # Sort by urgency (immediate first) then worst score first
    results.sort(key=lambda x: (["immediate","high","medium","low"].index(x["urgency"]), x["replacement_score"]))

    return {
        "threshold_urgency": threshold_urgency,
        "count": len(results),
        "recommendations": results,
        "generated_at": datetime.utcnow().isoformat()
    }

def mark_equipment_replaced(
    equipment_id: str,
    replaced_by_equipment_id: Optional[str] = None,
    notes: Optional[str] = None
) -> Dict[str, Any]:
    """
    Marks the equipment as replaced, archives it, and prevents it from showing in active fleet analytics.
    """

    with _store_lock:
        eq = _equipment_store.get(equipment_id)
        if not eq:
            return {"error": "equipment_not_found"}

        # Update lifecycle status
        eq["status"] = "replaced"
        eq["replaced_at"] = datetime.utcnow().isoformat()
        eq["replacement_notes"] = notes

        if replaced_by_equipment_id:
            eq["replaced_by_equipment_id"] = replaced_by_equipment_id

    return {
        "success": True,
        "message": "equipment_marked_as_replaced",
        "equipment_id": equipment_id,
        "replaced_by": replaced_by_equipment_id,
        "notes": notes
    }

def analyze_failure_root_cause(equipment_id: str) -> Optional[Dict[str, Any]]:
    """
    Performs heuristic root-cause analysis (RCA) for likely equipment failure types.
    Uses:
      - fuel efficiency
      - health score
      - breakdown probability
      - maintenance gaps
      - idle patterns
      - usage hours
      - parts scarcity or abnormal replacements

    Returns:
      {
        equipment_id,
        root_causes: [
          { cause, confidence, evidence: [...] }
        ],
        recommended_actions: [...],
        calculated_at
      }
    """

    with _store_lock:
        eq = _equipment_store.get(equipment_id)
        if not eq:
            return None

    # Gather signals
    health = compute_equipment_health(equipment_id) or {}
    health_score = health.get("health_score", 70)

    breakdown = compute_breakdown_probability(equipment_id) or {}
    breakdown_prob = breakdown.get("breakdown_probability", 20)

    fuel = compute_fuel_efficiency(equipment_id) or {}
    fph = None
    if fuel and "fuel_efficiency" in fuel:
        fph = fuel["fuel_efficiency"].get("liters_per_hour")

    idle = compute_idle_status(equipment_id) or {}
    idle_days = idle.get("idle_days", 0)

    maintenance_history = eq.get("maintenance_history", [])

    # Count time since last maintenance
    last_maint_days = None
    if maintenance_history:
        try:
            last_maint = max(maintenance_history, key=lambda x: x.get("performed_at", ""))
            if last_maint.get("performed_at"):
                d = datetime.fromisoformat(last_maint["performed_at"]).date()
                last_maint_days = (datetime.utcnow().date() - d).days
        except:
            last_maint_days = None

    # Spare parts signals
    try:
        from app.services.farmer.spare_parts_service import get_parts_for_equipment
        parts_info = get_parts_for_equipment(equipment_id)
        low_stock = []
        missing_parts = []
        for item in parts_info.get("items", []):
            p = item.get("part", {})
            if not p:
                missing_parts.append(item)
            else:
                if p.get("quantity", 0) <= p.get("min_stock_threshold", 1):
                    low_stock.append(p)
    except:
        low_stock = []
        missing_parts = []

    # =============================
    # RCA DETECTION LOGIC
    # =============================
    causes = []

    # 1. Engine inefficiency
    if fph and fph > 6:
        confidence = min(1.0, 0.4 + (fph - 6) * 0.05)
        causes.append({
            "cause": "Engine inefficiency",
            "confidence": round(confidence, 2),
            "evidence": [
                f"High fuel consumption: {fph} L/hour",
                f"Health score: {health_score}"
            ]
        })

    # 2. Poor lubrication / oil deterioration
    if last_maint_days and last_maint_days > 90:
        causes.append({
            "cause": "Lubrication system degradation (oil overdue)",
            "confidence": 0.65,
            "evidence": [
                f"Last maintenance was {last_maint_days} days ago",
                "Oil change likely overdue"
            ]
        })

    # 3. Clutch / transmission wear
    if fph and fph > 5 and breakdown_prob > 40:
        causes.append({
            "cause": "Transmission or clutch wear",
            "confidence": 0.55,
            "evidence": [
                f"High fuel usage: {fph} L/hour",
                f"Breakdown probability: {breakdown_prob}%"
            ]
        })

    # 4. Electrical failure
    if breakdown_prob > 60 and not fph:
        causes.append({
            "cause": "Electrical system instability",
            "confidence": 0.5,
            "evidence": [
                "High breakdown probability",
                "No clear mechanical indicators"
            ]
        })

    # 5. Dirt contamination / air filter clogging
    if idle_days < 3 and health_score < 55:
        causes.append({
            "cause": "Dirt contamination / filter clogging",
            "confidence": 0.45,
            "evidence": [
                f"Low health score: {health_score}",
                "Quick deterioration pattern"
            ]
        })

    # 6. Spare parts scarcity (future repairs will be delayed)
    if low_stock or missing_parts:
        confidence = 0.6 if missing_parts else 0.4
        causes.append({
            "cause": "Spare parts shortage",
            "confidence": confidence,
            "evidence": [
                f"Low stock parts: {len(low_stock)}",
                f"Missing parts: {len(missing_parts)}"
            ]
        })

    # Rank by confidence
    causes.sort(key=lambda x: x["confidence"], reverse=True)

    # =============================
    # Recommendations
    # =============================
    recommendations = []

    if fph and fph > 6:
        recommendations.append("Check engine tuning, fuel injectors, and air filters.")

    if last_maint_days and last_maint_days > 90:
        recommendations.append("Schedule lubrication/oil change immediately.")

    if breakdown_prob > 50:
        recommendations.append("Increase preventive maintenance frequency.")

    if low_stock or missing_parts:
        recommendations.append("Stock critical spare parts to avoid downtime.")

    if not recommendations:
        recommendations.append("No urgent actions detected.")

    return {
        "equipment_id": equipment_id,
        "root_causes": causes[:5],
        "recommended_actions": recommendations,
        "calculated_at": datetime.utcnow().isoformat()
    }

# Predictive maintenance scheduling store
_scheduled_maintenance_store: Dict[str, List[Dict[str, Any]]] = {}
_scheduled_maintenance_lock = Lock()


def _is_peak_day_for_equipment(equipment_type: str, date_iso: str, unit_plans: List[Dict[str, Any]] = None) -> bool:
    """
    Helper: given an equipment_type and date (ISO) tell if that date is high-demand (peak)
    based on provided unit_plans via predict_equipment_demand or None (best-effort).
    """
    try:
        # if caller provided plans, use them; otherwise run a default short horizon empty-plan check
        if unit_plans is None:
            unit_plans = []
        # call predict_equipment_demand to get date_equipment_map
        demand = predict_equipment_demand(unit_plans, horizon_days=30)
        day_map = demand.get("date_equipment_map", {}).get(date_iso, {})
        count = day_map.get(equipment_type, 0)
        # treat >0 as demand; treat >=2 as peak for our heuristic
        return count >= 2
    except Exception:
        return False


def optimize_maintenance_schedule(
    equipment_id: str,
    horizon_days: int = 60,
    avoid_peak: bool = True,
    unit_plans: List[Dict[str, Any]] = None,
    min_window_days: int = 1
) -> Optional[Dict[str, Any]]:
    """
    Suggests optimal maintenance windows for the given equipment within the next horizon_days.
    Strategy:
      - Compute next_due from generate_maintenance_schedule()
      - If next_due is overdue, recommend the nearest non-peak day within next 7 days (or today)
      - If not urgent, find the lowest-demand week/day within horizon that also respects maintenance interval
      - Returns a list of candidate windows sorted by preference

    Params:
      equipment_id, horizon_days, avoid_peak (bool), unit_plans (optional farmer plans to compute demand), min_window_days

    Returns:
      {
        equipment_id,
        next_due_date,
        candidates: [ {start_date, end_date, days_left, is_peak, reason, priority_score} , ... ],
        generated_at
      }
    """

    with _store_lock:
        rec = _equipment_store.get(equipment_id)
        if not rec:
            return None

    # Get schedule & health signals
    schedule = generate_maintenance_schedule(equipment_id)
    if not schedule:
        return None

    next_due = schedule.get("next_maintenance_date")
    if isinstance(next_due, datetime):
        next_due_date = next_due.date()
    elif isinstance(next_due, str):
        try:
            next_due_date = datetime.fromisoformat(next_due).date()
        except:
            next_due_date = datetime.utcnow().date()
    else:
        next_due_date = datetime.utcnow().date()

    today = datetime.utcnow().date()
    horizon_end = today + timedelta(days=horizon_days)

    # Build a daily score map: lower score = better day to schedule (avoid peak)
    daily_scores: Dict[str, int] = {}
    for i in range(horizon_days + 1):
        d = today + timedelta(days=i)
        iso = d.isoformat()
        # base score: distance from next_due (days_left) -> lower days_left when overdue get priority
        days_left = (d - next_due_date).days
        score = max(0, days_left)  # prefer dates at/after due (lower)
        # penalize weekend? optional (we'll slightly prefer weekdays)
        if d.weekday() in (5, 6):
            score += 2
        # avoid peak increases score heavily
        if avoid_peak and _is_peak_day_for_equipment(rec.get("type", "").lower(), iso, unit_plans):
            score += 10
        daily_scores[iso] = score

    # Build candidate windows of min_window_days length and score them by sum
    candidates = []
    for i in range(0, horizon_days - max(0, min_window_days-1) + 1):
        start = today + timedelta(days=i)
        end = start + timedelta(days=max(0, min_window_days-1))
        if end > horizon_end:
            break
        # compute aggregated score
        agg = 0
        peak_flag = False
        for dd in (start + timedelta(days=k) for k in range((end - start).days + 1)):
            s = daily_scores.get(dd.isoformat(), 0)
            agg += s
            if s >= 10:  # we used 10 as the peak-penalty earlier
                peak_flag = True
        # priority: lower agg -> higher priority. we also boost urgents (when date before next_due)
        days_until_start = (start - next_due_date).days
        priority_score = agg
        if days_until_start < 0:
            # overdue: make this window higher priority by lowering priority_score
            priority_score -= 20

        candidates.append({
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "window_days": (end - start).days + 1,
            "agg_score": priority_score,
            "is_peak_window": peak_flag,
            "days_until_window_start": (start - today).days,
            "days_until_next_due": (start - next_due_date).days
        })

    # sort by agg_score ascending (lower is better)
    candidates.sort(key=lambda x: x["agg_score"])

    # Return top N candidates (e.g., top 6)
    return {
        "equipment_id": equipment_id,
        "next_due_date": next_due_date.isoformat(),
        "candidates": candidates[:6],
        "generated_at": datetime.utcnow().isoformat()
    }


def schedule_maintenance(
    equipment_id: str,
    start_date_iso: str,
    duration_days: int = 1,
    notes: str = ""
) -> Optional[Dict[str, Any]]:
    """
    Schedules maintenance for an equipment by recording a scheduled slot.
    Returns the scheduled record.
    """

    # basic validation
    try:
        start_date = datetime.fromisoformat(start_date_iso)
    except Exception:
        return {"error": "invalid_date_format"}

    end_date = start_date + timedelta(days=max(0, duration_days - 1))

    # create schedule record
    rec = {
        "schedule_id": str(uuid.uuid4()),
        "equipment_id": equipment_id,
        "start_at": start_date.isoformat(),
        "end_at": end_date.isoformat(),
        "duration_days": duration_days,
        "notes": notes,
        "status": "scheduled",
        "created_at": datetime.utcnow().isoformat()
    }

    with _scheduled_maintenance_lock:
        if equipment_id not in _scheduled_maintenance_store:
            _scheduled_maintenance_store[equipment_id] = []
        _scheduled_maintenance_store[equipment_id].append(rec)

    return rec


def list_scheduled_maintenances(equipment_id: str = None) -> Dict[str, Any]:
    """
    Returns scheduled maintenances. If equipment_id provided, returns for that equipment only.
    """

    with _scheduled_maintenance_lock:
        if equipment_id:
            return {
                "equipment_id": equipment_id,
                "count": len(_scheduled_maintenance_store.get(equipment_id, [])),
                "schedules": _scheduled_maintenance_store.get(equipment_id, [])
            }
        # else return all
        aggregated = []
        for eid, items in _scheduled_maintenance_store.items():
            for it in items:
                aggregated.append(it)
        # sort by start_at
        aggregated.sort(key=lambda x: x.get("start_at", ""))
        return {"count": len(aggregated), "schedules": aggregated}

def equipment_workload_pressure_score(equipment_id: str) -> Optional[Dict[str, Any]]:
    """
    Computes how overloaded or underutilized an equipment is.
    Higher score = more overloaded.
    Uses:
      - avg_daily_usage
      - idle_days
      - health_score
      - breakdown_probability
      - next maintenance due proximity
    """

    with _store_lock:
        eq = _equipment_store.get(equipment_id)
        if not eq:
            return None

    util = compute_equipment_utilization(equipment_id) or {}
    avg_daily_usage = util.get("avg_daily_usage", 1)

    idle = compute_idle_status(equipment_id) or {}
    idle_days = idle.get("idle_days", 0)

    health = compute_equipment_health(equipment_id) or {}
    health_score = health.get("health_score", 70)

    breakdown = compute_breakdown_probability(equipment_id) or {}
    breakdown_prob = breakdown.get("breakdown_probability", 20)

    maint = generate_maintenance_schedule(equipment_id) or {}
    next_due_raw = maint.get("next_maintenance_date")
    try:
        next_due = datetime.fromisoformat(next_due_raw).date()
    except:
        next_due = datetime.utcnow().date()
    days_until_due = (next_due - datetime.utcnow().date()).days

    # Pressure scoring model
    score = 0

    # High avg usage increases pressure
    if avg_daily_usage >= 5:
        score += 40
    elif avg_daily_usage >= 3:
        score += 25
    else:
        score += 10

    # Lower idle days = more pressure
    if idle_days <= 2:
        score += 20
    elif idle_days <= 7:
        score += 10

    # Poor health increases pressure
    if health_score < 40:
        score += 30
    elif health_score < 60:
        score += 15

    # Breakdown probability
    if breakdown_prob >= 70:
        score += 35
    elif breakdown_prob >= 50:
        score += 20
    elif breakdown_prob >= 30:
        score += 10

    # Maintenance due soon increases pressure
    if days_until_due <= 0:
        score += 25
    elif days_until_due <= 7:
        score += 15

    # Normalize 0–100
    score = min(100, max(0, score))

    return {
        "equipment_id": equipment_id,
        "pressure_score": score,
        "avg_daily_usage": avg_daily_usage,
        "idle_days": idle_days,
        "health_score": health_score,
        "breakdown_probability": breakdown_prob,
        "days_until_maintenance_due": days_until_due,
        "computed_at": datetime.utcnow().isoformat()
    }

def recommend_workload_redistribution(
    horizon_days: int = 7,
    equipment_types: Optional[List[str]] = None
):
    """
    Recommends redistribution of workload across fleet for next horizon_days.
    Steps:
      - Compute pressure score for each equipment
      - Classify as: Overloaded, Balanced, Underutilized
      - Recommend:
          • Transfer 20–40% tasks from overloaded → underutilized
          • Rest certain equipment for 3–5 days
          • Reassign tasks where suitable equipment available
    """

    results = []
    overloaded = []
    underutilized = []
    balanced = []

    with _store_lock:
        eq_ids = list(_equipment_store.keys())

    # Filter by equipment type if provided
    if equipment_types:
        eq_ids = [
            eid for eid in eq_ids
            if _equipment_store[eid].get("type", "").lower() in equipment_types
        ]

    # Compute pressure for each equipment
    for eid in eq_ids:
        p = equipment_workload_pressure_score(eid)
        if not p:
            continue
        ps = p["pressure_score"]

        # Categorize
        if ps >= 70:
            overloaded.append(p)
        elif ps <= 30:
            underutilized.append(p)
        else:
            balanced.append(p)

        results.append(p)

    # Sort groups
    overloaded.sort(key=lambda x: x["pressure_score"], reverse=True)
    underutilized.sort(key=lambda x: x["pressure_score"])
    balanced.sort(key=lambda x: x["pressure_score"])

    recommendations = []

    # 1. Transfer work from overloaded to underutilized
    for high, low in zip(overloaded, underutilized):
        recommendations.append({
            "action": "redistribute_work",
            "from_equipment": high["equipment_id"],
            "to_equipment": low["equipment_id"],
            "suggested_transfer_percent": 30,
            "reason": f"{high['equipment_id']} is overloaded (score={high['pressure_score']}), "
                      f"{low['equipment_id']} is underutilized (score={low['pressure_score']})"
        })

    # 2. Rest overloaded equipment for a few days
    for item in overloaded:
        recommendations.append({
            "action": "rest_equipment",
            "equipment_id": item["equipment_id"],
            "rest_days": 3,
            "reason": f"High pressure score {item['pressure_score']}. Rest recommended for reliability."
        })

    # 3. Assign upcoming work to underutilized equipment
    for item in underutilized:
        recommendations.append({
            "action": "assign_more_work",
            "equipment_id": item["equipment_id"],
            "reason": f"Low pressure score {item['pressure_score']}. Safe to increase load."
        })

    return {
        "horizon_days": horizon_days,
        "fleet_count": len(eq_ids),
        "overloaded": overloaded,
        "balanced": balanced,
        "underutilized": underutilized,
        "recommendations": recommendations,
        "generated_at": datetime.utcnow().isoformat()
    }

def detect_fuel_anomalies(
    equipment_id: str,
    lookback_days: int = 30,
    spike_threshold_pct: float = 0.5,
    unexplained_loss_threshold_pct: float = 0.25
) -> Optional[Dict[str, Any]]:
    """
    Detect fuel anomalies for a single equipment.

    Heuristics used:
    - Refill without usage: a fuel_history entry with liters>0 but usage_hours==0 (possible refill while idle)
    - Sudden spike: single entry liters much larger than historical average (spike_threshold_pct)
    - Unexplained loss: total liters logged vs expected liters (from historic liters_per_hour * usage_hours)
      if actual > expected * (1 + unexplained_loss_threshold_pct) -> anomaly
    - Drops / negative behavior: unexpected (flagged)

    Returns:
      {
        equipment_id,
        anomalies: [ { type, confidence, message, evidence } ],
        summary: { total_liters, expected_liters, avg_lph, lookback_days },
        checked_at
      }
    """

    with _store_lock:
        rec = _equipment_store.get(equipment_id)
        if not rec:
            return None

        fuel_history = list(rec.get("fuel_history", []))  # list of dicts

    # filter lookback by date
    cutoff = datetime.utcnow() - timedelta(days=lookback_days)
    recent = []
    for entry in fuel_history:
        try:
            t = datetime.fromisoformat(entry.get("filled_at"))
        except:
            # if malformed, include conservatively
            t = None
        if t is None or t >= cutoff:
            recent.append(entry)

    anomalies = []

    # if not enough data, return conservative message
    if not recent:
        return {
            "equipment_id": equipment_id,
            "anomalies": [],
            "summary": {"message": "no_recent_fuel_logs", "count": 0},
            "checked_at": datetime.utcnow().isoformat()
        }

    # compute historical liters/hour (from compute_fuel_efficiency if available)
    fuel_eff_obj = compute_fuel_efficiency(equipment_id) or {}
    avg_lph = None
    if "fuel_efficiency" in fuel_eff_obj:
        avg_lph = fuel_eff_obj["fuel_efficiency"].get("liters_per_hour")

    # fallback: compute average liters per entry
    liters_list = [float(e.get("liters", 0)) for e in recent if e.get("liters") is not None]
    total_liters = sum(liters_list)
    avg_liters_per_entry = (sum(liters_list) / len(liters_list)) if liters_list else 0.0

    # compute expected liters from usage_hours recorded in these entries
    total_usage_hours = sum(float(e.get("usage_hours", 0)) for e in recent)
    expected_liters_by_avg = None
    if avg_lph:
        expected_liters_by_avg = avg_lph * total_usage_hours
    elif total_usage_hours > 0 and total_liters > 0:
        # derive implied lph and use it as expected baseline
        implied_lph = total_liters / total_usage_hours if total_usage_hours > 0 else None
        expected_liters_by_avg = implied_lph * total_usage_hours if implied_lph else None

    # 1) detect refill-without-usage
    for e in recent:
        liters = float(e.get("liters", 0) or 0)
        usage_h = float(e.get("usage_hours", 0) or 0)
        if liters > 0 and usage_h == 0:
            # refill recorded but no usage hours — could be legitimate (refuel before work) OR suspicious
            confidence = 0.5
            # increase confidence if previous/next entry shows no operations
            anomalies.append({
                "type": "refill_without_usage",
                "confidence": round(confidence, 2),
                "message": "Fuel refill logged without recorded usage hours in same entry.",
                "evidence": {"entry": e}
            })

    # 2) detect sudden spikes (single entry much larger than historical average)
    if avg_liters_per_entry is not None and avg_liters_per_entry > 0:
        for e in recent:
            liters = float(e.get("liters", 0) or 0)
            if liters > avg_liters_per_entry * (1 + spike_threshold_pct):
                # large spike
                # confidence scales with ratio
                ratio = liters / (avg_liters_per_entry + 1e-9)
                confidence = min(0.95, 0.4 + (ratio - 1) * 0.2)
                anomalies.append({
                    "type": "sudden_spike",
                    "confidence": round(confidence, 2),
                    "message": f"Single fuel entry ({liters} L) is {round((ratio-1)*100,1)}% larger than avg ({round(avg_liters_per_entry,2)} L).",
                    "evidence": {"entry": e, "avg_liters_per_entry": avg_liters_per_entry}
                })

    # 3) total unexplained loss vs expected
    if expected_liters_by_avg is not None and expected_liters_by_avg > 0:
        if total_liters > expected_liters_by_avg * (1 + unexplained_loss_threshold_pct):
            # more liters logged (consumed/refilled) than expected usage -> suspicious / leakage / theft possibility
            diff = total_liters - expected_liters_by_avg
            pct = diff / expected_liters_by_avg
            confidence = min(0.95, 0.4 + pct * 0.6)
            anomalies.append({
                "type": "unexplained_fuel_loss",
                "confidence": round(confidence, 2),
                "message": f"Total liters ({round(total_liters,2)} L) exceed expected ({round(expected_liters_by_avg,2)} L) by {round(pct*100,1)}%.",
                "evidence": {
                    "total_liters": total_liters,
                    "expected_liters": expected_liters_by_avg,
                    "total_usage_hours": total_usage_hours,
                    "avg_lph_used": avg_lph
                }
            })

    # 4) detect negative or inconsistent logs (malformed)
    for e in recent:
        liters = e.get("liters")
        if liters is None:
            continue
        try:
            if float(liters) < 0:
                anomalies.append({
                    "type": "negative_liters_recorded",
                    "confidence": 0.7,
                    "message": "Negative liters recorded in fuel history (data issue).",
                    "evidence": {"entry": e}
                })
        except:
            anomalies.append({
                "type": "malformed_entry",
                "confidence": 0.4,
                "message": "Malformed fuel history entry (non-numeric liters).",
                "evidence": {"entry": e}
            })

    # build summary
    summary = {
        "count_entries": len(recent),
        "total_liters": round(total_liters, 2),
        "total_usage_hours": round(total_usage_hours, 2),
        "avg_liters_per_entry": round(avg_liters_per_entry, 2),
        "avg_lph_reported": round(avg_lph, 2) if avg_lph else None,
        "lookback_days": lookback_days
    }

    return {
        "equipment_id": equipment_id,
        "anomalies": anomalies,
        "summary": summary,
        "checked_at": datetime.utcnow().isoformat()
    }


def scan_fleet_fuel_anomalies(
    lookback_days: int = 30,
    spike_threshold_pct: float = 0.5,
    unexplained_loss_threshold_pct: float = 0.25
) -> Dict[str, Any]:
    """
    Runs detect_fuel_anomalies across all equipment and returns aggregated anomalies.
    """

    results = []
    with _store_lock:
        equipment_ids = list(_equipment_store.keys())

    for eid in equipment_ids:
        res = detect_fuel_anomalies(eid, lookback_days=lookback_days,
                                    spike_threshold_pct=spike_threshold_pct,
                                    unexplained_loss_threshold_pct=unexplained_loss_threshold_pct)
        if res and res.get("anomalies"):
            results.append(res)

    return {
        "count": len(results),
        "anomalous_equipments": results,
        "scanned_at": datetime.utcnow().isoformat()
    }

def analyze_equipment_cost_optimization(equipment_id: str) -> Optional[Dict[str, Any]]:
    """
    Provides personalized cost-saving recommendations for a single equipment.

    Signals used:
      - fuel inefficiency
      - maintenance history & overdue gaps
      - spare parts shortages
      - breakdown probability
      - ROI
      - idle patterns
      - replacement urgency

    Returns:
      {
        equipment_id,
        cost_drivers: [ {driver, impact_level, evidence} ],
        recommendations: [ {action, estimated_savings, reason} ],
        estimated_total_savings,
        computed_at
      }
    """

    with _store_lock:
        rec = _equipment_store.get(equipment_id)
        if not rec:
            return None

    cost_summary = compute_equipment_operating_cost(equipment_id) or {}
    fuel_eff = compute_fuel_efficiency(equipment_id) or {}
    health = compute_equipment_health(equipment_id) or {}
    breakdown = compute_breakdown_probability(equipment_id) or {}
    rca = analyze_failure_root_cause(equipment_id) or {}
    perf = benchmark_equipment_performance(equipment_id) or {}
    replacement = recommend_equipment_replacement(equipment_id) or {}
    pressure = equipment_workload_pressure_score(equipment_id) or {}

    # Extract key signals
    cost_per_hour = cost_summary.get("cost_per_hour", None)
    total_operating_cost = cost_summary.get("total_operating_cost", 0.0)

    fph = None
    if "fuel_efficiency" in fuel_eff:
        fph = fuel_eff["fuel_efficiency"].get("liters_per_hour")

    health_score = health.get("health_score", 70)
    breakdown_prob = breakdown.get("breakdown_probability", 20)
    pressure_score = pressure.get("pressure_score", 40)

    idle_days = pressure.get("idle_days", 0)

    roi = perf.get("roi_percent", None)
    rca_causes = rca.get("root_causes", [])

    # Build cost drivers list
    cost_drivers = []

    # Driver: fuel inefficiency
    if fph and fph > 5:
        cost_drivers.append({
            "driver": "fuel_inefficiency",
            "impact_level": "high" if fph > 6 else "medium",
            "evidence": {"liters_per_hour": fph}
        })

    # Driver: overdue maintenance
    maint = generate_maintenance_schedule(equipment_id) or {}
    next_due = maint.get("next_maintenance_date")
    try:
        due_date = datetime.fromisoformat(next_due).date()
    except:
        due_date = datetime.utcnow().date()

    overdue_days = (datetime.utcnow().date() - due_date).days
    if overdue_days > 0:
        cost_drivers.append({
            "driver": "maintenance_overdue",
            "impact_level": "high" if overdue_days > 10 else "medium",
            "evidence": {"overdue_days": overdue_days}
        })

    # Driver: high breakdown probability
    if breakdown_prob >= 40:
        cost_drivers.append({
            "driver": "breakdown_risk",
            "impact_level": "high" if breakdown_prob >= 60 else "medium",
            "evidence": {"breakdown_probability": breakdown_prob}
        })

    # Driver: high operating cost per hour
    if cost_per_hour and cost_per_hour > 60:
        cost_drivers.append({
            "driver": "operating_cost_per_hour",
            "impact_level": "high" if cost_per_hour > 100 else "medium",
            "evidence": {"cost_per_hour": cost_per_hour}
        })

    # Driver: low ROI
    if roi is not None and roi < 10:
        cost_drivers.append({
            "driver": "low_roi",
            "impact_level": "high" if roi < 0 else "medium",
            "evidence": {"roi_percent": roi}
        })

    # Driver: overload pressure
    if pressure_score >= 70:
        cost_drivers.append({
            "driver": "overload_pressure",
            "impact_level": "medium",
            "evidence": {"pressure_score": pressure_score}
        })

    # Driver: idle waste
    if idle_days > 7:
        cost_drivers.append({
            "driver": "idle_cost",
            "impact_level": "low" if idle_days <= 14 else "medium",
            "evidence": {"idle_days": idle_days}
        })

    # Driver: RCA cost signals
    for cause in rca_causes:
        if cause["confidence"] > 0.5:
            cost_drivers.append({
                "driver": f"rca_risk: {cause['cause']}",
                "impact_level": "medium",
                "evidence": cause.get("evidence", [])
            })

    # Build recommendations and estimate potential savings
    recommendations = []
    savings_total = 0.0

    # 1. Fix fuel inefficiency
    if fph and fph > 6:
        est = round(0.12 * total_operating_cost, 2)
        savings_total += est
        recommendations.append({
            "action": "Tune engine & check air filters",
            "estimated_savings": est,
            "reason": "Fuel inefficiency detected"
        })

    # 2. Address overdue maintenance
    if overdue_days > 0:
        est = round(0.08 * total_operating_cost, 2)
        savings_total += est
        recommendations.append({
            "action": "Perform maintenance immediately",
            "estimated_savings": est,
            "reason": f"Maintenance overdue by {overdue_days} days"
        })

    # 3. Reduce breakdown risk
    if breakdown_prob > 40:
        est = round(0.15 * total_operating_cost, 2)
        savings_total += est
        recommendations.append({
            "action": "Increase preventive maintenance frequency",
            "estimated_savings": est,
            "reason": "High breakdown risk detected"
        })

    # 4. Reduce idle wastage
    if idle_days > 7:
        est = round(0.05 * total_operating_cost, 2)
        savings_total += est
        recommendations.append({
            "action": "Reassign this equipment to appropriate tasks",
            "estimated_savings": est,
            "reason": "Idle days high"
        })

    # 5. Suggest workload redistribution
    if pressure_score >= 70:
        est = round(0.06 * total_operating_cost, 2)
        savings_total += est
        recommendations.append({
            "action": "Redistribute workload away from this equipment",
            "estimated_savings": est,
            "reason": "Equipment overloaded"
        })

    # 6. Suggest replacement (long-term)
    if replacement.get("recommendation") == "replace":
        est = round(0.25 * total_operating_cost, 2)
        savings_total += est
        recommendations.append({
            "action": "Consider replacing this equipment",
            "estimated_savings": est,
            "reason": replacement.get("rationale", [])
        })

    return {
        "equipment_id": equipment_id,
        "cost_drivers": cost_drivers,
        "recommendations": recommendations,
        "estimated_total_savings": round(savings_total, 2),
        "computed_at": datetime.utcnow().isoformat()
    }


def fleet_cost_optimization():
    """
    Runs cost optimization across the entire fleet.
    Returns sorted list (highest savings potential first).
    """

    results = []
    with _store_lock:
        ids = list(_equipment_store.keys())

    for eid in ids:
        r = analyze_equipment_cost_optimization(eid)
        if r:
            results.append(r)

    # Sort by savings potential (descending)
    results.sort(key=lambda x: x.get("estimated_total_savings", 0), reverse=True)

    return {
        "count": len(results),
        "fleet_cost_optimization": results,
        "generated_at": datetime.utcnow().isoformat()
    }

def forecast_equipment_seasonal_workload(
    unit_plans: List[Dict[str, Any]],
    season_months: int = 6,
    include_weather: bool = True
) -> Dict[str, Any]:
    """
    Long-horizon workload forecast (season-level).
    Expands Feature 219 (daily demand) → multi-month load and pressure estimation.

    Inputs:
      - unit_plans: list of farmer cropping plans
      - season_months: forecast horizon (default 6 months)
      - include_weather: adjust workload based on expected delays/boosts

    Output:
      {
        equipment_id,
        type,
        workload_score,
        monthly_load: { '2026-02': {...}, ... },
        season_summary: {...},
        recommendations: [...]
      }
    """

    # Step 1: Extend daily demand forecast over entire season
    horizon_days = season_months * 30
    demand = predict_equipment_demand(unit_plans, horizon_days=horizon_days)
    date_map = demand.get("date_equipment_map", {})

    # Step 2: Aggregate monthly workload per equipment type
    monthly_load: Dict[str, Dict[str, int]] = {}  # { '2026-02': { 'tractor': 3, 'sprayer': 1 } }

    for date_str, eq_map in date_map.items():
        try:
            dt = datetime.fromisoformat(date_str)
        except:
            continue
        key = f"{dt.year}-{dt.month:02d}"

        if key not in monthly_load:
            monthly_load[key] = {}

        for eq_type, count in eq_map.items():
            monthly_load[key][eq_type] = monthly_load[key].get(eq_type, 0) + count

    # Step 3: Convert to workload per actual equipment_id
    with _store_lock:
        eq_ids = list(_equipment_store.keys())
        snapshot = _equipment_store.copy()

    equipment_result = []

    for eid in eq_ids:
        rec = snapshot[eid]

        if rec.get("status") == "replaced":
            continue  # skip archived/replaced equipment

        eq_type = rec.get("type", "").lower()

        # Build monthly load for this equipment
        eq_monthly = {}
        for month, type_map in monthly_load.items():
            eq_monthly[month] = type_map.get(eq_type, 0)

        # Step 4: Compute workload pressure score per month
        # Normalize monthly counts → workload_score (0–100)
        max_load = max(eq_monthly.values()) if eq_monthly else 0
        workload_score = 0
        if max_load > 0:
            workload_score = min(100, max_load * 10)

        # Step 5: Weather adjustment
        if include_weather:
            # crude: increase workload if rain expected (delays compress operations)
            # Future: integrate weather service properly
            for month, load in eq_monthly.items():
                # If heavy rain (assume rainy season June–Aug), increase load +20%
                m = int(month.split("-")[1])
                if m in (6, 7, 8):
                    eq_monthly[month] = int(load * 1.2)

        # Step 6: Recommendations
        recs = []

        # If workload exceeds 70 → Overload alert
        if workload_score >= 70:
            recs.append("High workload expected – prepare preventive maintenance early.")
            recs.append("Consider distributing work to underutilized equipment.")
            recs.append("Check spare parts inventory for replacement cycles.")

        # If workload very low → Underutilized
        if workload_score <= 20:
            recs.append("Low workload expected – use equipment on secondary units or rental opportunities.")

        # If mid-range → Balanced
        if 20 < workload_score < 70:
            recs.append("Workload moderate – standard maintenance cycle sufficient.")

        equipment_result.append({
            "equipment_id": eid,
            "type": eq_type,
            "monthly_load": eq_monthly,
            "season_workload_score": workload_score,
            "recommendations": recs,
        })

    # Step 7: Sort highest workload → lowest
    equipment_result.sort(key=lambda x: x["season_workload_score"], reverse=True)

    return {
        "season_months": season_months,
        "equipment_workload_forecast": equipment_result,
        "monthly_load_summary": monthly_load,
        "generated_at": datetime.utcnow().isoformat()
    }

def compute_equipment_profitability(
    equipment_id: str,
    unit_plans: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """
    Computes crop-wise and unit-wise profitability for a single equipment.
    Uses:
      - equipment usage history
      - cost per hour (fuel + maintenance + depreciation proxy)
      - crop calendar & unit plans
      - involvement weight of equipment type in different crop stages
      - ROI
      - seasonal workload

    Returns:
      {
         equipment_id,
         crop_profitability: { crop_name: score },
         unit_profitability: { unit_id: score },
         profitability_score (0-100),
         category: high/medium/low,
         recommendations: [...],
         computed_at
      }
    """

    with _store_lock:
        eq = _equipment_store.get(equipment_id)
        if not eq:
            return None

    eq_type = eq.get("type", "").lower()

    # Cost signals
    cost_summary = compute_equipment_operating_cost(equipment_id) or {}
    cost_per_hour = cost_summary.get("cost_per_hour", 0)
    total_cost = cost_summary.get("total_operating_cost", 0)

    # ROI signal
    perf = benchmark_equipment_performance(equipment_id) or {}
    roi = perf.get("roi_percent", 0)

    # Seasonal workload
    seasonal = forecast_equipment_seasonal_workload(unit_plans, season_months=4)
    monthly_load_map = seasonal.get("monthly_load_summary", {})

    # Crop and unit profitability maps
    crop_profit = {}
    unit_profit = {}

    # Approx crop yield contribution constants (simplified)
    stage_weight = {
        "land_preparation": 0.30,
        "sowing": 0.25,
        "spraying": 0.20,
        "harvesting": 0.70
    }

    # Equipment role mapping
    equipment_role_map = {
        "tractor": ["land_preparation", "sowing"],
        "power_tiller": ["land_preparation"],
        "sprayer": ["spraying"],
        "harvester": ["harvesting"],
        "rotavator": ["land_preparation"],
        "seed_drill": ["sowing"]
    }

    roles = equipment_role_map.get(eq_type, [])

    # Aggregate crop & unit level scores
    for plan in unit_plans:
        crop = plan.get("crop")
        unit = plan.get("unit_id")
        area = plan.get("area", 1)

        # Crop calendar estimate
        operations = plan.get("operations", [])

        # Score how important this equipment is to this crop
        contribution = 0
        for op in operations:
            stage = op.get("stage", "").lower()
            if stage in roles:
                contribution += stage_weight.get(stage, 0.1)

        # Adjust with area (larger crops → more revenue potential)
        contribution *= max(1, area / 2)

        # Save crop-level score
        crop_profit[crop] = crop_profit.get(crop, 0) + contribution

        # Save unit-level score
        unit_profit[unit] = unit_profit.get(unit, 0) + contribution

    # Normalize scores
    if crop_profit:
        max_crop = max(crop_profit.values())
        for c in crop_profit:
            crop_profit[c] = round((crop_profit[c] / max_crop) * 100, 2)

    if unit_profit:
        max_unit = max(unit_profit.values())
        for u in unit_profit:
            unit_profit[u] = round((unit_profit[u] / max_unit) * 100, 2)

    # Efficiency score from cost signals
    if cost_per_hour <= 40:
        efficiency = 90
    elif cost_per_hour <= 60:
        efficiency = 70
    elif cost_per_hour <= 80:
        efficiency = 50
    else:
        efficiency = 30

    # ROI normalization
    roi_score = 50
    if roi is not None:
        if roi >= 40:
            roi_score = 95
        elif roi >= 20:
            roi_score = 80
        elif roi >= 10:
            roi_score = 60
        elif roi >= 0:
            roi_score = 40
        else:
            roi_score = 20

    # Final profitability score
    crop_score = max(crop_profit.values()) if crop_profit else 0
    profitability_score = int(
        crop_score * 0.6 +
        efficiency * 0.2 +
        roi_score * 0.2
    )

    # Category
    if profitability_score >= 80:
        category = "high"
    elif profitability_score >= 55:
        category = "medium"
    else:
        category = "low"

    # Recommendations
    recs = []

    if profitability_score < 50:
        recs.append("Low profitability – reduce operating cost or reassign to more profitable crops/units.")
    if cost_per_hour > 60:
        recs.append("High operating cost – check fuel efficiency and maintenance load.")
    if roi is not None and roi < 10:
        recs.append("ROI low – evaluate replacement or reduce workload on low-value operations.")

    return {
        "equipment_id": equipment_id,
        "crop_profitability": crop_profit,
        "unit_profitability": unit_profit,
        "profitability_score": profitability_score,
        "category": category,
        "recommendations": recs,
        "computed_at": datetime.utcnow().isoformat()
    }


def fleet_profitability_ranking(unit_plans: List[dict]):
    """
    Generates profitability ranking for entire equipment fleet.
    """

    results = []
    with _store_lock:
        ids = list(_equipment_store.keys())

    for eid in ids:
        r = compute_equipment_profitability(eid, unit_plans)
        if r:
            results.append(r)

    # Sort highest profitability → lowest
    results.sort(key=lambda x: x["profitability_score"], reverse=True)

    return {
        "count": len(results),
        "ranking": results,
        "generated_at": datetime.utcnow().isoformat()
    }

# Smart Equipment Assignment store
_task_assignments: Dict[str, Dict[str, Any]] = {}  # task_id -> assignment record
_task_assignments_lock = Lock()


def _score_equipment_for_task(equipment_id: str, task: Dict[str, Any]) -> Dict[str, Any]:
    """
    Return a score object for equipment suitability for a given task.
    Factors:
      - type match (required_equipment_type vs eq.type)
      - suitability score (crop & stage) if provided
      - workload pressure (lower pressure preferred)
      - maintenance proximity (avoid if maintenance due soon)
      - availability (status != replaced)
      - cost (cost_per_hour lower preferred)
      - explicit preference boost
    Returns:
      {
        equipment_id,
        score (0-100),
        breakdown: {type_match, suitability, pressure_penalty, maintenance_penalty, cost_penalty, preference_bonus},
        rationale: [...]
      }
    """

    task_type = (task.get("required_equipment_type") or "").lower()
    preferred = task.get("preferred_equipment_ids", []) or []
    crop = task.get("crop", "")
    stage = task.get("stage", "")

    with _store_lock:
        rec = _equipment_store.get(equipment_id)
        if not rec:
            return {"equipment_id": equipment_id, "score": 0, "breakdown": {}, "rationale": ["equipment_not_found"]}

    # basic availability & status
    if rec.get("status") == "replaced":
        return {"equipment_id": equipment_id, "score": 0, "breakdown": {}, "rationale": ["equipment_replaced"]}

    eq_type = rec.get("type", "").lower()

    breakdown = {}
    rationale = []

    # Type match
    type_score = 50 if eq_type == task_type else (25 if task_type in eq_type or eq_type in task_type else 10)
    breakdown["type_match"] = type_score
    if eq_type == task_type:
        rationale.append("type_exact_match")

    # Suitability (if crop/stage provided)
    suitability_score = 0
    try:
        if crop and stage:
            suit = get_equipment_suitability_score(equipment_id, crop, stage) or {}
            suitability_score = suit.get("suitability_score") or 0
            breakdown["suitability"] = int((suitability_score / 100) * 30)  # scale into 0..30
            if suit.get("label"):
                rationale.append(f"suitability:{suit.get('label')}")
        else:
            breakdown["suitability"] = 10  # small neutral value
    except Exception:
        breakdown["suitability"] = 5

    # Pressure penalty
    pressure = equipment_workload_pressure_score(equipment_id) or {}
    pressure_score = pressure.get("pressure_score", 40)
    # convert pressure to penalty: higher pressure -> larger penalty
    pressure_penalty = int(min(30, (pressure_score / 100) * 30))
    breakdown["pressure_penalty"] = pressure_penalty
    if pressure_score >= 70:
        rationale.append("high_pressure")

    # Maintenance penalty
    maint = generate_maintenance_schedule(equipment_id) or {}
    days_left = None
    try:
        nd = maint.get("next_maintenance_date")
        if isinstance(nd, str):
            days_left = (datetime.fromisoformat(nd).date() - datetime.utcnow().date()).days
        elif isinstance(nd, datetime):
            days_left = (nd.date() - datetime.utcnow().date()).days
    except Exception:
        days_left = None

    maintenance_penalty = 0
    if days_left is not None:
        if days_left < 0:
            maintenance_penalty = 20
            rationale.append("maintenance_overdue")
        elif days_left <= 3:
            maintenance_penalty = 10
            rationale.append("maintenance_due_soon")
    breakdown["maintenance_penalty"] = maintenance_penalty

    # Cost penalty (higher cost -> penalty)
    cost_summary = compute_equipment_operating_cost(equipment_id) or {}
    cph = cost_summary.get("cost_per_hour")
    cost_penalty = 0
    if cph is not None:
        if cph > 100:
            cost_penalty = 15
        elif cph > 60:
            cost_penalty = 8
    breakdown["cost_penalty"] = cost_penalty

    # Preference bonus
    preference_bonus = 10 if equipment_id in preferred else 0
    if preference_bonus:
        rationale.append("preferred_by_user")
    breakdown["preference_bonus"] = preference_bonus

    # Compose final score (type + suitability + neutral baseline) - penalties + bonus
    base = type_score + breakdown.get("suitability", 0) + 10  # baseline 10
    penalties = pressure_penalty + maintenance_penalty + cost_penalty
    final = int(max(0, min(100, base - penalties + preference_bonus)))

    return {
        "equipment_id": equipment_id,
        "score": final,
        "breakdown": breakdown,
        "rationale": rationale
    }


def smart_assign_tasks(task_list: List[Dict[str, Any]], auto_confirm: bool = False) -> Dict[str, Any]:
    """
    Assigns equipment to tasks using the scoring function.
    task_list: [ { task_id, required_equipment_type, start_iso, end_iso, estimated_hours, priority (1-10), crop, stage, unit_id, preferred_equipment_ids } ]
    Returns:
      {
        count: N,
        assignments: [ { task_id, equipment_id, score, breakdown, rationale, assigned_at, status } ],
        unassigned: [ task_id ... ],
        generated_at
      }
    Behavior:
      - For each task, rank eligible equipment by score
      - Pick highest score equipment that is not already assigned to overlapping tasks
      - If auto_confirm True, mark assignment.store it; else return proposed assignments with status 'proposed'
    """

    # Build simple availability map from existing _task_assignments to prevent double booking
    # For simplicity we assume tasks overlap if their date ranges intersect (inclusive)
    def overlaps(a_start, a_end, b_start, b_end):
        return not (a_end < b_start or b_end < a_start)

    # helper to check equipment free for a task window
    def equipment_free(eid, task_start, task_end):
        with _task_assignments_lock:
            for t, rec in _task_assignments.items():
                if rec.get("equipment_id") != eid:
                    continue
                # if status is cancelled or completed skip
                if rec.get("status") in ("cancelled", "completed"):
                    continue
                a_s = datetime.fromisoformat(rec["start_iso"])
                a_e = datetime.fromisoformat(rec["end_iso"])
                if overlaps(a_s, a_e, task_start, task_end):
                    return False
        return True

    assignments = []
    unassigned = []

    # snapshot equipment ids
    with _store_lock:
        equipment_ids = [eid for eid, r in _equipment_store.items() if r.get("status") != "replaced"]

    # process higher priority tasks first
    tasks_sorted = sorted(task_list, key=lambda x: -(x.get("priority", 5)))

    for task in tasks_sorted:
        tid = task.get("task_id") or str(uuid.uuid4())
        start_iso = task.get("start_iso")
        end_iso = task.get("end_iso")
        try:
            t_start = datetime.fromisoformat(start_iso)
            t_end = datetime.fromisoformat(end_iso) if end_iso else (t_start + timedelta(hours=int(task.get("estimated_hours", 4))))
        except Exception:
            # invalid dates -> skip
            unassigned.append(tid)
            continue

        # candidate scoring
        candidates = []
        for eid in equipment_ids:
            # quick type filter: if equipment type is exact mismatch and not in preferred, deprioritize but still allowed
            s = _score_equipment_for_task(eid, task)
            if s["score"] <= 0:
                continue
            # check availability
            if not equipment_free(eid, t_start, t_end):
                continue
            candidates.append(s)

        if not candidates:
            unassigned.append(tid)
            continue

        # pick top candidate
        candidates.sort(key=lambda x: x["score"], reverse=True)
        chosen = candidates[0]

        assign_record = {
            "task_id": tid,
            "equipment_id": chosen["equipment_id"],
            "start_iso": start_iso,
            "end_iso": end_iso or t_end.isoformat(),
            "estimated_hours": task.get("estimated_hours"),
            "priority": task.get("priority", 5),
            "score": chosen["score"],
            "breakdown": chosen["breakdown"],
            "rationale": chosen["rationale"],
            "status": "confirmed" if auto_confirm else "proposed",
            "assigned_at": datetime.utcnow().isoformat(),
            "task_meta": task
        }

        # store assignment if auto_confirm True
        if auto_confirm:
            with _task_assignments_lock:
                _task_assignments[tid] = assign_record

        assignments.append(assign_record)

    return {
        "count": len(assignments),
        "assignments": assignments,
        "unassigned": unassigned,
        "generated_at": datetime.utcnow().isoformat()
    }


def list_task_assignments(task_id: str = None) -> Dict[str, Any]:
    """
    Returns assignments. If task_id provided, return single assignment.
    """
    with _task_assignments_lock:
        if task_id:
            rec = _task_assignments.get(task_id)
            if not rec:
                return {"task_id": task_id, "found": False}
            return {"task_id": task_id, "assignment": rec}
        # else return all
        items = list(_task_assignments.values())
    return {"count": len(items), "assignments": items}


def clear_task_assignment(task_id: str) -> Dict[str, Any]:
    """
    Cancel an assignment (do not delete, mark status cancelled).
    """
    with _task_assignments_lock:
        rec = _task_assignments.get(task_id)
        if not rec:
            return {"error": "assignment_not_found"}
        rec["status"] = "cancelled"
        rec["cancelled_at"] = datetime.utcnow().isoformat()
    return {"success": True, "task_id": task_id}

def forecast_equipment_downtime(
    equipment_id: str,
    horizon_days: int = 30
) -> Optional[Dict[str, Any]]:
    """
    Predict downtime days and confidence band for an equipment.
    Horizon: 7, 30, 90 days (default 30).
    Uses:
      - breakdown_probability
      - health_score
      - maintenance schedule
      - workload pressure
      - seasonal workload
      - spare parts availability
      - fuel anomalies
    """

    with _store_lock:
        eq = _equipment_store.get(equipment_id)
        if not eq:
            return None

    # Pull existing intelligence signals
    health = compute_equipment_health(equipment_id) or {}
    breakdown = compute_breakdown_probability(equipment_id) or {}
    pressure = equipment_workload_pressure_score(equipment_id) or {}
    maint = generate_maintenance_schedule(equipment_id) or {}
    cost = compute_equipment_operating_cost(equipment_id) or {}
    rca = analyze_failure_root_cause(equipment_id) or {}
    fuel_anom = detect_fuel_anomalies(equipment_id, lookback_days=30) or {}

    health_score = health.get("health_score", 70)
    breakdown_prob = breakdown.get("breakdown_probability", 20)
    pressure_score = pressure.get("pressure_score", 30)

    # Maintenance due logic
    next_due_raw = maint.get("next_maintenance_date")
    try:
        due_date = datetime.fromisoformat(next_due_raw).date()
        days_until_due = (due_date - datetime.utcnow().date()).days
    except:
        days_until_due = 10

    # Spare parts scarcity → downtime risk
    from app.services.farmer.spare_parts_service import get_parts_for_equipment
    parts_info = get_parts_for_equipment(equipment_id)
    low_stock = []
    missing_parts = []
    for item in parts_info.get("items", []):
        p = item.get("part", {})
        if not p:
            missing_parts.append(item)
        else:
            if p.get("quantity", 0) <= p.get("min_stock_threshold", 1):
                low_stock.append(p)

    # Fuel anomalies → downtime leading indicators
    anomaly_count = len(fuel_anom.get("anomalies", []))

    # ============================
    # Calculate downtime risk score
    # ============================
    downtime_score = 0

    # Breakdown probability
    downtime_score += min(40, (breakdown_prob / 100) * 40)

    # Low health
    if health_score < 40:
        downtime_score += 25
    elif health_score < 60:
        downtime_score += 10

    # Maintenance overdue or near
    if days_until_due < 0:
        downtime_score += 25
    elif days_until_due <= 3:
        downtime_score += 10

    # Workload pressure
    downtime_score += min(20, (pressure_score / 100) * 20)

    # Spare parts scarcity
    if missing_parts:
        downtime_score += 20
    elif low_stock:
        downtime_score += 10

    # Fuel anomalies
    if anomaly_count >= 3:
        downtime_score += 10
    elif anomaly_count > 0:
        downtime_score += 5

    # Normalize
    downtime_score = int(min(100, downtime_score))

    # ============================
    # Convert score → downtime days
    # ============================
    # simple interpretable model:
    expected_downtime_days = round((downtime_score / 100) * horizon_days * 0.4, 1)
    # (0.4 = max downtime fraction allowed)

    # Confidence band
    if downtime_score >= 70:
        confidence = "high"
        low = max(0, expected_downtime_days - 2)
        high = expected_downtime_days + 5
    elif downtime_score >= 40:
        confidence = "medium"
        low = max(0, expected_downtime_days - 3)
        high = expected_downtime_days + 3
    else:
        confidence = "low"
        low = max(0, expected_downtime_days - 4)
        high = expected_downtime_days + 2

    # Recommendations
    recs = []

    if days_until_due < 0:
        recs.append("Maintenance overdue — perform immediately to avoid long downtime.")

    if breakdown_prob > 50:
        recs.append("High breakdown probability — schedule preventive maintenance.")

    if pressure_score > 70:
        recs.append("Equipment overloaded — redistribute workload.")

    if low_stock or missing_parts:
        recs.append("Spare parts low — restock to avoid repair delays.")

    if anomaly_count > 0:
        recs.append("Fuel anomalies detected — investigate for possible engine/stoppage issues.")

    if not recs:
        recs.append("Downtime risk low — follow normal maintenance schedule.")

    return {
        "equipment_id": equipment_id,
        "horizon_days": horizon_days,
        "downtime_score": downtime_score,
        "expected_downtime_days": expected_downtime_days,
        "confidence_band": {
            "confidence": confidence,
            "range": {"low": low, "high": high}
        },
        "signals": {
            "health_score": health_score,
            "breakdown_probability": breakdown_prob,
            "pressure_score": pressure_score,
            "days_until_maintenance_due": days_until_due,
            "fuel_anomaly_count": anomaly_count,
            "spare_parts_low": len(low_stock),
            "spare_parts_missing": len(missing_parts),
        },
        "recommendations": recs,
        "computed_at": datetime.utcnow().isoformat()
    }

def fleet_downtime_forecast(horizon_days: int = 30) -> Dict[str, Any]:
    results = []
    with _store_lock:
        ids = list(_equipment_store.keys())

    for eid in ids:
        r = forecast_equipment_downtime(eid, horizon_days)
        if r:
            results.append(r)

    # sort by highest downtime risk
    results.sort(key=lambda x: x["downtime_score"], reverse=True)

    return {
        "count": len(results),
        "fleet_downtime_forecast": results,
        "generated_at": datetime.utcnow().isoformat()
    }

# -----------------------------------------------------
# Warranty Store: in-memory until DB layer is finalized
# -----------------------------------------------------

_equipment_warranty_store: Dict[str, Dict[str, Any]] = {}
_warranty_lock = Lock()


def add_or_update_warranty(
    equipment_id: str,
    start_date: str,
    end_date: str,
    provider: str = "Unknown",
    notes: Optional[str] = None
):
    """
    Save or update warranty info for an equipment.
    """
    record = {
        "equipment_id": equipment_id,
        "start_date": start_date,
        "end_date": end_date,
        "provider": provider,
        "notes": notes
    }
    with _warranty_lock:
        _equipment_warranty_store[equipment_id] = record
    return record


def get_warranty_status(equipment_id: str) -> Dict[str, Any]:
    """
    Returns:
      - status: active / expired / expiring_soon
      - days_to_expiry
      - risk level based on breakdown prediction
      - renewal suggestion
    """

    with _warranty_lock:
        w = _equipment_warranty_store.get(equipment_id)

    if not w:
        return {"equipment_id": equipment_id, "status": "not_available"}

    try:
        end = datetime.fromisoformat(w["end_date"]).date()
        start = datetime.fromisoformat(w["start_date"]).date()
    except Exception:
        return {"equipment_id": equipment_id, "status": "invalid_dates", "record": w}

    today = datetime.utcnow().date()
    days_to_expiry = (end - today).days

    # Determine warranty status
    if days_to_expiry < 0:
        status = "expired"
    elif days_to_expiry <= 30:
        status = "expiring_soon"
    else:
        status = "active"

    # Integrate with breakdown prediction for renewal recommendation
    breakdown = compute_breakdown_probability(equipment_id) or {}
    breakdown_prob = breakdown.get("breakdown_probability", 0)

    # Estimate risk level
    if breakdown_prob >= 60:
        risk = "high"
    elif breakdown_prob >= 30:
        risk = "medium"
    else:
        risk = "low"

    # Renewal suggestion
    renewal_suggestion = None
    if status == "expiring_soon" or status == "expired":
        if risk == "high":
            renewal_suggestion = "Strongly recommended — breakdown risk is high and warranty expired/ending."
        elif risk == "medium":
            renewal_suggestion = "Recommended — warranty ending soon and moderate breakdown risk."
        else:
            renewal_suggestion = "Optional — warranty ending but equipment health is stable."

    # Savings estimate if renewed
    # For simplicity, assume warranty covers 70% of major repair cost
    operating_cost = compute_equipment_operating_cost(equipment_id) or {}
    total_cost = operating_cost.get("total_operating_cost", 0)
    potential_savings = round(total_cost * 0.15, 2) if renewal_suggestion else 0.0

    return {
        "equipment_id": equipment_id,
        "warranty": w,
        "status": status,
        "days_to_expiry": days_to_expiry,
        "breakdown_probability": breakdown_prob,
        "risk_level": risk,
        "renewal_suggestion": renewal_suggestion,
        "estimated_renewal_savings": potential_savings,
        "computed_at": datetime.utcnow().isoformat()
    }


def fleet_warranty_overview() -> Dict[str, Any]:
    """
    Returns warranty status for all equipment.
    Sorted by days_to_expiry ascending (soonest expiring first).
    """

    results = []
    with _store_lock:
        eq_ids = list(_equipment_store.keys())

    for eid in eq_ids:
        results.append(get_warranty_status(eid))

    # sort by nearest expiry (None statuses are last)
    results.sort(key=lambda x: x.get("days_to_expiry", 99999))

    return {
        "count": len(results),
        "overview": results,
        "generated_at": datetime.utcnow().isoformat()
    }
