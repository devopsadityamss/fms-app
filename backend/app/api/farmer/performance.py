# backend/app/api/farmer/performance.py

from fastapi import APIRouter, HTTPException
from typing import List
from app.services.farmer.performance_service import (
    cache_set,
    cache_get,
    cache_delete,
    cache_clear,
    cache_metrics,
    allow_request,
    rate_metrics,
    run_batch_jobs,
)

router = APIRouter()


@router.get("/performance/cache/{key}")
def api_cache_get(key: str):
    result = cache_get(key)
    if result is None:
        return {"key": key, "value": None, "hit": False}
    return {"key": key, "value": result, "hit": True}


@router.post("/performance/cache/{key}")
def api_cache_set(key: str, value: str, ttl: int = 60):
    cache_set(key, value, ttl_seconds=ttl)
    return {"key": key, "value": value, "ttl": ttl}


@router.delete("/performance/cache/{key}")
def api_cache_delete(key: str):
    cache_delete(key)
    return {"key": key, "deleted": True}


@router.post("/performance/cache/clear")
def api_cache_clear():
    cache_clear()
    return {"cleared": True}


@router.get("/performance/cache/metrics")
def api_cache_metrics():
    return cache_metrics()


@router.get("/performance/rate/allow")
def api_rate_check(key: str, max_requests: int = 60, window_seconds: int = 60):
    allowed = allow_request(key, max_requests=max_requests, window_seconds=window_seconds)
    return {"key": key, "allowed": allowed}


@router.get("/performance/rate/metrics")
def api_rate_metrics():
    return rate_metrics()


@router.post("/performance/batch")
def api_run_batch(unit_ids: List[int]):
    """
    Generic batch runner endpoint: expects a list of unit ids and will
    run a small mock job that returns 'ok' per unit for demo.
    In real usage, provide a job endpoint or use background tasks.
    """
    def mock_job(uid: int):
        # simple mock workload
        return {"unit_id": uid, "status": "ok"}
    results = run_batch_jobs(mock_job, unit_ids)
    return results
