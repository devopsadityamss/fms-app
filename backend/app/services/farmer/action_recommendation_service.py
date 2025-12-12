# backend/app/services/farmer/action_recommendation_service.py

"""
Farm Action Recommendation Engine (Feature 298 - Medium)

Generates ranked, actionable recommendations (today / 3 days / 7 days)
by combining signals from:
 - farm_risk_service.compute_risk_score
 - early_warning_service.run_check
 - opportunity_service.compute_opportunities
 - advisory_service (stage_practices, irrigation, fertilizer, scouting)
 - task_service (overdue, upcoming)
 - labour_service, equipment_service, weather_service

Design goals:
 - deterministic, rule-based, in-memory
 - graceful degradation if dependencies missing
 - produce list of actions with: action, category, priority(0-100), reason, time_horizon, sources
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from threading import Lock

# Optional imports; fallback gracefully
try:
    from app.services.farmer.farm_risk_service import compute_risk_score
except Exception:
    compute_risk_score = None

try:
    from app.services.farmer.early_warning_service import run_check as run_early_warning, get_last_warnings
except Exception:
    run_early_warning = None
    get_last_warnings = None

try:
    from app.services.farmer.opportunity_service import compute_opportunities
except Exception:
    compute_opportunities = None

try:
    from app.services.farmer.advisory_service import (
        stage_practices,
        fertilizer_recommendation,
        irrigation_suggestion,
        scouting_checklist,
        get_general_advice,
    )
except Exception:
    stage_practices = None
    fertilizer_recommendation = None
    irrigation_suggestion = None
    scouting_checklist = None
    get_general_advice = None

try:
    from app.services.farmer.task_service import count_overdue_tasks, upcoming_tasks_for_unit, list_tasks_for_unit
except Exception:
    count_overdue_tasks = None
    upcoming_tasks_for_unit = None
    list_tasks_for_unit = None

try:
    from app.services.farmer.labour_service import detect_labor_shortage, labor_summary
except Exception:
    detect_labor_shortage = None
    labor_summary = None

try:
    from app.services.farmer.equipment_service import equipment_availability_risk, equipment_utilization
except Exception:
    equipment_availability_risk = None
    equipment_utilization = None

try:
    from app.services.farmer.weather_service import get_current_weather
except Exception:
    get_current_weather = None

_lock = Lock()

# Time horizon enums
TIME_HORIZON_TODAY = "today"
TIME_HORIZON_3_DAYS = "3_days"
TIME_HORIZON_7_DAYS = "7_days"

def _now_iso() -> str:
    return datetime.utcnow().isoformat()

def _score_clip(v: float) -> int:
    return int(max(0, min(100, round(v))))

def _merge_sources(sources: List[str]) -> List[str]:
    # dedupe maintain order
    out = []
    for s in sources:
        if s not in out:
            out.append(s)
    return out

# Basic scoring helpers (weights tuned heuristically)
_WEIGHTS = {
    "warning_high": 40,
    "warning_medium": 25,
    "opportunity_high": 30,
    "opportunity_medium": 15,
    "risk_high": 35,
    "risk_medium": 20,
    "stage_practice": 20,
    "overdue_task": 30,
    "labour_shortage": 30,
    "equipment_unavailable": 25,
    "weather_urgent": 30
}

def _make_action(title: str, category: str, base_score: float, reason: str, time_horizon: str, sources: List[str], details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "action": title,
        "category": category,
        "priority": _score_clip(base_score),
        "reason": reason,
        "time_horizon": time_horizon,
        "sources": _merge_sources(sources),
        "details": details or {},
        "generated_at": _now_iso()
    }

# ---------- action generators ----------
def _actions_from_warnings(unit_id: Optional[int]) -> List[Dict[str, Any]]:
    acts: List[Dict[str, Any]] = []
    if not run_early_warning:
        return acts
    try:
        # run an immediate check (no auto_notify)
        res = run_early_warning(str(unit_id), auto_notify=False)
        warnings = res.get("warnings", []) if isinstance(res, dict) else []
    except Exception:
        warnings = []

    for w in warnings:
        typ = w.get("type")
        subtype = w.get("subtype")
        level = w.get("level")
        score = w.get("severity_score", 50)
        message = w.get("message", "")
        # map to actions and time horizon
        if typ == "weather":
            if subtype in ("heatwave", "heavy_rain"):
                th = TIME_HORIZON_TODAY
                base = _WEIGHTS["warning_high"] if level == "high" else _WEIGHTS["warning_medium"]
                title = f"Immediate action: {subtype.replace('_',' ').title()}"
                reason = message
                acts.append(_make_action(title, "weather", base + (score * 0.2), reason, th, ["early_warning", "weather"], details=w))
            else:
                th = TIME_HORIZON_3_DAYS
                base = _WEIGHTS["warning_medium"]
                acts.append(_make_action(f"Monitor weather: {subtype}", "weather", base + (score * 0.1), message, th, ["early_warning", "weather"], details=w))

        elif typ == "operational":
            if subtype == "overdue_tasks":
                overdue = w.get("data", {}).get("overdue_count", 0)
                th = TIME_HORIZON_TODAY if overdue >= 5 else TIME_HORIZON_3_DAYS
                base = _WEIGHTS["overdue_task"]
                reason = message
                acts.append(_make_action("Resolve overdue tasks", "tasks", base + (overdue * 3), reason, th, ["early_warning", "tasks"], details=w))
            elif subtype == "labour_shortage":
                th = TIME_HORIZON_3_DAYS
                base = _WEIGHTS["labour_shortage"]
                acts.append(_make_action("Address labour shortage", "labour", base + w.get("severity_score", 20), message, th, ["early_warning", "labour"], details=w))
        elif typ == "crop_health":
            if subtype in ("rapid_decline", "pest_alert"):
                th = TIME_HORIZON_TODAY
                base = _WEIGHTS["warning_high"]
                acts.append(_make_action("Urgent scouting & treatment", "pest", base + w.get("severity_score",50), message, th, ["early_warning","crop_health"], details=w))
            else:
                th = TIME_HORIZON_3_DAYS
                base = _WEIGHTS["warning_medium"]
                acts.append(_make_action("Scouting recommended", "pest", base + w.get("severity_score",30), message, th, ["early_warning","crop_health"], details=w))
        elif typ == "trend":
            # rising risk trend -> proactive actions
            th = TIME_HORIZON_3_DAYS
            base = _WEIGHTS["risk_medium"]
            acts.append(_make_action("Proactive mitigation (trend detected)", "risk", base + w.get("severity_score",30), w.get("message","Trend-based alert"), th, ["early_warning","trend"], details=w))
        else:
            # generic
            acts.append(_make_action(f"Investigate: {typ}/{subtype}", "monitor", 30 + w.get("severity_score",0)*0.1, w.get("message",""), TIME_HORIZON_3_DAYS, ["early_warning"], details=w))

    return acts

def _actions_from_opportunities(unit_id: Optional[int], farmer_id: Optional[str], crop: Optional[str], stage: Optional[str], area_ha: Optional[float], expected_yield: Optional[float]) -> List[Dict[str, Any]]:
    acts: List[Dict[str, Any]] = []
    if not compute_opportunities:
        return acts
    try:
        opp = compute_opportunities(unit_id=unit_id, farmer_id=farmer_id, crop=crop, stage=stage, area_ha=area_ha, expected_yield_t_per_ha=expected_yield, max_results=20)
        suggestions = opp.get("opportunities", [])
    except Exception:
        suggestions = []

    for s in suggestions:
        typ = s.get("type","opportunity")
        title = s.get("title") or s.get("message","Opportunity")
        impact = s.get("impact_score",50)
        msg = s.get("message","")
        # map impact to time horizon: high -> 3 days / medium -> 7 days / very high -> today
        if impact >= 70:
            th = TIME_HORIZON_3_DAYS
            base = _WEIGHTS["opportunity_high"]
        elif impact >= 45:
            th = TIME_HORIZON_7_DAYS
            base = _WEIGHTS["opportunity_medium"]
        else:
            th = TIME_HORIZON_7_DAYS
            base = 10
        acts.append(_make_action(title, typ, base + (impact * 0.3), msg, th, ["opportunity"], details=s))
    return acts

def _actions_from_stage_and_advisory(unit_id: Optional[int], crop: Optional[str], stage: Optional[str]) -> List[Dict[str, Any]]:
    acts: List[Dict[str, Any]] = []
    # stage practices -> turn into scheduled actions (priority based on number of practices and stage criticality)
    if stage_practices and crop and stage:
        try:
            sp = stage_practices(crop, stage)
            practices = sp.get("practices",[]) if isinstance(sp, dict) else []
            # prioritize first 2 practices as actions
            for i, p in enumerate(practices[:3]):
                # earlier stage practices often have medium priority; for flowering/harvest increase
                if stage in ("flowering","grain_filling","heading","harvest"):
                    base = _WEIGHTS["stage_practice"] + 15
                    th = TIME_HORIZON_TODAY if i == 0 else TIME_HORIZON_3_DAYS
                else:
                    base = _WEIGHTS["stage_practice"]
                    th = TIME_HORIZON_3_DAYS
                title = f"Do: {p}"
                reason = f"Stage practice recommended for {crop} @ {stage}"
                acts.append(_make_action(title, "stage_practice", base + (10 / (i+1)), reason, th, ["stage_practices"], details={"practice_index": i}))
        except Exception:
            pass

    # irrigation & fertilizer quick checks (if advisory functions present)
    if irrigation_suggestion and get_current_weather:
        # We prefer SDK callers (UI) to call irrigation endpoint with soil moisture; here we offer generic check via weather
        try:
            w = get_current_weather(unit_id) if get_current_weather else {}
            forecast = w.get("forecast_rain_48h", w.get("forecast_rain_24h",0))
            if forecast and forecast >= 5:
                # postpone irrigation opportunity - but as action with lower priority (opportunity)
                acts.append(_make_action("Postpone irrigation due to rain forecast", "irrigation", _WEIGHTS["weather_urgent"], f"Forecast rain {forecast}mm", TIME_HORIZON_3_DAYS, ["advisory","weather"], details={"forecast_rain": forecast}))
        except Exception:
            pass

    # scouting checklist conversion
    if scouting_checklist and crop and stage:
        try:
            sc = scouting_checklist(crop, stage)
            msg = "Run scouting checklist for current stage."
            acts.append(_make_action("Perform scouting checklist", "scouting", 50, msg, TIME_HORIZON_3_DAYS, ["advisory","scouting"], details=sc))
        except Exception:
            pass

    return acts

def _actions_from_tasks_and_capacity(unit_id: Optional[int]) -> List[Dict[str, Any]]:
    acts: List[Dict[str, Any]] = []
    # overdue tasks
    overdue = 0
    if count_overdue_tasks:
        try:
            overdue = int(count_overdue_tasks(int(unit_id)))
        except Exception:
            try:
                overdue = int(count_overdue_tasks(unit_id))
            except Exception:
                overdue = 0
    if overdue > 0:
        th = TIME_HORIZON_TODAY if overdue >= 5 else TIME_HORIZON_3_DAYS
        acts.append(_make_action("Clear overdue tasks", "tasks", _WEIGHTS["overdue_task"] + overdue*2, f"{overdue} overdue tasks present", th, ["tasks"], details={"overdue_count": overdue}))

    # upcoming tasks prioritization (if available)
    if upcoming_tasks_for_unit:
        try:
            upcoming = upcoming_tasks_for_unit(unit_id) or []
            # find critical upcoming tasks in next 3 days and recommend scheduling priorities
            for t in upcoming[:5]:
                # assume t has {'title','due_date','priority'} or similar
                title = f"Prepare: {t.get('title','task')}"
                th = TIME_HORIZON_TODAY if t.get("priority","low") == "high" else TIME_HORIZON_3_DAYS
                score = 40 + (20 if t.get("priority","low") == "high" else 0)
                acts.append(_make_action(title, "tasks", score, f"Upcoming task due {t.get('due_date')}", th, ["tasks"], details=t))
        except Exception:
            pass

    return acts

def _actions_from_labour_equipment(unit_id: Optional[int]) -> List[Dict[str, Any]]:
    acts: List[Dict[str, Any]] = []
    # labour shortage -> recommend hiring or reassign
    if detect_labor_shortage:
        try:
            shortage = detect_labor_shortage(str(unit_id), stage="", area_acres=0.0)
            sh = float(shortage.get("shortage_hours",0) or 0)
            if sh > 0:
                th = TIME_HORIZON_3_DAYS if sh < 10 else TIME_HORIZON_TODAY
                acts.append(_make_action("Arrange additional labour", "labour", _WEIGHTS["labour_shortage"] + int(min(40, sh*2)), f"Estimated shortage {sh} hours", th, ["labour"], details=shortage))
        except Exception:
            pass

    # equipment availability suggestions
    if equipment_availability_risk:
        try:
            e_risk = equipment_availability_risk(unit_id)
            if e_risk and e_risk.get("score",0) > 50:
                acts.append(_make_action("Resolve equipment conflicts", "equipment", _WEIGHTS["equipment_unavailable"] + e_risk.get("score",0)*0.2, "Equipment availability risk detected", TIME_HORIZON_3_DAYS, ["equipment"], details=e_risk))
        except Exception:
            pass

    return acts

# ---------- consolidate, dedupe, rank ----------
def generate_actions(
    unit_id: Optional[int],
    farmer_id: Optional[str] = None,
    crop: Optional[str] = None,
    stage: Optional[str] = None,
    area_ha: Optional[float] = None,
    expected_yield_t_per_ha: Optional[float] = None,
    max_actions: int = 10,
    include_opportunities: bool = True,
    include_warnings: bool = True
) -> Dict[str, Any]:
    """
    Main entrypoint. Returns ranked action recommendations.
    """
    actions: List[Dict[str, Any]] = []

    # 1. warnings -> actions
    if include_warnings:
        try:
            actions += _actions_from_warnings(unit_id)
        except Exception:
            pass

    # 2. opportunities (positive)
    if include_opportunities:
        try:
            actions += _actions_from_opportunities(unit_id, farmer_id, crop, stage, area_ha, expected_yield_t_per_ha)
        except Exception:
            pass

    # 3. stage & advisory -> actions
    try:
        actions += _actions_from_stage_and_advisory(unit_id, crop, stage)
    except Exception:
        pass

    # 4. tasks & capacity
    try:
        actions += _actions_from_tasks_and_capacity(unit_id)
    except Exception:
        pass

    # 5. labour & equipment
    try:
        actions += _actions_from_labour_equipment(unit_id)
    except Exception:
        pass

    # 6. risk-driven prompts (if compute_risk_score available)
    if compute_risk_score:
        try:
            risk = compute_risk_score(unit_id=unit_id, farmer_id=farmer_id, crop=crop, stage=stage)
            rs = risk.get("risk_score", None)
            if rs is not None and rs >= 70:
                # top priority mitigation action
                actions.append(_make_action("High-risk mitigation plan", "risk_mitigation", 90 + (rs-70)*0.3, f"Overall farm risk score is {rs}", TIME_HORIZON_TODAY, ["risk"], details={"risk_score": rs}))
            elif rs is not None and rs >= 50:
                actions.append(_make_action("Review farm risk & implement mitigation", "risk_mitigation", 70, f"Overall risk {rs}", TIME_HORIZON_3_DAYS, ["risk"], details={"risk_score": rs}))
        except Exception:
            pass

    # deduplicate by (category + normalized action text)
    seen_keys = {}
    deduped: List[Dict[str, Any]] = []
    for a in actions:
        key = (a.get("category"), a.get("action").strip().lower()[:120])
        existing = seen_keys.get(key)
        if existing:
            # keep higher priority
            if a.get("priority",0) > existing.get("priority",0):
                # replace in deduped list
                try:
                    idx = deduped.index(existing)
                    deduped[idx] = a
                    seen_keys[key] = a
                except ValueError:
                    pass
        else:
            deduped.append(a)
            seen_keys[key] = a

    # sort by priority desc, then by time horizon urgency
    horizon_score = {TIME_HORIZON_TODAY: 3, TIME_HORIZON_3_DAYS: 2, TIME_HORIZON_7_DAYS: 1}
    deduped_sorted = sorted(deduped, key=lambda x: (x.get("priority",0), horizon_score.get(x.get("time_horizon"),0)), reverse=True)

    # limit results
    result = deduped_sorted[:max_actions]

    return {"unit_id": unit_id, "farmer_id": farmer_id, "timestamp": _now_iso(), "count": len(result), "recommended_actions": result}
