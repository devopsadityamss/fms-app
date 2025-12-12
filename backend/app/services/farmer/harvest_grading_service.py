# backend/app/services/farmer/harvest_grading_service.py
"""
Harvest Lot Grading & Moisture Scoring (Feature 332)

Provides:
 - auto_grade_lot(lot_id): compute grade category using latest quality tests
 - compute_moisture_score(lot_id): normalized score (0-100) from moisture & dockage
 - moisture_trend(lot_id): time-series of moisture values from tests
 - recommend_drying_action(lot_id): actionable drying advice (target moisture, hours estimate)
 - grade_summary_for_farmer(farmer_id): quick overview of lot grades
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from threading import Lock
import statistics
import math

# defensive imports (best-effort)
try:
    from app.services.farmer.harvest_lot_service import (
        list_quality_tests,
        compute_lot_quality_score,
        get_harvest_lot,
        list_lots_by_farmer,
        record_quality_test
    )
except Exception:
    # fallbacks to avoid hard dependency errors
    list_quality_tests = lambda lot_id: []
    compute_lot_quality_score = lambda lot_id: {"lot_id": lot_id, "score": None, "components": {}}
    get_harvest_lot = lambda lot_id: {}
    list_lots_by_farmer = lambda farmer_id: []
    record_quality_test = lambda *args, **kwargs: {"error": "not_available"}

_lock = Lock()


def _now_iso():
    return datetime.utcnow().isoformat()


# -----------------------
# Moisture score calculation
# -----------------------
def compute_moisture_score(lot_id: str) -> Dict[str, Any]:
    """
    Score rules:
     - ideal moisture <= 12% -> no penalty
     - penalty of 4 points per % above 12 upto 18%
     - large penalty beyond 18%
     - dockage reduces score too (1.5 points per %)
     - score clipped 0..100
    Returns components and final score.
    """
    tests = list_quality_tests(lot_id)
    if not tests:
        return {"lot_id": lot_id, "score": None, "components": {}, "reason": "no_tests"}

    moist_vals = [t["moisture_pct"] for t in tests if t.get("moisture_pct") is not None]
    dock_vals = [t["dockage_pct"] for t in tests if t.get("dockage_pct") is not None]

    if not moist_vals:
        return {"lot_id": lot_id, "score": None, "components": {}, "reason": "no_moisture_data"}

    avg_moist = statistics.mean(moist_vals)
    avg_dock = statistics.mean(dock_vals) if dock_vals else 0.0

    score = 100.0
    components = {"avg_moisture_pct": round(avg_moist,2), "avg_dockage_pct": round(avg_dock,2)}

    if avg_moist > 12.0:
        if avg_moist <= 18.0:
            penalty = (avg_moist - 12.0) * 4.0
        else:
            penalty = (6.0 * 4.0) + (avg_moist - 18.0) * 8.0  # steeper beyond 18%
        score -= penalty
        components["moisture_penalty"] = round(penalty,2)
    else:
        components["moisture_penalty"] = 0.0

    dock_penalty = avg_dock * 1.5
    score -= dock_penalty
    components["dockage_penalty"] = round(dock_penalty,2)

    # small bonus if moisture <=11 and dockage low
    if avg_moist <= 11.0 and avg_dock <= 2.0:
        score += 2.0
        components["bonus_low_moisture"] = 2.0

    score = max(0.0, min(100.0, round(score,2)))
    components["final_score"] = score

    return {"lot_id": lot_id, "score": score, "components": components, "generated_at": _now_iso()}


# -----------------------
# Auto grading
# -----------------------
def auto_grade_lot(lot_id: str) -> Dict[str, Any]:
    """
    Determines grade category:
     - If quality_score >= 90 -> 'A' / 'Premium'
     - 75 <= score < 90 -> 'B' / 'Standard'
     - <75 -> 'C' / 'Low'
    Combines moisture_score and quality score. Returns grade, reasons, and suggested price_factor (multiplier).
    """
    qscore_res = compute_lot_quality_score(lot_id)
    mscore_res = compute_moisture_score(lot_id)

    # pick available numeric score; prefer qscore final_score if present else moisture
    qscore = qscore_res.get("score")
    mscore = mscore_res.get("score")
    # normalize: if one missing use the other
    if qscore is None and mscore is None:
        return {"lot_id": lot_id, "error": "no_quality_data"}
    if qscore is None:
        combined = mscore
    elif mscore is None:
        combined = qscore
    else:
        # weight: quality 0.6, moisture 0.4
        combined = round(0.6 * float(qscore) + 0.4 * float(mscore), 2)

    if combined >= 90:
        grade = "A"
        label = "Premium"
        price_factor = 1.15
    elif combined >= 75:
        grade = "B"
        label = "Standard"
        price_factor = 1.0
    else:
        grade = "C"
        label = "Low"
        price_factor = 0.85

    reasons = {
        "quality_score": qscore,
        "moisture_score": mscore,
        "combined_score": combined
    }

    # suggested actions
    actions = []
    if mscore_res.get("components", {}).get("avg_moisture_pct", 999) > 14.0:
        actions.append("requires_drying")
    if qscore is not None and qscore < 60:
        actions.append("consider_reject_or_blending")

    return {
        "lot_id": lot_id,
        "grade": grade,
        "label": label,
        "combined_score": combined,
        "price_factor": price_factor,
        "reasons": reasons,
        "actions": actions,
        "generated_at": _now_iso()
    }


# -----------------------
# Moisture trend (time series)
# -----------------------
def moisture_trend(lot_id: str) -> Dict[str, Any]:
    tests = list_quality_tests(lot_id)
    if not tests:
        return {"lot_id": lot_id, "trend": [], "reason": "no_tests"}

    # sort by recorded_at if available else date field
    def _ts_key(t):
        return t.get("recorded_at") or t.get("date") or ""
    sorted_tests = sorted(tests, key=_ts_key)
    timeline = []
    for t in sorted_tests:
        if t.get("moisture_pct") is None:
            continue
        timeline.append({"recorded_at": t.get("recorded_at") or t.get("date"), "moisture_pct": t.get("moisture_pct")})

    # compute simple trend slope (delta per test)
    if len(timeline) >= 2:
        vals = [p["moisture_pct"] for p in timeline]
        slope = (vals[-1] - vals[0]) / (len(vals)-1)
    else:
        slope = 0.0

    return {"lot_id": lot_id, "trend": timeline, "slope_per_test": round(slope,3), "generated_at": _now_iso()}


# -----------------------
# Drying recommendation
# -----------------------
def recommend_drying_action(lot_id: str, ambient_temp_c: Optional[float] = None, ambient_humidity_pct: Optional[float] = None) -> Dict[str, Any]:
    """
    Recommend drying target & rough hours:
     - target moisture: 11.0% (default) or lower for premium
     - estimate hours = k * (current_moisture - target) where k depends on ambient conditions ~ 8 hours per % at mild conditions
    This is a heuristic stub.
    """
    mres = compute_moisture_score(lot_id)
    comps = mres.get("components", {})
    avg_moist = comps.get("avg_moisture_pct")
    if avg_moist is None:
        return {"lot_id": lot_id, "error": "no_moisture_data"}

    target = 11.0
    # if ambient humidity high, increase hours per % by factor
    base_hours_per_pct = 8.0
    factor = 1.0
    if ambient_temp_c is not None and ambient_temp_c < 15.0:
        factor += 0.2
    if ambient_humidity_pct is not None and ambient_humidity_pct > 70.0:
        factor += 0.4

    if avg_moist <= target:
        return {"lot_id": lot_id, "message": "moisture_at_or_below_target", "avg_moisture_pct": avg_moist, "recommended_hours": 0.0, "target_moisture": target}

    delta = max(0.0, avg_moist - target)
    hours = round(delta * base_hours_per_pct * factor, 2)

    advice = {
        "lot_id": lot_id,
        "avg_moisture_pct": avg_moist,
        "target_moisture": target,
        "estimated_drying_hours": hours,
        "hours_per_percent": round(base_hours_per_pct * factor,2),
        "notes": "heuristic estimate; use calibrated dryer metrics for accuracy",
        "generated_at": _now_iso()
    }
    return advice


# -----------------------
# Farmer-level grade summary
# -----------------------
def grade_summary_for_farmer(farmer_id: str) -> Dict[str, Any]:
    lots = list_lots_by_farmer(farmer_id)
    out = []
    for l in lots:
        lid = l.get("lot_id")
        ag = auto_grade_lot(lid)
        out.append({"lot_id": lid, "crop": l.get("crop"), "grade": ag.get("grade"), "combined_score": ag.get("combined_score")})
    return {"farmer_id": farmer_id, "summary": out, "generated_at": _now_iso()}
