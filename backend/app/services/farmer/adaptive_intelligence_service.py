# backend/app/services/farmer/adaptive_intelligence_service.py

"""
Adaptive Intelligence Feedback Engine (Feature 301 - Medium)

- Maintains per-farmer adaptive profiles based on execution history and other signals.
- Computes completion rates, ignored-high-priority counts, average delay, preferred advisory complexity.
- Produces adaptive modifiers that can be applied to other engines (weights, capacity multipliers).
- Provides utilities to update profile, get profile, and apply modifiers (best-effort).
- In-memory only; designed to be a thin personalization layer that can be persisted later.
"""

from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, Any, List, Optional, Tuple
import statistics

# Optional dependencies (best-effort)
try:
    from app.services.farmer.execution_monitor_service import list_executions_for_unit, get_execution_summary, get_farmer_reliability
except Exception:
    list_executions_for_unit = None
    get_execution_summary = None
    get_farmer_reliability = None

try:
    from app.services.farmer.farm_risk_service import DEFAULT_WEIGHTS as RISK_DEFAULT_WEIGHTS
except Exception:
    RISK_DEFAULT_WEIGHTS = None

try:
    from app.services.farmer.schedule_service import MAX_TODAY_ACTIONS_BASE as SCHED_BASE_CAP
except Exception:
    SCHED_BASE_CAP = None

try:
    from app.services.farmer.notification_service import immediate_send
except Exception:
    immediate_send = None

_lock = Lock()

# Stored profiles: farmer_id -> profile
_PROFILES: Dict[str, Dict[str, Any]] = {}

# Adaptive global modifiers (farmer-specific live overrides)
# farmer_id -> modifiers dict
_MODIFIERS: Dict[str, Dict[str, Any]] = {}

# Defaults & bounds
DEFAULT_PROFILE = {
    "farmer_id": None,
    "created_at": None,
    "last_updated": None,
    "completion_rate_pct": 0.0,  # 0..100
    "avg_completion_delay_hours": 0.0,
    "ignored_high_priority_count": 0,
    "avg_priority_completion": 50.0,
    "reliability_score": None,  # from execution monitor if available
    "behaviour_summary": {},
    # personalization fields
    "intensity_level": "medium",  # low | medium | high
    "irrigation_sensitivity": 1.0,
    "fertilizer_sensitivity": 1.0,
    "labour_risk_tolerance": 1.0,
    "advisory_complexity": "normal",  # simple | normal | detailed
    "priority_adjustment_factor": 1.0
}

# Global tunables (you can tune these to change adaptation aggressiveness)
ADAPT_TUNING = {
    "completion_rate_threshold_high": 80.0,  # >= => increase intensity
    "completion_rate_threshold_low": 40.0,   # <= => reduce intensity
    "ignored_hp_threshold": 3,               # high priority actions ignored
    "delay_hours_threshold": 24.0,           # avg delay in hours considered significant
    "max_sensitivity_multiplier": 1.6,
    "min_sensitivity_multiplier": 0.6
}

def _now_iso() -> str:
    return datetime.utcnow().isoformat()

# ----------------------------
# Profile helpers
# ----------------------------
def _init_profile(farmer_id: str) -> Dict[str, Any]:
    with _lock:
        p = _PROFILES.get(farmer_id)
        if p:
            return p
        prof = DEFAULT_PROFILE.copy()
        prof["farmer_id"] = farmer_id
        prof["created_at"] = _now_iso()
        prof["last_updated"] = _now_iso()
        prof["completion_rate_pct"] = 0.0
        prof["avg_completion_delay_hours"] = 0.0
        prof["ignored_high_priority_count"] = 0
        prof["avg_priority_completion"] = 50.0
        prof["reliability_score"] = None
        prof["behaviour_summary"] = {}
        _PROFILES[farmer_id] = prof
        # default modifiers
        _MODIFIERS.setdefault(farmer_id, {
            "priority_adjustment_factor": 1.0,
            "irrigation_sensitivity": 1.0,
            "fertilizer_sensitivity": 1.0,
            "labour_risk_tolerance": 1.0,
            "schedule_capacity_multiplier": 1.0,
            "advisory_complexity": "normal"
        })
        return prof

def get_farmer_profile(farmer_id: str) -> Dict[str, Any]:
    """
    Return stored profile for farmer (init if missing).
    """
    prof = _init_profile(farmer_id)
    # attach live modifiers
    with _lock:
        profile_copy = dict(prof)
        profile_copy["modifiers"] = dict(_MODIFIERS.get(farmer_id, {}))
    return profile_copy

# ----------------------------
# Core update function
# ----------------------------
def update_farmer_intelligence_profile(farmer_id: str, recent_unit_ids: Optional[List[str]] = None, lookback_days: int = 30) -> Dict[str, Any]:
    """
    Recompute the farmer profile using:
      - execution history from execution_monitor_service (best-effort)
      - reliability score
      - summary stats (completion rate, delay, ignored high-priority count)
    If execution_monitor_service isn't available, function will estimate limited profile fields.
    recent_unit_ids: optional list of unit ids to consider (if omitted, we will try to pull summary across all units we can find)
    """
    prof = _init_profile(farmer_id)
    now = datetime.utcnow()
    cutoff = now - timedelta(days=lookback_days)

    # collect execution records summary
    total_actions = 0
    done_on_time = 0
    done_late = 0
    partial = 0
    skipped = 0
    failed = 0
    ignored = 0
    sum_delay_hours = []
    ignored_high_priority = 0
    priority_completion_vals = []

    # best-effort: if list_executions_for_unit not available, skip
    unit_ids = recent_unit_ids or []
    if not unit_ids and list_executions_for_unit and isinstance(list_executions_for_unit, type(lambda:0)):
        # we don't have a global index of units; caller can pass recent_unit_ids for better results
        # as fallback, try to use get_execution_summary keys (not provided) - skip if not possible
        unit_ids = []

    for uid in unit_ids:
        try:
            res = list_executions_for_unit(str(uid), limit=1000)
            items = res.get("items", []) if isinstance(res, dict) else []
        except Exception:
            items = []

        for r in items:
            # filter by created_at if present and within lookback
            try:
                created = datetime.fromisoformat(r.get("created_at"))
            except Exception:
                created = None
            if created and created < cutoff:
                continue
            total_actions += 1
            st = r.get("status", "scheduled")
            pr = int(r.get("priority", 0) or 0)
            if st == "done":
                # determine on-time vs late
                try:
                    scheduled_end = datetime.fromisoformat(r.get("scheduled_window_end"))
                    status_at = datetime.fromisoformat(r.get("status_at"))
                    if status_at <= scheduled_end:
                        done_on_time += 1
                        priority_completion_vals.append(pr)
                    else:
                        done_late += 1
                        priority_completion_vals.append(pr)
                        delay = (status_at - scheduled_end).total_seconds() / 3600.0
                        sum_delay_hours.append(delay)
                except Exception:
                    # treat as on time when timestamps are missing
                    done_on_time += 1
                    priority_completion_vals.append(pr)
            elif st == "partial":
                partial += 1
                priority_completion_vals.append(pr)
            elif st == "skipped":
                skipped += 1
            elif st == "failed":
                failed += 1
            elif st == "ignored":
                ignored += 1
                if pr >= 80:
                    ignored_high_priority += 1

    # compute derived metrics
    completion_count = done_on_time + done_late + partial
    completion_rate = (completion_count / total_actions * 100.0) if total_actions > 0 else prof.get("completion_rate_pct", 0.0)
    avg_delay = statistics.mean(sum_delay_hours) if sum_delay_hours else 0.0
    avg_priority_completion = statistics.mean(priority_completion_vals) if priority_completion_vals else prof.get("avg_priority_completion", 50.0)

    # reliability from execution monitor if available
    reliability = None
    try:
        if get_farmer_reliability:
            rr = get_farmer_reliability(farmer_id)
            reliability = rr.get("reliability_score")
    except Exception:
        reliability = prof.get("reliability_score")

    # update profile fields
    with _lock:
        prof["completion_rate_pct"] = round(float(completion_rate), 2)
        prof["avg_completion_delay_hours"] = round(float(avg_delay), 2)
        prof["ignored_high_priority_count"] = int(ignored_high_priority)
        prof["avg_priority_completion"] = round(float(avg_priority_completion), 2)
        prof["reliability_score"] = reliability
        prof["last_updated"] = _now_iso()

        # fill behaviour_summary for UI
        prof["behaviour_summary"] = {
            "total_actions_considered": total_actions,
            "done_on_time": done_on_time,
            "done_late": done_late,
            "partial": partial,
            "skipped": skipped,
            "failed": failed,
            "ignored": ignored,
            "ignored_high_priority": ignored_high_priority
        }

    # compute and apply adaptive modifiers (in-memory)
    modifiers = _compute_adaptive_modifiers_from_profile(prof)
    with _lock:
        _MODIFIERS[farmer_id] = modifiers

    # attempt to apply modifiers to other services (best-effort)
    _apply_modifiers_to_services(farmer_id, modifiers)

    return get_farmer_profile(farmer_id)

# ----------------------------
# Adaptive modifier computation
# ----------------------------
def _compute_adaptive_modifiers_from_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Given the computed profile, produce modifiers:
      - priority_adjustment_factor (multiplier for action priorities)
      - irrigation_sensitivity (multiplier)
      - fertilizer_sensitivity (multiplier)
      - labour_risk_tolerance (multiplier)
      - schedule_capacity_multiplier (how aggressively scheduler should schedule today)
      - advisory_complexity (simple/normal/detailed)
    """

    # start from defaults
    p = profile
    completion = p.get("completion_rate_pct", 0.0)
    avg_delay = p.get("avg_completion_delay_hours", 0.0)
    ignored_hp = p.get("ignored_high_priority_count", 0)
    reliability = p.get("reliability_score") or 0.0

    # base modifiers
    priority_mult = 1.0
    irrigation_sens = 1.0
    fertilizer_sens = 1.0
    labour_tol = 1.0
    schedule_capacity = 1.0
    advisory_complexity = "normal"

    # if completion high => increase intensity (more opportunities, higher priority scaling)
    if completion >= ADAPT_TUNING["completion_rate_threshold_high"]:
        priority_mult = min(ADAPT_TUNING["max_sensitivity_multiplier"], 1.0 + ((completion - ADAPT_TUNING["completion_rate_threshold_high"]) / 100.0))
        schedule_capacity = 1.2
        advisory_complexity = "detailed"
    # if completion low => reduce intensity and simplify
    elif completion <= ADAPT_TUNING["completion_rate_threshold_low"]:
        priority_mult = max(ADAPT_TUNING["min_sensitivity_multiplier"], 0.7 - ((ADAPT_TUNING["completion_rate_threshold_low"] - completion) / 200.0))
        schedule_capacity = 0.7
        advisory_complexity = "simple"

    # ignored high-priority actions -> increase irrigation/fertilizer sensitivity (these are often time-critical)
    if ignored_hp >= ADAPT_TUNING["ignored_hp_threshold"]:
        irrigation_sens = min(ADAPT_TUNING["max_sensitivity_multiplier"], irrigation_sens + 0.2)
        fertilizer_sens = min(ADAPT_TUNING["max_sensitivity_multiplier"], fertilizer_sens + 0.15)
        # also decrease schedule capacity to avoid overloading
        schedule_capacity = max(0.5, schedule_capacity - 0.15)

    # if average delay large -> push schedule capacity down
    if avg_delay >= ADAPT_TUNING["delay_hours_threshold"]:
        schedule_capacity = max(0.5, schedule_capacity - 0.15)
        priority_mult = max(0.6, priority_mult - 0.1)

    # reliability adjustments (more aggressive tuning if reliability score known)
    if reliability is not None:
        if reliability >= 85:
            schedule_capacity = min(1.4, schedule_capacity + 0.1)
            priority_mult = min(ADAPT_TUNING["max_sensitivity_multiplier"], priority_mult + 0.05)
        elif reliability < 50:
            schedule_capacity = max(0.6, schedule_capacity - 0.1)
            priority_mult = max(ADAPT_TUNING["min_sensitivity_multiplier"], priority_mult - 0.05)

    modifiers = {
        "priority_adjustment_factor": round(priority_mult, 3),
        "irrigation_sensitivity": round(irrigation_sens, 3),
        "fertilizer_sensitivity": round(fertilizer_sens, 3),
        "labour_risk_tolerance": round(labour_tol, 3),
        "schedule_capacity_multiplier": round(schedule_capacity, 3),
        "advisory_complexity": advisory_complexity,
        "last_computed": _now_iso()
    }
    return modifiers

# ----------------------------
# Best-effort application to other services
# ----------------------------
def _apply_modifiers_to_services(farmer_id: str, modifiers: Dict[str, Any]) -> None:
    """
    Best-effort: If target services export writable config objects,
    apply per-farmer modifiers (this is optional and done non-destructively).
    For example:
      - if farm_risk_service exposes DEFAULT_WEIGHTS, we can scale certain weights.
      - scheduler might have a base capacity constant.
    We avoid throwing on errors and do not persist beyond runtime.
    """
    # try to update farm_risk_service.DEFAULT_WEIGHTS proportional to irrigation/fertilizer sensitivity
    try:
        if RISK_DEFAULT_WEIGHTS is not None and isinstance(RISK_DEFAULT_WEIGHTS, dict):
            # do not overwrite globally for all farmers; instead expose a derived per-farmer local view in _MODIFIERS.
            # However, if you prefer global changes, uncomment the next lines to apply global multiplier (not recommended).
            # RISK_DEFAULT_WEIGHTS['weather'] *= modifiers.get('irrigation_sensitivity', 1.0)
            pass
    except Exception:
        pass

    # try to update scheduler base capacity if exposed
    try:
        if SCHED_BASE_CAP is not None:
            # cannot safely modify imported constant; prefer the scheduler to read modifiers via this service's get_modifiers_for_farmer()
            pass
    except Exception:
        pass

    # optionally notify farmer that profile has adapted (best-effort)
    try:
        if immediate_send:
            # single notify for significant changes like capacity reduction or ignored HP events
            if modifiers.get("schedule_capacity_multiplier", 1.0) < 0.8 or modifiers.get("priority_adjustment_factor",1.0) < 0.8:
                # find farmer contact via execution monitor reliability (if available) — best-effort use farmer_id as identifier
                title = "Your farm intelligence profile was updated"
                body = f"Your action schedule and advice style have been adjusted to better match your recent activity."
                immediate_send(str(farmer_id), title, body, channels=["in_app"])
    except Exception:
        pass

# ----------------------------
# Accessor for modifiers (other services can call this)
# ----------------------------
def get_modifiers_for_farmer(farmer_id: str) -> Dict[str, Any]:
    _init_profile(farmer_id)
    with _lock:
        # return a copy
        return dict(_MODIFIERS.get(farmer_id, {}))

# ----------------------------
# Convenience: bulk update / auto-tune
# ----------------------------
def auto_update_profiles(farmer_unit_map: Optional[Dict[str, List[str]]] = None, lookback_days: int = 30) -> Dict[str, Any]:
    """
    Runs update for multiple farmers.
    farmer_unit_map: optional dict farmer_id -> [unit_id, ...]. If absent, function won't be able to scan execution history (no global index).
    Returns summary of updated farmers.
    """
    updated = []
    if not farmer_unit_map:
        # nothing to do without a list of farmers and units (caller should provide)
        return {"updated_count": 0, "updated": updated}
    for farmer_id, units in farmer_unit_map.items():
        try:
            update_farmer_intelligence_profile(farmer_id, recent_unit_ids=units, lookback_days=lookback_days)
            updated.append(farmer_id)
        except Exception:
            continue
    return {"updated_count": len(updated), "updated": updated, "run_at": _now_iso()}

# ----------------------------
# Manual override endpoint helpers
# ----------------------------
def set_manual_modifier(farmer_id: str, key: str, value: Any) -> Dict[str, Any]:
    """
    Allow manual tuning of a specific modifier (e.g., priority_adjustment_factor).
    """
    _init_profile(farmer_id)
    with _lock:
        _MODIFIERS.setdefault(farmer_id, {})[key] = value
        # update profile timestamp
        _PROFILES[farmer_id]["last_updated"] = _now_iso()
    return {"farmer_id": farmer_id, "modifier_set": key, "value": value, "updated_at": _now_iso()}

def get_all_profiles() -> Dict[str, Any]:
    with _lock:
        return {"count": len(_PROFILES), "profiles": [get_farmer_profile(fid) for fid in _PROFILES.keys()]}
