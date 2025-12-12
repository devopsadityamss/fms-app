# backend/app/services/farmer/health_monitor_service.py

"""
System Health & Monitoring Layer

Provides:
- API heartbeat
- Cache metrics
- Plugin system health
- Intelligence engine health check
- Latency estimation mock
- Mini risk-check (quick validated response)
"""

from datetime import datetime
import time
from typing import Dict, Any

from app.services.farmer.performance_service import cache_metrics
from app.services.farmer.plugin_registry_service import list_plugins
from app.services.farmer.risk_service import compute_unified_risk
from app.services.farmer.weather_service import get_current_weather
from app.services.farmer.health_service import get_crop_health_score
from app.services.farmer.soil_service import get_soil_intelligence
from app.services.farmer.cost_service import get_cost_analysis
from app.services.farmer.market_service import get_market_intelligence
from app.services.farmer.pest_service import get_pest_intel


# -------------------------------------------------
# 1. Basic heartbeat
# -------------------------------------------------

def heartbeat() -> Dict[str, Any]:
    return {
        "status": "ok",
        "timestamp": datetime.utcnow(),
        "message": "Farmer intelligence backend is running."
    }


# -------------------------------------------------
# 2. Intelligence engine health probe (mock)
# -------------------------------------------------

def engine_health_probe(unit_id: int = 1, stage: str = "vegetative") -> Dict[str, Any]:
    """
    Validates that core intelligence components are callable.
    It does NOT run full intelligence engine.
    """
    weather = get_current_weather(unit_id)
    health = get_crop_health_score(unit_id, stage, weather)
    soil = get_soil_intelligence(unit_id)
    cost = get_cost_analysis(unit_id, stage, actual_cost_spent=0)

    return {
        "timestamp": datetime.utcnow(),
        "weather_ok": weather is not None,
        "health_ok": health is not None,
        "soil_ok": soil is not None,
        "cost_ok": cost is not None,
        "overall_status": "ok"
    }


# -------------------------------------------------
# 3. Latency benchmark mock
# -------------------------------------------------

def estimate_latency() -> Dict[str, Any]:
    start = time.time()
    # Do a quick call to internal mock components
    _ = cache_metrics()
    end = time.time()
    return {
        "timestamp": datetime.utcnow(),
        "latency_ms": round((end - start) * 1000, 2)
    }


# -------------------------------------------------
# 4. Plugin health
# -------------------------------------------------

def plugin_health() -> Dict[str, Any]:
    plugins = list_plugins()
    return {
        "timestamp": datetime.utcnow(),
        "plugin_count": len(plugins),
        "plugins": plugins
    }


# -------------------------------------------------
# 5. Risk quick-check
# -------------------------------------------------

def quick_risk_check(unit_id: int, stage: str) -> Dict[str, Any]:
    weather = get_current_weather(unit_id)
    health = get_crop_health_score(unit_id, stage, weather)
    soil = get_soil_intelligence(unit_id)
    cost = get_cost_analysis(unit_id, stage, actual_cost_spent=0)
    market = get_market_intelligence(unit_id)
    pest = get_pest_intel(unit_id, stage, weather)

    risk_summary = compute_unified_risk(
        unit_id=unit_id,
        weather=weather,
        pest_intel=pest,
        health=health,
        soil=soil,
        cost=cost,
        market=market,
    )

    return {
        "timestamp": datetime.utcnow(),
        "unified_risk": risk_summary["unified_score"],
        "risk_breakdown": risk_summary["breakdown"],
        "recommendations": risk_summary["recommendations"]
    }


# -------------------------------------------------
# 6. System health overview
# -------------------------------------------------

def system_health() -> Dict[str, Any]:
    return {
        "timestamp": datetime.utcnow(),
        "heartbeat": heartbeat(),
        "engine": engine_health_probe(),
        "cache": cache_metrics(),
        "plugins": plugin_health(),
        "latency": estimate_latency()
    }
