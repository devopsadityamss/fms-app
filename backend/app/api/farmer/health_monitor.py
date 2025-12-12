# backend/app/api/farmer/health_monitor.py

from fastapi import APIRouter

from app.services.farmer.health_monitor_service import (
    heartbeat,
    engine_health_probe,
    estimate_latency,
    plugin_health,
    quick_risk_check,
    system_health,
)

router = APIRouter()


@router.get("/health")
def api_health():
    return heartbeat()


@router.get("/health/engine")
def api_engine_health(unit_id: int = 1, stage: str = "vegetative"):
    return engine_health_probe(unit_id, stage)


@router.get("/health/cache")
def api_cache_health():
    return estimate_latency()


@router.get("/health/plugins")
def api_plugin_health():
    return plugin_health()


@router.get("/health/latency")
def api_latency():
    return estimate_latency()


@router.get("/health/risk-check")
def api_risk_check(unit_id: int, stage: str):
    return quick_risk_check(unit_id, stage)


@router.get("/health/system")
def api_system_health():
    return system_health()
