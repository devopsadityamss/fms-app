# backend/app/services/farmer/recommendation_engine_service.py

from datetime import datetime
from typing import Dict, Any, Optional, List

# Import all intelligence modules (best-effort)
try:
    from app.services.farmer.risk_alerts_service import evaluate_risks_for_unit
except:
    evaluate_risks_for_unit = None

try:
    from app.services.farmer.irrigation_service import get_irrigation_schedule
except:
    get_irrigation_schedule = None

try:
    from app.services.farmer.input_shortage_service import check_shortages_for_unit
except:
    check_shortages_for_unit = None

try:
    from app.services.farmer.task_prioritization_service import prioritize_tasks_for_unit
except:
    prioritize_tasks_for_unit = None

try:
    from app.services.farmer.yield_forecasting_service import forecast_yield_for_unit
except:
    forecast_yield_for_unit = None

try:
    from app.services.farmer.profitability_service import compute_profitability
except:
    compute_profitability = None

try:
    from app.services.farmer.peer_benchmark_service import benchmark_unit_against_peers
except:
    benchmark_unit_against_peers = None

# unit store
try:
    from app.services.farmer.unit_service import _unit_store
except:
    _unit_store = {}


def _score(high: bool = False, medium: bool = False, low: bool = False) -> int:
    """Assign numerical priority score."""
    if high:
        return 90
    if medium:
        return 70
    if low:
        return 50
    return 40


def _add(rec_list: List[Dict[str, Any]], category: str, text: str, severity: str, score: int, meta: Optional[Dict[str,Any]]=None):
    rec_list.append({
        "category": category,
        "recommendation": text,
        "severity": severity,
        "score": score,
        "meta": meta or {},
        "generated_at": datetime.utcnow().isoformat()
    })


def generate_recommendations_for_unit(
    unit_id: str,
    weather_now: Optional[Dict[str, Any]] = None,
    inputs_snapshot: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:

    unit = _unit_store.get(unit_id)
    if not unit:
        return {"status": "unit_not_found", "unit_id": unit_id}

    recs: List[Dict[str, Any]] = []

    # -------------------------------------------------------
    # 1. RISK-BASED RECOMMENDATIONS
    # -------------------------------------------------------
    if evaluate_risks_for_unit:
        risk = evaluate_risks_for_unit(unit_id, weather_now=weather_now, inputs_snapshot=inputs_snapshot, auto_record=False)
        alerts = risk.get("alerts", [])
        for a in alerts:
            sev = a.get("severity")
            if sev == "high":
                _add(
                    recs,
                    "protection",
                    f"High-risk alert: {a.get('type')} detected. Take immediate mitigation action.",
                    "high",
                    _score(high=True),
                    meta=a,
                )
            elif sev == "medium":
                _add(
                    recs,
                    "protection",
                    f"Medium-risk alert: {a.get('type')}. Monitor closely and prepare contingency.",
                    "medium",
                    _score(medium=True),
                    meta=a,
                )

    # -------------------------------------------------------
    # 2. IRRIGATION RECOMMENDATIONS
    # -------------------------------------------------------
    if get_irrigation_schedule:
        sch = get_irrigation_schedule(unit_id)
        if sch and sch.get("events"):
            next_ev = sch["events"][0]
            _add(
                recs,
                "irrigation",
                f"Upcoming irrigation scheduled on {next_ev['scheduled_date']} requiring {next_ev['apply_mm']} mm.",
                "medium",
                _score(medium=True),
                meta=next_ev
            )

            # If priority high — make a strong recommendation
            if next_ev.get("priority") == "high":
                _add(
                    recs,
                    "irrigation",
                    "Irrigation priority is HIGH — soil depletion is above safe limits.",
                    "high",
                    _score(high=True),
                    meta=next_ev
                )

    # -------------------------------------------------------
    # 3. INPUT SHORTAGE RECOMMENDATIONS
    # -------------------------------------------------------
    if check_shortages_for_unit:
        sh = check_shortages_for_unit(unit_id)
        for s in sh.get("shortages", []):
            _add(
                recs,
                "inputs",
                f"Shortage detected: {s['item_name']} — deficit {s['deficit_qty']} {s['unit']}",
                "high" if s["severity"] == "high" else "medium",
                _score(high=s["severity"]=="high", medium=s["severity"]=="medium"),
                meta=s
            )

    # -------------------------------------------------------
    # 4. TASK PRIORITY RECOMMENDATIONS
    # -------------------------------------------------------
    if prioritize_tasks_for_unit:
        tasks = prioritize_tasks_for_unit(unit_id, weather_now=weather_now, inputs_snapshot=inputs_snapshot)
        for t in tasks.get("tasks", [])[:5]:  # top 5 urgent tasks
            if t["urgency_score"] >= 80:
                _add(
                    recs,
                    "operations",
                    f"High priority task: {t['task_name']} ({t['recommended_action']})",
                    "high",
                    _score(high=True),
                    meta=t
                )
            elif t["urgency_score"] >= 60:
                _add(
                    recs,
                    "operations",
                    f"Upcoming task: {t['task_name']} should be scheduled soon.",
                    "medium",
                    _score(medium=True),
                    meta=t
                )

    # -------------------------------------------------------
    # 5. YIELD FORECAST RECOMMENDATIONS
    # -------------------------------------------------------
    if forecast_yield_for_unit:
        yf = forecast_yield_for_unit(unit_id)
        if yf.get("expected_yield_quintal") and yf.get("confidence_score", 80) < 60:
            _add(
                recs,
                "yield",
                "Yield forecast confidence is low — review crop practices and nutrient status.",
                "medium",
                _score(medium=True),
                meta=yf,
            )

    # -------------------------------------------------------
    # 6. PROFITABILITY RECOMMENDATIONS
    # -------------------------------------------------------
    if compute_profitability:
        pf = compute_profitability(unit_id, market_price_per_quintal=0)
        margin = pf.get("margin_percent")
        if margin is not None and margin < 10:
            _add(
                recs,
                "finance",
                "Profit margin is low — consider cost reduction or input optimization.",
                "medium",
                _score(medium=True),
                meta=pf,
            )

    # -------------------------------------------------------
    # 7. PEER BENCHMARKING RECOMMENDATIONS
    # -------------------------------------------------------
    if benchmark_unit_against_peers:
        bn = benchmark_unit_against_peers(unit_id)
        for note in bn.get("notes", []):
            _add(
                recs,
                "benchmarking",
                note,
                "low",
                _score(low=True),
                meta=bn
            )

    # -------------------------------------------------------
    # Sort final recommendations by score (desc)
    # -------------------------------------------------------
    recs_sorted = sorted(recs, key=lambda x: x["score"], reverse=True)

    return {
        "unit_id": unit_id,
        "recommendations": recs_sorted,
        "count": len(recs_sorted),
        "generated_at": datetime.utcnow().isoformat()
    }
