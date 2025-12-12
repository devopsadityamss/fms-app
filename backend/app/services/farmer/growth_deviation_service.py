"""
Growth Deviation Service (stub-ready)
------------------------------------

This module evaluates crop growth deviation using simple heuristics:
 - expected_height vs. observed_height
 - optional canopy_coverage signal (stub)
 - optional ndvi_score (stub)
 - crop_stage adjustments

Outputs:
 - deviation_status (ahead | normal | lagging | stressed)
 - confidence score (0–1) based on how strong the deviation is
 - contributing factors
 - stored advisory record (in-memory)

Replace heuristics with ML or model-driven agronomy logic later.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid


# ---------------------------------------------------------------------
# In-memory store
# ---------------------------------------------------------------------
_growth_store: Dict[str, Dict[str, Any]] = {}


def _now() -> str:
    return datetime.utcnow().isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------
# Stub Growth Logic
# ---------------------------------------------------------------------
def _evaluate_height(expected: Optional[float], observed: Optional[float]) -> Dict[str, Any]:
    """Basic height deviation scoring."""
    if expected is None or observed is None:
        return {"delta": None, "height_factor": None}

    delta = observed - expected
    height_factor = delta / expected if expected > 0 else 0
    return {"delta": delta, "height_factor": height_factor}


def _evaluate_canopy(canopy: Optional[float]) -> str:
    """
    canopy coverage 0–1
    """
    if canopy is None:
        return "unknown"

    if canopy > 0.75:
        return "dense"
    if canopy > 0.45:
        return "moderate"
    return "sparse"


def _evaluate_ndvi(ndvi: Optional[float]) -> str:
    """NDVI 0–1."""
    if ndvi is None:
        return "unknown"

    if ndvi > 0.7:
        return "healthy"
    if ndvi > 0.45:
        return "moderate"
    return "low"


def _derive_status(
    height_factor: Optional[float],
    canopy_state: str,
    ndvi_state: str
) -> str:
    """
    Combine different signals to classify growth deviation.
    """

    # Height rule
    if height_factor is None:
        height_status = "unknown"
    elif height_factor > 0.15:
        height_status = "ahead"
    elif height_factor < -0.15:
        height_status = "lagging"
    else:
        height_status = "normal"

    # Combine
    if height_status == "lagging" or ndvi_state == "low":
        return "stressed"
    if height_status == "ahead" and canopy_state == "dense":
        return "ahead"
    return height_status


def _confidence(height_factor: Optional[float], ndvi_state: str) -> float:
    """
    Produce a simple confidence score.
    """
    base = 0.5

    if height_factor is not None:
        base += min(0.4, abs(height_factor))  # stronger deviations more confident

    if ndvi_state == "low":
        base += 0.1

    return round(min(1.0, max(0.0, base)), 2)


# ---------------------------------------------------------------------
# MAIN ENTRY
# ---------------------------------------------------------------------
def analyze_growth(
    unit_id: Optional[str],
    expected_height: Optional[float],
    observed_height: Optional[float],
    canopy_coverage: Optional[float],
    ndvi_score: Optional[float],
    crop_stage: Optional[str] = None,
    notes: Optional[str] = None
) -> Dict[str, Any]:

    advisory_id = _new_id()

    height_eval = _evaluate_height(expected_height, observed_height)
    canopy_state = _evaluate_canopy(canopy_coverage)
    ndvi_state = _evaluate_ndvi(ndvi_score)

    status = _derive_status(height_eval["height_factor"], canopy_state, ndvi_state)
    conf = _confidence(height_eval["height_factor"], ndvi_state)

    record = {
        "id": advisory_id,
        "unit_id": unit_id,
        "generated_at": _now(),
        "inputs": {
            "expected_height": expected_height,
            "observed_height": observed_height,
            "canopy_coverage": canopy_coverage,
            "ndvi_score": ndvi_score,
            "crop_stage": crop_stage
        },
        "analysis": {
            "height": height_eval,
            "canopy_state": canopy_state,
            "ndvi_state": ndvi_state,
        },
        "deviation_status": status,
        "confidence": conf,
        "notes": notes,
    }

    _growth_store[advisory_id] = record
    return record


def get_growth_analysis(advisory_id: str) -> Optional[Dict[str, Any]]:
    return _growth_store.get(advisory_id)


def list_growth_analyses(unit_id: Optional[str] = None) -> Dict[str, Any]:
    items = list(_growth_store.values())
    if unit_id:
        items = [i for i in items if i.get("unit_id") == unit_id]
    return {"count": len(items), "items": items}


def _clear_store():
    _growth_store.clear()
