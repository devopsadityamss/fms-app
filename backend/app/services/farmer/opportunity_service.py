# backend/app/services/farmer/opportunity_service.py

"""
Farm Opportunity Engine (Feature #297 - Medium)

- Analyzes current farm state and finds positive opportunities:
  - cost_saving
  - yield_improvement
  - efficiency
  - market_stub (placeholder)
- Uses advisory_service, weather_service, finance_service, labour_service, task_service, equipment_service, farm_risk_service when available.
- Returns deduplicated suggestions with impact_score (0..100) and short actionable message.
- In-memory, deterministic, safe-to-run.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from threading import Lock

# Optional imports — if missing, we'll fallback to safe defaults
try:
    from app.services.farmer.advisory_service import fertilizer_recommendation, irrigation_suggestion, stage_practices
except Exception:
    fertilizer_recommendation = None
    irrigation_suggestion = None
    stage_practices = None

try:
    from app.services.farmer.weather_service import get_current_weather
except Exception:
    get_current_weather = None

try:
    from app.services.farmer.finance_service import top_categories, list_subsidy_rules, apply_subsidy_rule, query_ledger
except Exception:
    top_categories = None
    list_subsidy_rules = None
    apply_subsidy_rule = None
    query_ledger = None

try:
    from app.services.farmer.labour_service import list_labor_logs, labor_efficiency_score
except Exception:
    list_labor_logs = None
    labor_efficiency_score = None

try:
    from app.services.farmer.task_service import count_overdue_tasks, upcoming_tasks_for_unit
except Exception:
    count_overdue_tasks = None
    upcoming_tasks_for_unit = None

try:
    from app.services.farmer.equipment_service import equipment_idle_suggestions, equipment_utilization
except Exception:
    equipment_idle_suggestions = None
    equipment_utilization = None

try:
    from app.services.farmer.farm_risk_service import compute_risk_score
except Exception:
    compute_risk_score = None

_lock = Lock()

def _now_iso():
    return datetime.utcnow().isoformat()

# ---------- helper utilities ----------
def _score_to_impact(score: float) -> int:
    """Clamp/convert to int 0..100"""
    s = max(0.0, min(100.0, float(score)))
    return int(round(s))

def _dedupe_suggestions(suggestions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicates by (type,title) keeping the highest impact_score"""
    seen: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for s in suggestions:
        key = (s.get("type"), s.get("title"))
        existing = seen.get(key)
        if not existing or (s.get("impact_score", 0) > existing.get("impact_score", 0)):
            seen[key] = s
    return list(seen.values())

# ---------- Opportunity generators ----------
def _opportunity_from_weather(unit_id: Optional[int], overrides: Optional[Dict[str,Any]] = None) -> List[Dict[str,Any]]:
    ops = []
    w = overrides or {}
    if not w and get_current_weather and unit_id is not None:
        try:
            w = get_current_weather(unit_id) or {}
        except Exception:
            w = {}

    if not w:
        return ops

    forecast_24 = w.get("forecast_rain_24h") or w.get("forecast_rain_48h") or 0
    temp = w.get("temperature")

    # rain opportunity: postpone irrigation, save cost
    if forecast_24 and forecast_24 >= 5:
        impact = min(90, int(forecast_24 * 2))  # more rain => bigger saving
        ops.append({
            "type": "cost_saving",
            "category": "irrigation",
            "title": "Postpone irrigation — rain expected",
            "message": f"~{forecast_24}mm rain expected soon. Postpone scheduled irrigation to save water and cost.",
            "impact_score": _score_to_impact(impact),
            "generated_at": _now_iso()
        })

    # cool/calm days: ideal for pesticide application (efficiency)
    if temp is not None and temp <= 28 and forecast_24 < 5:
        ops.append({
            "type": "efficiency",
            "category": "spraying",
            "title": "Good window for spraying",
            "message": "Cool conditions with low wind forecast — ideal time for safe and effective pesticide application.",
            "impact_score": _score_to_impact(50),
            "generated_at": _now_iso()
        })
    return ops

def _opportunity_from_fertilizer(unit_id: Optional[int], crop: Optional[str], area_ha: Optional[float], expected_yield: Optional[float]) -> List[Dict[str,Any]]:
    ops = []
    # If fertilizer_recommendation available and we have crop+area+yield, compute and detect overspend opportunity
    if fertilizer_recommendation and crop and area_ha and expected_yield:
        try:
            plan = fertilizer_recommendation(crop, area_ha, expected_yield)
            # simple heuristic: if any nutrient required is small (< 5 kg) suggest micro-dose or foliar instead
            for nut, vals in plan.get("nutrient_plan", {}).items():
                req = vals.get("fertilizer_required_kg", 0)
                if req > 0 and req < 5:
                    ops.append({
                        "type": "yield_improvement",
                        "category": "fertilizer",
                        "title": f"Optimize {nut} application",
                        "message": f"Small requirement ({req} kg) for {nut} — consider foliar or blended micro-dose for efficiency.",
                        "impact_score": _score_to_impact(40),
                        "details": {"nutrient": nut, "required_kg": req},
                        "generated_at": _now_iso()
                    })
            # if total N is large, suggest split-application to reduce losses
            n_req = plan.get("split_suggestion", {}).get("N", {}).get("basal", 0) + plan.get("split_suggestion", {}).get("N", {}).get("topdress", 0)
            if n_req and n_req >= 50:
                ops.append({
                    "type": "yield_improvement",
                    "category": "fertilizer",
                    "title": "Split nitrogen application",
                    "message": f"High nitrogen requirement (~{n_req} kg). Consider split application to improve uptake and reduce losses.",
                    "impact_score": _score_to_impact(70),
                    "details": {"n_total_kg": n_req},
                    "generated_at": _now_iso()
                })
        except Exception:
            pass
    return ops

def _opportunity_from_labour(unit_id: Optional[int]) -> List[Dict[str,Any]]:
    ops = []
    # labor efficiency suggestions
    try:
        if labor_efficiency_score and unit_id is not None:
            res = labor_efficiency_score(str(unit_id))
            score = res.get("score", 50)
            # if efficiency low -> optimize training / reallocation
            if score < 60:
                ops.append({
                    "type": "efficiency",
                    "category": "labour",
                    "title": "Improve labour efficiency",
                    "message": f"Labour efficiency score is {score}. Consider reassigning tasks, upskilling or hiring short-term help for peak tasks.",
                    "impact_score": _score_to_impact(60 - score + 30),
                    "details": {"efficiency_score": score},
                    "generated_at": _now_iso()
                })
            elif score > 85:
                # possible opportunity to rent out spare labor time or accelerate tasks
                ops.append({
                    "type": "market_stub",
                    "category": "labour",
                    "title": "Monetize labour capacity",
                    "message": "Labour efficiency is high — consider offering labor for nearby farms during slack periods.",
                    "impact_score": _score_to_impact(40),
                    "generated_at": _now_iso()
                })
    except Exception:
        pass

    # detect labor log imbalance — if labor logs exist
    try:
        if list_labor_logs and unit_id is not None:
            logs = list_labor_logs(str(unit_id))
            if logs:
                # quick heuristic: if most hours spent on one non-critical task -> suggest re-balance
                task_hours: Dict[str, float] = {}
                for l in logs:
                    t = l.get("task_name","other")
                    task_hours[t] = task_hours.get(t, 0.0) + float(l.get("hours",0) or 0)
                if task_hours:
                    top_task, top_hours = max(task_hours.items(), key=lambda x: x[1])
                    total_hours = sum(task_hours.values()) or 1.0
                    if (top_hours / total_hours) > 0.6:
                        ops.append({
                            "type": "efficiency",
                            "category": "labour",
                            "title": "Rebalance labour tasks",
                            "message": f"~{int((top_hours/total_hours)*100)}% of logged hours spent on '{top_task}'. Rebalance to focus on critical stage activities.",
                            "impact_score": _score_to_impact(50),
                            "details": {"top_task": top_task, "top_hours": top_hours, "total_hours": total_hours},
                            "generated_at": _now_iso()
                        })
    except Exception:
        pass

    return ops

def _opportunity_from_equipment(unit_id: Optional[int]) -> List[Dict[str,Any]]:
    ops = []
    # equipment utilization suggestions (if service exists)
    try:
        if equipment_utilization and unit_id is not None:
            util = equipment_utilization(unit_id)
            # expecting util: {"utilization_pct": 40, "idle_hours": 10}
            pct = util.get("utilization_pct", 0)
            idle = util.get("idle_hours", 0)
            if pct < 30 and idle >= 5:
                ops.append({
                    "type": "market_stub",
                    "category": "equipment",
                    "title": "Rent out idle equipment",
                    "message": f"Equipment utilization low ({pct}%). Consider renting equipment to nearby farmers to generate income.",
                    "impact_score": _score_to_impact(40),
                    "details": {"utilization_pct": pct, "idle_hours": idle},
                    "generated_at": _now_iso()
                })
    except Exception:
        pass

    # equipment idle suggestions from another helper
    try:
        if equipment_idle_suggestions and unit_id is not None:
            lst = equipment_idle_suggestions(unit_id) or []
            for ent in lst:
                # ent expected {title,message,impact_estimate}
                ops.append({
                    "type": "market_stub",
                    "category": "equipment",
                    "title": ent.get("title","Equipment rental"),
                    "message": ent.get("message","Consider renting out unused equipment."),
                    "impact_score": _score_to_impact(ent.get("impact_estimate", 30)),
                    "generated_at": _now_iso()
                })
    except Exception:
        pass

    return ops

def _opportunity_from_finance(unit_id: Optional[int], farmer_id: Optional[str]) -> List[Dict[str,Any]]:
    ops = []
    # top expense categories -> where to save
    try:
        if top_categories and farmer_id:
            tc = top_categories(farmer_id=farmer_id, top_n=5)
            cats = tc.get("top_categories", [])
            if cats:
                # suggest reviewing the top expense category
                top = cats[0]
                if top.get("amount", 0) > 10000:  # threshold in currency units (heuristic)
                    ops.append({
                        "type": "cost_saving",
                        "category": "finance",
                        "title": f"Review spending on {top.get('category')}",
                        "message": f"High spending detected on {top.get('category')} (~{top.get('amount')}). Negotiate prices or optimize usage.",
                        "impact_score": _score_to_impact(60),
                        "details": {"category": top.get("category"), "amount": top.get("amount")},
                        "generated_at": _now_iso()
                    })
    except Exception:
        pass

    # subsidy suggestion (if rules exist)
    try:
        if list_subsidy_rules and farmer_id:
            rules = list_subsidy_rules(active_only=True)
            if rules:
                # show top rule names as opportunity to claim subsidy
                for r in rules[:2]:
                    ops.append({
                        "type": "cost_saving",
                        "category": "subsidy",
                        "title": f"Check subsidy: {r.get('name')}",
                        "message": f"Eligible subsidy '{r.get('name')}' exists — check eligibility to reduce costs.",
                        "impact_score": _score_to_impact(50),
                        "details": {"rule_id": r.get("rule_id")},
                        "generated_at": _now_iso()
                    })
    except Exception:
        pass

    return ops

def _opportunity_from_stage(unit_id: Optional[int], crop: Optional[str], stage: Optional[str]) -> List[Dict[str,Any]]:
    ops = []
    # stage_practices: missing scheduled practice => opportunity to schedule
    try:
        if stage_practices and crop and stage:
            sp = stage_practices(crop, stage) or {}
            practices = sp.get("practices", [])
            if practices:
                # suggest scheduling top practice if not already done (we don't have task list here — UI can check)
                ops.append({
                    "type": "yield_improvement",
                    "category": "stage",
                    "title": f"Follow stage best practices for {stage}",
                    "message": f"{len(practices)} recommended practices for {crop} at {stage}. Scheduling critical ones can improve yield.",
                    "impact_score": _score_to_impact(60),
                    "details": {"practices_count": len(practices)},
                    "generated_at": _now_iso()
                })
    except Exception:
        pass
    return ops

def _opportunity_from_risk(unit_id: Optional[int], farmer_id: Optional[str]) -> List[Dict[str,Any]]:
    ops = []
    # if compute_risk_score exists, low-to-moderate risk with actionable items = opportunity to improve quickly
    try:
        if compute_risk_score:
            r = compute_risk_score(unit_id=unit_id, farmer_id=farmer_id)
            score = r.get("risk_score")
            if score is not None and score < 40:
                # relatively low risk: opportunity to intensify certain operations for higher yield
                ops.append({
                    "type": "yield_improvement",
                    "category": "intensify",
                    "title": "Opportunity to intensify for yield",
                    "message": "Current risk is low — consider timely application of high-impact operations (fertilizer split, irrigation scheduling) to boost yield.",
                    "impact_score": _score_to_impact(55),
                    "details": {"risk_score": score},
                    "generated_at": _now_iso()
                })
    except Exception:
        pass
    return ops

# ---------- Main public API ----------
def compute_opportunities(
    unit_id: Optional[int] = None,
    farmer_id: Optional[str] = None,
    crop: Optional[str] = None,
    stage: Optional[str] = None,
    area_ha: Optional[float] = None,
    expected_yield_t_per_ha: Optional[float] = None,
    weather_override: Optional[Dict[str,Any]] = None,
    max_results: int = 10
) -> Dict[str,Any]:
    """
    Compute a ranked list of opportunity suggestions for the given unit/farmer.
    Returns:
      {
        "unit_id": ...,
        "timestamp": ...,
        "opportunities": [ {type, category, title, message, impact_score, details?}, ... ]
      }
    """
    suggestions: List[Dict[str,Any]] = []

    # generate from multiple sources
    try:
        suggestions += _opportunity_from_weather(unit_id, weather_override)
    except Exception:
        pass

    try:
        suggestions += _opportunity_from_fertilizer(unit_id, crop, area_ha, expected_yield_t_per_ha)
    except Exception:
        pass

    try:
        suggestions += _opportunity_from_labour(unit_id)
    except Exception:
        pass

    try:
        suggestions += _opportunity_from_equipment(unit_id)
    except Exception:
        pass

    try:
        suggestions += _opportunity_from_finance(unit_id, farmer_id)
    except Exception:
        pass

    try:
        suggestions += _opportunity_from_stage(unit_id, crop, stage)
    except Exception:
        pass

    try:
        suggestions += _opportunity_from_risk(unit_id, farmer_id)
    except Exception:
        pass

    # dedupe and sort by impact_score desc
    deduped = _dedupe_suggestions(suggestions)
    deduped_sorted = sorted(deduped, key=lambda x: x.get("impact_score",0), reverse=True)

    # limit results
    limited = deduped_sorted[:max_results]

    return {"unit_id": unit_id, "farmer_id": farmer_id, "timestamp": _now_iso(), "count": len(limited), "opportunities": limited}
