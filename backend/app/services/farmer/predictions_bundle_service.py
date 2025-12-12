"""
Overall Predictions Bundle Service (stub-ready)
-----------------------------------------------

This module aggregates multiple crop condition signals into a unified
"prediction bundle" that gives farmers a high-level view of their field status.

Inputs:
 - unit_id
 - optional parameters (growth metrics, soil metrics, weather signals)
 - optional references to results from other modules (growth deviation id, vision id, etc.)

Outputs:
 - unified scores (health/pest/disease/nutrient/moisture/growth)
 - a simple overall recommendation summary
 - confidence estimation
 - in-memory stored prediction bundle

Later:
 - Replace with ML ensemble or field-level analytics engine.
"""

from typing import Dict, Any, Optional
from datetime import datetime
import uuid

# In-memory store
_bundle_store: Dict[str, Dict[str, Any]] = {}


def _now() -> str:
    return datetime.utcnow().isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


# -------------------------------------------------------------
# Stub signal estimators
# -------------------------------------------------------------
def _health_stub(ndvi: Optional[float], canopy: Optional[float]) -> float:
    """0–1 scale."""
    score = 0.5
    if ndvi is not None:
        score += (ndvi - 0.5) * 0.5
    if canopy is not None:
        score += (canopy - 0.5) * 0.3
    return round(max(0.0, min(1.0, score)), 2)


def _pest_stub(humidity: Optional[float]) -> float:
    if humidity is None:
        return 0.3
    if humidity > 70:
        return 0.7
    if humidity > 60:
        return 0.5
    return 0.3


def _disease_stub(humidity: Optional[float], temp: Optional[float]) -> float:
    score = 0.3
    if humidity and humidity > 70:
        score += 0.3
    if temp and temp > 32:
        score += 0.1
    return round(min(score, 1.0), 2)


def _nutrient_stub(n: Optional[float], p: Optional[float], k: Optional[float]) -> float:
    """Lower soil nutrients → higher nutrient risk."""
    if n is None and p is None and k is None:
        return 0.3

    risk = 0.0
    for v in (n, p, k):
        if v is not None and v < 0.4:
            risk += 0.2
    return round(min(1.0, risk), 2)


def _moisture_stub(moisture: Optional[float]) -> float:
    """Assume moisture 0–1 range."""
    if moisture is None:
        return 0.5
    if moisture < 0.3:
        return 0.8  # high risk (too dry)
    if moisture > 0.8:
        return 0.6  # risk of disease
    return 0.3


def _growth_stub(growth_delta: Optional[float]) -> float:
    """delta negative → stress"""
    if growth_delta is None:
        return 0.5
    if growth_delta > 0:
        return 0.3
    if growth_delta < -10:
        return 0.8
    return 0.6


def _overall_confidence(signals: Dict[str, float]) -> float:
    """
    Confidence based on consistency of signals.
    """
    vals = list(signals.values())
    spread = max(vals) - min(vals)
    base = 0.6 - (spread * 0.2)
    return round(max(0.2, min(1.0, base)), 2)


def _insight_stub(signals: Dict[str, float]) -> str:
    """
    Simple human-readable insight.
    """
    if signals["pest_risk"] > 0.6:
        return "Potential pest risk detected — consider scouting and preventive action."
    if signals["disease_risk"] > 0.6:
        return "High disease risk — monitor humidity and crop canopy."
    if signals["nutrient_risk"] > 0.6:
        return "Possible nutrient deficiency — consider soil testing or split application."
    if signals["moisture_risk"] > 0.6:
        return "Soil moisture imbalance — irrigation adjustment recommended."
    return "Conditions appear stable with low immediate threats."


# -------------------------------------------------------------
# MAIN ENTRY
# -------------------------------------------------------------
def generate_predictions_bundle(
    unit_id: str,
    ndvi: Optional[float] = None,
    canopy: Optional[float] = None,
    humidity: Optional[float] = None,
    temperature: Optional[float] = None,
    soil_n: Optional[float] = None,
    soil_p: Optional[float] = None,
    soil_k: Optional[float] = None,
    soil_moisture: Optional[float] = None,
    growth_delta: Optional[float] = None,
    notes: Optional[str] = None
) -> Dict[str, Any]:

    bundle_id = _new_id()

    signals = {
        "health_score": _health_stub(ndvi, canopy),
        "pest_risk": _pest_stub(humidity),
        "disease_risk": _disease_stub(humidity, temperature),
        "nutrient_risk": _nutrient_stub(soil_n, soil_p, soil_k),
        "moisture_risk": _moisture_stub(soil_moisture),
        "growth_risk": _growth_stub(growth_delta),
    }

    insight = _insight_stub(signals)
    confidence = _overall_confidence(signals)

    record = {
        "id": bundle_id,
        "unit_id": unit_id,
        "generated_at": _now(),
        "inputs": {
            "ndvi": ndvi,
            "canopy": canopy,
            "humidity": humidity,
            "temperature": temperature,
            "soil_n": soil_n,
            "soil_p": soil_p,
            "soil_k": soil_k,
            "soil_moisture": soil_moisture,
            "growth_delta": growth_delta,
        },
        "signals": signals,
        "overall_confidence": confidence,
        "insight": insight,
        "notes": notes,
    }

    _bundle_store[bundle_id] = record
    return record


def get_bundle(bundle_id: str) -> Optional[Dict[str, Any]]:
    return _bundle_store.get(bundle_id)


def list_bundles(unit_id: Optional[str] = None) -> Dict[str, Any]:
    items = list(_bundle_store.values())
    if unit_id:
        items = [i for i in items if i.get("unit_id") == unit_id]
    return {"count": len(items), "items": items}


def _clear_store():
    _bundle_store.clear()
