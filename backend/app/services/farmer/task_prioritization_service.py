# backend/app/services/farmer/task_prioritization_service.py

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import math

from app.services.farmer.unit_service import _unit_store
from app.services.farmer.stage_service import _stage_template_store
from app.services.farmer.risk_alerts_service import evaluate_risks_for_unit
from app.services.farmer.input_forecasting_service import forecast_inputs_for_unit


"""
SMART TASK PRIORITIZATION ENGINE v1

For each task in each stage:
  - Compute urgency score based on:
        - Due date proximity
        - Weather suitability
        - Dependency risk (fertilizer/pesticide missing)
        - Alerts (pest, disease, weather stress)
        - Stage delay penalties
  - Output: sorted prioritized list with explanation
"""


# -------------------------
# Helper scoring functions
# -------------------------
def _due_date_score(due_iso: Optional[str]) -> float:
    if not due_iso:
        return 50  # neutral
    try:
        due = datetime.fromisoformat(due_iso)
        delta = (due - datetime.utcnow()).days
        if delta <= 0:
            return 100  # overdue
        if delta <= 3:
            return 85
        if delta <= 7:
            return 70
        return 50
    except Exception:
        return 50


def _weather_suitability_score(task_type: str, weather: Optional[Dict[str, Any]]) -> float:
    if not weather:
        return 70

    tmax = float(weather.get("temp_c_max", 30) or 30)
    rain = float(weather.get("rain_mm_24h", 0) or 0)
    hum = float(weather.get("humidity_pct", 70) or 70)

    # example heuristics
    if task_type == "fertilizer":
        # avoid heavy rain
        if rain > 20:
            return 40
        return 80

    if task_type == "pesticide":
        # avoid rain & high wind/humidity
        if rain > 2:
            return 20
        if hum > 85:
            return 40
        return 85

    if task_type == "irrigation":
        if rain > 10:
            return 20
        return 80

    if task_type == "sowing":
        if rain < 5:
            return 60
        if 5 <= rain <= 20:
            return 85
        return 70

    # default
    return 70


def _alert_penalty_score(alerts: List[Dict[str, Any]]) -> float:
    """Alerts of severity high increase urgency for specific tasks."""
    if not alerts:
        return 0
    penalty = 0
    for a in alerts:
        sev = a.get("severity", "low")
        if sev == "high":
            penalty += 20
        elif sev == "medium":
            penalty += 10
    return min(40, penalty)


def _input_readiness_score(task_type: str, expected_inputs: Dict[str, Any], applied_inputs: Optional[Dict[str, Any]] = None) -> float:
    """
    If task requires certain input (seed, fertilizer, pesticide) and it's missing → reduce score
    """
    applied_inputs = applied_inputs or {}

    if task_type == "sowing":
        if applied_inputs.get("seed_kg_applied", 0) <= 0:
            return 40  
        return 80

    if task_type == "fertilizer":
        fert_exp = expected_inputs.get("fertilizer", {})
        fert_applied = applied_inputs.get("fertilizer_applied", {})
        if not fert_exp:
            return 60
        # Check if required nutrient is applied or planned
        for k, v in fert_exp.items():
            if fert_applied.get(k, 0) < v * 0.3:
                return 50
        return 80

    if task_type == "pesticide":
        # Missing pesticide is common; prioritize if risks present
        return 70

    return 70


# -------------------------
# MAIN PRIORITIZATION ENGINE
# -------------------------
def prioritize_tasks_for_unit(
    unit_id: str,
    weather_now: Optional[Dict[str, Any]] = None,
    inputs_snapshot: Optional[Dict[str, Any]] = None,
    crop_stage_name: Optional[str] = None
) -> Dict[str, Any]:

    unit = _unit_store.get(unit_id)
    if not unit:
        return {"status": "unit_not_found", "unit_id": unit_id}

    template_id = unit.get("stage_template_id")
    stages = _stage_template_store.get(template_id, {}).get("stages", [])
    expected_inputs = forecast_inputs_for_unit(unit_id).get("total_inputs", {})

    # evaluate risk alerts (but do NOT record them)
    alerts = evaluate_risks_for_unit(
        unit_id,
        weather_now=weather_now,
        inputs_snapshot=inputs_snapshot,
        crop_stage_name=crop_stage_name,
        auto_record=False
    )["alerts"]

    prioritized = []

    for stage in stages:
        for operation_id in stage.get("operations", []):
            # In your ecosystem, task templates are stored in task_service
            # So we import from there now
            from app.services.farmer.task_service import _task_templates_store
            task_def = _task_templates_store.get(operation_id, {})

            task_type = task_def.get("type", "general")
            due_date = task_def.get("due_date")  # optional
            name = task_def.get("name", f"task_{operation_id}")

            # Compute scores
            due_score = _due_date_score(due_date)
            weather_score = _weather_suitability_score(task_type, weather_now)
            input_score = _input_readiness_score(task_type, expected_inputs, inputs_snapshot)
            alert_penalty = _alert_penalty_score(alerts)

            # Final score
            urgency = due_score * 0.4 + weather_score * 0.2 + input_score * 0.2 + alert_penalty

            prioritized.append({
                "task_id": operation_id,
                "task_name": name,
                "stage_name": stage.get("name"),
                "task_type": task_type,
                "due_date": due_date,
                "urgency_score": round(urgency, 2),
                "components": {
                    "due_score": due_score,
                    "weather_score": weather_score,
                    "input_score": input_score,
                    "alert_penalty": alert_penalty
                },
                "recommended_action": (
                    "do_today" if urgency >= 80
                    else "schedule_this_week" if urgency >= 60
                    else "low_priority"
                ),
                "explainability": {
                    "weather_now": weather_now,
                    "alerts_considered": alerts,
                    "inputs_snapshot": inputs_snapshot
                }
            })

    prioritized = sorted(prioritized, key=lambda x: x["urgency_score"], reverse=True)

    return {
        "unit_id": unit_id,
        "task_count": len(prioritized),
        "tasks": prioritized,
        "generated_at": datetime.utcnow().isoformat()
    }


# -------------------------
# Fleet-level prioritization
# -------------------------
def prioritize_tasks_for_fleet(
    weather_map: Optional[Dict[str, Dict[str, Any]]] = None,
    inputs_snapshots: Optional[Dict[str, Dict[str, Any]]] = None,
    stage_map: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:

    all_results = []

    for unit_id in list(_unit_store.keys()):
        res = prioritize_tasks_for_unit(
            unit_id,
            weather_now=(weather_map or {}).get(unit_id),
            inputs_snapshot=(inputs_snapshots or {}).get(unit_id),
            crop_stage_name=(stage_map or {}).get(unit_id)
        )
        if res.get("status") != "unit_not_found":
            all_results.append(res)

    # Flatten tasks for global ranking
    global_tasks = []
    for r in all_results:
        for t in r["tasks"]:
            tt = t.copy()
            tt["unit_id"] = r["unit_id"]
            global_tasks.append(tt)

    global_tasks = sorted(global_tasks, key=lambda x: x["urgency_score"], reverse=True)

    return {
        "units_processed": len(all_results),
        "global_task_count": len(global_tasks),
        "global_prioritized_tasks": global_tasks,
        "unit_wise": all_results,
        "generated_at": datetime.utcnow().isoformat()
    }
