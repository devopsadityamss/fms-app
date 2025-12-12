# backend/app/services/farmer/performance_service.py

"""
Lightweight performance helpers:
- simple in-memory TTL cache (useful for mocking caching layer)
- simple rate-limiter stub
- batch runner helper (for later scheduled batch intelligence)
No DB usage. Pure in-process helpers to be replaced by Redis / Celery later.
"""

from datetime import datetime, timedelta
from threading import Lock
from typing import Any, Callable, Dict, Optional, Tuple, List

# Simple in-memory cache with TTL
_cache: Dict[str, Tuple[Any, datetime]] = {}
_cache_lock = Lock()


def cache_set(key: str, value: Any, ttl_seconds: int = 60):
    expire_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
    with _cache_lock:
        _cache[key] = (value, expire_at)


def cache_get(key: str) -> Optional[Any]:
    with _cache_lock:
        item = _cache.get(key)
        if not item:
            return None
        value, expire_at = item
        if datetime.utcnow() >= expire_at:
            # expired
            del _cache[key]
            return None
        return value


def cache_delete(key: str):
    with _cache_lock:
        if key in _cache:
            del _cache[key]


def cache_clear():
    with _cache_lock:
        _cache.clear()


def cache_metrics() -> Dict[str, Any]:
    with _cache_lock:
        total = len(_cache)
        keys = list(_cache.keys())
    return {"entries": total, "keys": keys}


# Simple rate-limiter stub (token-bucket-like)
_rate_limits: Dict[str, Tuple[int, datetime]] = {}
_rate_lock = Lock()


def allow_request(key: str, max_requests: int = 60, window_seconds: int = 60) -> bool:
    """
    Very simple limiting: counts requests in current window
    Key can be e.g. "user:123" or "unit:45"
    """
    now = datetime.utcnow()
    window_start = now.replace(second=0, microsecond=0)
    with _rate_lock:
        count, ts = _rate_limits.get(key, (0, window_start))
        # if window older than current window, reset
        if ts < window_start:
            count = 0
            ts = window_start
        if count >= max_requests:
            return False
        _rate_limits[key] = (count + 1, ts)
        return True


def rate_metrics() -> Dict[str, Any]:
    with _rate_lock:
        return {"tracked_keys": list(_rate_limits.keys()), "raw": _rate_limits.copy()}


# Batch runner helper — used by batch jobs to compute intelligence across units
def run_batch_jobs(job_fn: Callable[[int], Any], unit_ids: List[int]) -> Dict[int, Any]:
    """
    Runs job_fn(unit_id) for each unit_id and returns a mapping.
    In production this would be asynchronous/parallel. Here it's sequential.
    """
    results = {}
    for uid in unit_ids:
        try:
            results[uid] = job_fn(uid)
        except Exception as e:
            results[uid] = {"error": str(e)}
    return results
