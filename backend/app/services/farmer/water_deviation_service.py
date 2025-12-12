# backend/app/services/farmer/water_deviation_service.py

"""
Water Consumption vs Prediction Deviation Engine
------------------------------------------------
Features:
 - Store predicted water usage per irrigation event
 - Store actual water usage from logs
 - Compute deviation %
 - Flag anomalies (overuse / underuse)
 - Multi-event & daily deviation summaries
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
import uuid

_predicted_usage: Dict[str, Dict[str, Any]] = {}   # pid -> record
_actual_usage: Dict[str, Dict[str, Any]] = {}      # aid -> record

_pred_by_unit: Dict[str, List[str]] = {}
_actual_by_unit: Dict[str, List[str]] = {}


def _now():
    return datetime.utcnow().isoformat()


# -------------------------------------------------------------
# RECORD PREDICTED WATER USAGE
# -------------------------------------------------------------
def record_predicted_usage(
    unit_id: str,
    scheduled_date: str,
    predicted_liters: float,
    source: str = "irrigation_schedule",
    metadata: Optional[Dict[str, Any]] = None
):
    pid = f"pred_{uuid.uuid4()}"
    rec = {
        "pred_id": pid,
        "unit_id": unit_id,
        "date": scheduled_date,
        "predicted_liters": float(predicted_liters),
        "source": source,
        "metadata": metadata or {},
        "created_at": _now()
    }
    _predicted_usage[pid] = rec
    _pred_by_unit.setdefault(unit_id, []).append(pid)
    return rec


# -------------------------------------------------------------
# RECORD ACTUAL WATER USAGE
# -------------------------------------------------------------
def record_actual_usage(
    unit_id: str,
    date: str,
    actual_liters: float,
    method: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    aid = f"act_{uuid.uuid4()}"
    rec = {
        "act_id": aid,
        "unit_id": unit_id,
        "date": date,
        "actual_liters": float(actual_liters),
        "method": method,
        "metadata": metadata or {},
        "created_at": _now()
    }
    _actual_usage[aid] = rec
    _actual_by_unit.setdefault(unit_id, []).append(aid)
    return rec


# -------------------------------------------------------------
# DEVIATION CALCULATION
# -------------------------------------------------------------
def _calc_deviation(pred: float, act: float):
    if pred <= 0:
        return None
    return round((act - pred) / pred * 100.0, 2)


def analyze_deviation_for_unit(unit_id: str):
    preds = [_predicted_usage[p] for p in _pred_by_unit.get(unit_id, [])]
    acts = [_actual_usage[a] for a in _actual_by_unit.get(unit_id, [])]

    # index predictions & actuals by date
    pred_map = {}
    for p in preds:
        pred_map.setdefault(p["date"], []).append(p)

    act_map = {}
    for a in acts:
        act_map.setdefault(a["date"], []).append(a)

    results = []

    for date, p_list in pred_map.items():
        total_pred = sum(p["predicted_liters"] for p in p_list)
        total_act = sum(a["actual_liters"] for a in act_map.get(date, []))

        deviation_pct = _calc_deviation(total_pred, total_act)

        if deviation_pct is None:
            status = "no_prediction"
        else:
            if deviation_pct > 30:
                status = "overuse"
            elif deviation_pct < -30:
                status = "underuse"
            else:
                status = "normal"

        results.append({
            "date": date,
            "predicted_liters": round(total_pred, 2),
            "actual_liters": round(total_act, 2),
            "deviation_pct": deviation_pct,
            "status": status
        })

    return {
        "unit_id": unit_id,
        "events": sorted(results, key=lambda x: x["date"]),
        "timestamp": _now()
    }


# -------------------------------------------------------------
# FULL SUMMARY
# -------------------------------------------------------------
def water_deviation_summary(unit_id: str):
    return analyze_deviation_for_unit(unit_id)
