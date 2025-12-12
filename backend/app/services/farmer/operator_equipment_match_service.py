# backend/app/services/farmer/operator_equipment_match_service.py

from datetime import datetime
from threading import Lock
from typing import Dict, Any, List, Optional

# Reuse existing services
from app.services.farmer.operator_behavior_service import (
    compute_operator_behavior,
    _operator_store,
    _operator_lock,
    _operator_usage_log
)
from app.services.farmer.equipment_service import (
    equipment_workload_pressure_score,
    generate_maintenance_schedule,
    compute_equipment_operating_cost,
    _equipment_store,
    _store_lock
)
# optional helper from previous modules
try:
    from app.services.farmer.equipment_service import get_equipment_suitability_score
except Exception:
    # If not present exactly under that name, define a stub that returns neutral suitability.
    def get_equipment_suitability_score(equipment_id, crop, stage):
        return {"suitability_score": 50, "label": "neutral"}

# Assignment store
_operator_equipment_assignments: Dict[str, Dict[str, Any]] = {}  # key = assignment_id
_assign_lock = Lock()


def _score_operator_for_equipment(operator_id: str, equipment_id: str, task_meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Score an operator for a specific equipment and optional task.
    Returns { operator_id, equipment_id, score, breakdown, rationale }.
    """

    task_meta = task_meta or {}
    crop = task_meta.get("crop", "")
    stage = task_meta.get("stage", "")
    priority = task_meta.get("priority", 5)
    estimated_hours = float(task_meta.get("estimated_hours", 4))

    # baseline checks
    with _operator_lock:
        op = _operator_store.get(operator_id)
    with _store_lock:
        eq = _equipment_store.get(equipment_id)

    if not op:
        return {"operator_id": operator_id, "equipment_id": equipment_id, "score": 0, "breakdown": {}, "rationale": ["operator_not_found"]}
    if not eq:
        return {"operator_id": operator_id, "equipment_id": equipment_id, "score": 0, "breakdown": {}, "rationale": ["equipment_not_found"]}

    breakdown = {}
    rationale = []

    # 1) Operator behavior signals
    op_behavior = compute_operator_behavior(operator_id)
    final_behavior_score = op_behavior.get("final_behavior_score", 50)  # 0-100
    breakdown["operator_behavior_score"] = final_behavior_score
    # better behavior yields bonus
    behavior_bonus = int((final_behavior_score - 50) * 0.3)  # scale to +-15
    if final_behavior_score >= 75:
        rationale.append("operator_highly_trusted")
    elif final_behavior_score < 40:
        rationale.append("operator_low_score")

    # 2) Suitability (equipment <-> crop/stage)
    suit = get_equipment_suitability_score(equipment_id, crop, stage) or {}
    suit_score_raw = suit.get("suitability_score", 50)
    # map to 0..30
    suit_score = int((suit_score_raw / 100) * 30)
    breakdown["suitability_score"] = suit_score
    if suit.get("label"):
        rationale.append(f"suitability:{suit.get('label')}")

    # 3) Pressure penalty (avoid assigning overloaded equipment)
    pressure = equipment_workload_pressure_score(equipment_id) or {}
    pressure_score = pressure.get("pressure_score", 40)
    pressure_penalty = int((pressure_score / 100) * 25)  # up to 25 penalty
    breakdown["pressure_penalty"] = pressure_penalty
    if pressure_score >= 70:
        rationale.append("equipment_high_pressure")

    # 4) Maintenance proximity penalty
    maint = generate_maintenance_schedule(equipment_id) or {}
    days_left = None
    try:
        nd = maint.get("next_maintenance_date")
        if isinstance(nd, str):
            days_left = (datetime.fromisoformat(nd).date() - datetime.utcnow().date()).days
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

    # 5) Operator experience with this equipment (usage logs)
    # compute count of past usage entries for this operator+equipment
    usage_count = 0
    with _operator_lock:
        for rec in _operator_usage_log:
            if rec.get("operator_id") == operator_id and rec.get("equipment_id") == equipment_id:
                usage_count += 1
    experience_bonus = 0
    if usage_count >= 5:
        experience_bonus = 15
        rationale.append("experienced_on_equipment")
    elif usage_count >= 1:
        experience_bonus = 6
        rationale.append("some_experience")
    breakdown["experience_bonus"] = experience_bonus

    # 6) Cost awareness: prefer lower operating cost equipment for less-skilled operators
    cost = compute_equipment_operating_cost(equipment_id) or {}
    cost_per_hour = cost.get("cost_per_hour", 50)
    cost_penalty = 0
    if final_behavior_score < 50 and cost_per_hour > 80:
        cost_penalty = 10
        rationale.append("avoid_high_cost_for_low_skill")
    breakdown["cost_penalty"] = cost_penalty

    # 7) Task-specific adjustments: for high priority tasks prefer high-behavior & experienced operators
    priority_bonus = 0
    if priority >= 8:
        priority_bonus = int((final_behavior_score / 100) * 10)  # up to +10
        rationale.append("task_high_priority")

    # Compose final score: sum of components
    # baseline: suitability + operator behavior (scaled) + experience bonus - penalties + priority bonus
    # scale behavior to 0..40
    behavior_component = int((final_behavior_score / 100) * 40)
    base = suit_score + behavior_component + experience_bonus + 10  # baseline +10
    penalties = pressure_penalty + maintenance_penalty + cost_penalty
    final = max(0, min(100, base - penalties + behavior_bonus + priority_bonus))

    breakdown.update({
        "behavior_component": behavior_component,
        "base_before_penalties": base,
        "penalties_total": penalties,
        "priority_bonus": priority_bonus,
        "behavior_bonus": behavior_bonus
    })

    return {
        "operator_id": operator_id,
        "equipment_id": equipment_id,
        "score": int(final),
        "breakdown": breakdown,
        "rationale": rationale,
        "computed_at": datetime.utcnow().isoformat()
    }


def match_operators_to_equipment(
    equipment_id: str,
    candidate_operator_ids: Optional[List[str]] = None,
    task_meta: Optional[Dict[str, Any]] = None,
    top_n: int = 5
) -> Dict[str, Any]:
    """
    Return ranked operators suitable for given equipment and task.
    If candidate_operator_ids is None, all registered operators are considered.
    """

    with _operator_lock:
        all_ops = list(_operator_store.keys())

    if candidate_operator_ids:
        ops = [oid for oid in candidate_operator_ids if oid in all_ops]
    else:
        ops = all_ops

    scores = []
    for oid in ops:
        s = _score_operator_for_equipment(oid, equipment_id, task_meta)
        if s["score"] > 0:
            scores.append(s)

    scores.sort(key=lambda x: x["score"], reverse=True)

    return {
        "equipment_id": equipment_id,
        "task_meta": task_meta or {},
        "candidates": scores[:top_n],
        "generated_at": datetime.utcnow().isoformat()
    }


def match_equipment_to_operator(
    operator_id: str,
    candidate_equipment_ids: Optional[List[str]] = None,
    task_meta: Optional[Dict[str, Any]] = None,
    top_n: int = 5
) -> Dict[str, Any]:
    """
    Return ranked equipments suitable for an operator.
    """

    with _store_lock:
        all_eq = list(_equipment_store.keys())

    if candidate_equipment_ids:
        eqs = [eid for eid in candidate_equipment_ids if eid in all_eq]
    else:
        eqs = all_eq

    scores = []
    for eid in eqs:
        s = _score_operator_for_equipment(operator_id, eid, task_meta)
        if s["score"] > 0:
            scores.append(s)

    scores.sort(key=lambda x: x["score"], reverse=True)

    return {
        "operator_id": operator_id,
        "task_meta": task_meta or {},
        "candidates": scores[:top_n],
        "generated_at": datetime.utcnow().isoformat()
    }


def confirm_assignment(operator_id: str, equipment_id: str, task_meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Confirm (persist in-memory) an operator<->equipment assignment for the task.
    Returns assignment record.
    """

    assignment = {
        "assignment_id": f"{operator_id}__{equipment_id}__{int(datetime.utcnow().timestamp())}",
        "operator_id": operator_id,
        "equipment_id": equipment_id,
        "task_meta": task_meta or {},
        "confirmed_at": datetime.utcnow().isoformat(),
        "status": "active"
    }

    with _assign_lock:
        _operator_equipment_assignments[assignment["assignment_id"]] = assignment

    return assignment


def list_assignments(operator_id: Optional[str] = None, equipment_id: Optional[str] = None) -> Dict[str, Any]:
    with _assign_lock:
        items = list(_operator_equipment_assignments.values())
    if operator_id:
        items = [i for i in items if i["operator_id"] == operator_id]
    if equipment_id:
        items = [i for i in items if i["equipment_id"] == equipment_id]
    return {"count": len(items), "assignments": items}


def cancel_assignment(assignment_id: str) -> Dict[str, Any]:
    with _assign_lock:
        rec = _operator_equipment_assignments.get(assignment_id)
        if not rec:
            return {"error": "assignment_not_found"}
        rec["status"] = "cancelled"
        rec["cancelled_at"] = datetime.utcnow().isoformat()
    return {"success": True, "assignment_id": assignment_id}
