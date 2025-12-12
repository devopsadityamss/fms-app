# backend/app/services/farmer/dashboard_intel_service.py

from datetime import datetime
from typing import Dict, Any, Optional

# imports from all intelligence modules (best-effort)
try:
    from app.services.farmer.unit_service import _unit_store
except:
    _unit_store = {}

try:
    from app.services.farmer.weather_service import get_weather_snapshot_for_unit
except:
    get_weather_snapshot_for_unit = None

try:
    from app.services.farmer.task_prioritization_service import prioritize_tasks_for_unit
except:
    prioritize_tasks_for_unit = None

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

try:
    from app.services.farmer.notification_service import list_history
except:
    list_history = None

try:
    from app.services.farmer.recommendation_engine_service import generate_recommendations_for_unit
except:
    generate_recommendations_for_unit = None


def get_dashboard_for_unit(unit_id: str) -> Dict[str, Any]:
    unit = _unit_store.get(unit_id)
    if not unit:
        return {"status": "unit_not_found", "unit_id": unit_id}

    result = {
        "unit_id": unit_id,
        "unit_name": unit.get("name"),
        "crop": unit.get("crop"),
        "generated_at": datetime.utcnow().isoformat(),
        "weather": None,
        "today_tasks": [],
        "risk_alerts": [],
        "irrigation_next": None,
        "shortages": [],
        "yield_quick": None,
        "profit_quick": None,
        "benchmark": None,
        "unread_notifications": 0,
        "top_recommendations": []
    }

    # WEATHER snapshot
    if get_weather_snapshot_for_unit:
        try:
            w = get_weather_snapshot_for_unit(unit_id)
            result["weather"] = w
        except:
            pass

    # TASKS (top few)
    if prioritize_tasks_for_unit:
        try:
            t = prioritize_tasks_for_unit(unit_id)
            result["today_tasks"] = t.get("tasks", [])[:5]
        except:
            pass

    # RISK alerts
    if evaluate_risks_for_unit:
        try:
            ra = evaluate_risks_for_unit(unit_id, weather_now=None, inputs_snapshot=None, auto_record=False)
            result["risk_alerts"] = ra.get("alerts", [])
        except:
            pass

    # IRRIGATION
    if get_irrigation_schedule:
        try:
            sch = get_irrigation_schedule(unit_id)
            if sch and sch.get("events"):
                result["irrigation_next"] = sch["events"][0]
        except:
            pass

    # INPUT SHORTAGES
    if check_shortages_for_unit:
        try:
            sh = check_shortages_for_unit(unit_id)
            result["shortages"] = sh.get("shortages", [])
        except:
            pass

    # YIELD quick stats
    if forecast_yield_for_unit:
        try:
            y = forecast_yield_for_unit(unit_id)
            result["yield_quick"] = {
                "expected_quintal": y.get("expected_yield_quintal"),
                "confidence": y.get("confidence_score")
            }
        except:
            pass

    # PROFITABILITY quick stats
    if compute_profitability:
        try:
            p = compute_profitability(unit_id, market_price_per_quintal=0)
            result["profit_quick"] = {
                "total_cost": p.get("cost_breakdown", {}).get("total_cost"),
                "expected_margin_pct": p.get("margin_percent")
            }
        except:
            pass

    # BENCHMARK
    if benchmark_unit_against_peers:
        try:
            b = benchmark_unit_against_peers(unit_id)
            result["benchmark"] = {
                "yield_percentile": b.get("percentile_ranks", {}).get("yield_q_per_acre"),
                "profit_percentile": b.get("percentile_ranks", {}).get("profit_margin_pct")
            }
        except:
            pass

    # NOTIFICATIONS — unread count
    if list_history:
        try:
            h = list_history(limit=200)
            unread = [x for x in h.get("history", []) if not x.get("acknowledged")]
            result["unread_notifications"] = len(unread)
        except:
            pass

    # RECOMMENDATIONS — top few
    if generate_recommendations_for_unit:
        try:
            recs = generate_recommendations_for_unit(unit_id)
            result["top_recommendations"] = recs.get("recommendations", [])[:5]
        except:
            pass

    return result
