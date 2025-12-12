# backend/app/services/farmer/schedule_service.py

"""
Farm Scheduling Engine (Feature 299 - Medium)

- Uses action_recommendation_service.generate_actions to obtain recommended actions.
- Groups actions into 'today', 'next_3_days', 'next_7_days'.
- Performs simple rebalancing based on labour capacity and equipment availability.
- Applies weather-aware adjustments (postpone irrigation if rain forecast).
- Degrades gracefully if dependent services are missing.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from threading import Lock
import math

# Optional imports
try:
    from app.services.farmer.action_recommendation_service import generate_actions
except Exception:
    generate_actions = None

try:
    from app.services.farmer.weather_service import get_current_weather
except Exception:
    get_current_weather = None

try:
    from app.services.farmer.labour_service import labor_summary
except Exception:
    labor_summary = None

try:
    from app.services.farmer.equipment_service import equipment_utilization, equipment_availability_risk
except Exception:
    equipment_utilization = None
    equipment_availability_risk = None

_lock = Lock()

# scheduling caps / heuristics
MAX_TODAY_ACTIONS_BASE = 6   # base number of actions considered doable in one day
LABOUR_CAPACITY_FACTOR = 0.5  # reduces today capacity if labour efficiency low
EQUIPMENT_CONFLICT_PENALTY = 1  # how many actions to push if equipment conflict

# weather thresholds
RAIN_POSTPONE_MM = 5.0  # mm in next 24h above which irrigation/spraying might be postponed

def _now_iso():
    return datetime.utcnow().isoformat()

def _is_irrigation_action(action: Dict[str, Any]) -> bool:
    cat = (action.get("category") or "").lower()
    title = (action.get("action") or "").lower()
    if "irrig" in cat or "irrig" in title or "water" in title:
        return True
    return False

def _is_spraying_action(action: Dict[str, Any]) -> bool:
    title = (action.get("action") or "").lower()
    if "spray" in title or "spraying" in title or "pesticide" in title or "spray" in action.get("category",""):
        return True
    return False

def _get_today_capacity(unit_id: Optional[int]) -> int:
    """
    Compute approximate count of actions doable today.
    Uses base cap adjusted by labour efficiency if available.
    """
    cap = MAX_TODAY_ACTIONS_BASE
    try:
        if labor_summary and unit_id is not None:
            # labour_summary returns an 'efficiency' key from existing service
            res = labor_summary(str(unit_id), stage=None, area_acres=0.0) if callable(labor_summary) else None
            if isinstance(res, dict):
                eff = res.get("efficiency", {}).get("score")
                # if eff exists and low, lower capacity
                if eff is not None:
                    try:
                        effv = float(eff)
                        # scale capacity: high efficiency -> +30%, low -> -40%
                        modifier = (effv - 50) / 100.0  # eff 50 => 0
                        cap = max(1, int(round(cap * (1 + modifier))))
                    except Exception:
                        pass
    except Exception:
        pass
    return cap

def _equipment_conflicts_count(unit_id: Optional[int]) -> int:
    """
    Heuristic: return a small integer representing equipment conflicts that should reduce today's capacity.
    """
    cnt = 0
    try:
        if equipment_availability_risk and unit_id is not None:
            res = equipment_availability_risk(unit_id)
            if isinstance(res, dict):
                sc = res.get("score", 0)
                # high risk -> push some actions
                if sc > 60:
                    cnt = 2
                elif sc > 40:
                    cnt = 1
    except Exception:
        pass
    return cnt

def _forecast_rain_next_24h(unit_id: Optional[int]) -> float:
    """
    Return forecast rainfall in next 24h (mm) if available from weather_service.
    """
    try:
        if get_current_weather and unit_id is not None:
            w = get_current_weather(unit_id) or {}
            # try keys that other services might use
            return float(w.get("forecast_rain_24h", w.get("forecast_rain_48h", w.get("rainfall_next_48h", 0))) or 0)
    except Exception:
        pass
    return 0.0

def _split_actions_by_horizon(actions: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Start by placing actions into their suggested time_horizon buckets.
    Then apply weather/equipment/labour rebalances.
    """
    today: List[Dict[str, Any]] = []
    next_3_days: List[Dict[str, Any]] = []
    next_7_days: List[Dict[str, Any]] = []

    # initial bucket by action.time_horizon
    for a in actions:
        th = a.get("time_horizon")
        if th == "today":
            today.append(a)
        elif th == "3_days" or th == "3_days":
            next_3_days.append(a)
        else:
            next_7_days.append(a)

    return {"today": today, "next_3_days": next_3_days, "next_7_days": next_7_days}

def _apply_weather_adjustments(buckets: Dict[str, List[Dict[str, Any]]], unit_id: Optional[int]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Move irrigation/spraying actions out of today if heavy rain expected.
    Prefer to keep non-weather-sensitive actions in today.
    """
    rain = _forecast_rain_next_24h(unit_id)
    if rain >= RAIN_POSTPONE_MM:
        # move irrigation and spraying scheduled for today -> next_3_days (postpone)
        new_today = []
        moved = []
        for a in buckets["today"]:
            if _is_irrigation_action(a) or _is_spraying_action(a):
                moved.append(a)
            else:
                new_today.append(a)
        buckets["today"] = new_today
        # prepend moved items into next_3_days
        buckets["next_3_days"] = moved + buckets.get("next_3_days", [])
    return buckets

def _rebalance_for_capacity(buckets: Dict[str, List[Dict[str, Any]]], unit_id: Optional[int]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Ensure 'today' bucket does not exceed capacity. Move lowest-priority items to next_3_days.
    Also account for equipment conflicts (push some actions).
    """
    today_capacity = _get_today_capacity(unit_id)
    equip_penalty = _equipment_conflicts_count(unit_id)

    effective_capacity = max(1, today_capacity - equip_penalty)

    today = buckets.get("today", [])
    if len(today) <= effective_capacity:
        return buckets

    # sort today's by priority ascending so we move least important first
    today_sorted = sorted(today, key=lambda x: x.get("priority", 0))
    num_to_move = len(today_sorted) - effective_capacity
    to_move = today_sorted[:num_to_move]
    remaining_today = today_sorted[num_to_move:]

    # move to next_3_days (append at front so they are considered earlier)
    buckets["today"] = remaining_today
    buckets["next_3_days"] = to_move + buckets.get("next_3_days", [])
    return buckets

def _normalize_action(a: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensure action contains minimal fields and normalized priority.
    """
    return {
        "action": a.get("action"),
        "category": a.get("category"),
        "priority": int(a.get("priority", 0)),
        "reason": a.get("reason"),
        "time_horizon": a.get("time_horizon", "3_days"),
        "sources": a.get("sources", []),
        "details": a.get("details", {}),
        "generated_at": a.get("generated_at", _now_iso())
    }

# ---------- Public API ----------
def generate_schedule(
    unit_id: Optional[int],
    farmer_id: Optional[str] = None,
    crop: Optional[str] = None,
    stage: Optional[str] = None,
    area_ha: Optional[float] = None,
    expected_yield_t_per_ha: Optional[float] = None,
    max_today_actions: Optional[int] = None
) -> Dict[str, Any]:
    """
    Generate schedule object grouped as:
      - today
      - next_3_days
      - next_7_days
    The function uses action_recommendation_service.generate_actions internally.
    """
    # Step 1: obtain recommended actions
    actions: List[Dict[str, Any]] = []
    if generate_actions:
        try:
            out = generate_actions(unit_id=unit_id, farmer_id=farmer_id, crop=crop, stage=stage, area_ha=area_ha, expected_yield_t_per_ha=expected_yield_t_per_ha, max_actions=30)
            actions = out.get("recommended_actions", []) or []
        except Exception:
            actions = []
    else:
        actions = []

    # normalize actions
    actions_norm = [_normalize_action(a) for a in actions]

    # Step 2: initial split by horizon
    buckets = _split_actions_by_horizon(actions_norm)

    # Step 3: weather adjustments
    buckets = _apply_weather_adjustments(buckets, unit_id)

    # Step 4: capacity + equipment rebalancing
    buckets = _rebalance_for_capacity(buckets, unit_id)

    # Step 5: ensure next_3_days not overloaded; if so move extras to next_7_days
    if len(buckets.get("next_3_days", [])) > 12:
        extra = buckets["next_3_days"][12:]
        buckets["next_3_days"] = buckets["next_3_days"][:12]
        buckets["next_7_days"] = extra + buckets.get("next_7_days", [])

    # Step 6: fill placeholders / add helpful metadata
    schedule = {
        "unit_id": unit_id,
        "farmer_id": farmer_id,
        "generated_at": _now_iso(),
        "today": buckets.get("today", []),
        "next_3_days": buckets.get("next_3_days", []),
        "next_7_days": buckets.get("next_7_days", [])
    }

    # optional: limit today's items by explicit max_today_actions param
    if max_today_actions is not None:
        if len(schedule["today"]) > int(max_today_actions):
            excess = schedule["today"][int(max_today_actions):]
            schedule["today"] = schedule["today"][:int(max_today_actions)]
            schedule["next_3_days"] = excess + schedule["next_3_days"]

    return schedule
