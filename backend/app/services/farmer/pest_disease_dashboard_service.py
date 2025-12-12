"""
Pest & Disease Risk Dashboard Service (stub-ready)
--------------------------------------------------

Aggregates multiple risk sources for a production unit.

Inputs:
 - From protection advisory: pest / disease risk
 - From predictions bundle: pest_risk, disease_risk
 - From weather module: humidity risk / rainfall risk
 - From vision module (stub): leaf stress, yellowing ratio, pest indicators
 - Manual farmer signals: pest_sightings (0–1), leaf_damage (0–1)

Outputs:
 - Overall pest risk (0–1)
 - Overall disease risk (0–1)
 - Combined threat level (low/medium/high)
 - Recommendations
 - In-memory stored dashboard record

This is a read-synthesis module and does NOT call other modules internally—
the client should pass values directly or use fetched outputs.
"""

from typing import Dict, Any, Optional
from datetime import datetime
import uuid


_dashboard_store: Dict[str, Dict[str, Any]] = {}


def _new_id() -> str:
    return str(uuid.uuid4())


def _now() -> str:
    return datetime.utcnow().isoformat()


# ---------------------------------------------------------------------
# Weighted Stub Risk Models
# ---------------------------------------------------------------------
def _weighted_score(values: Dict[str, Optional[float]], default: float = 0.3) -> float:
    """
    values: dict of {source_name: numeric_value}
    None values are ignored.
    Final score = average of all provided numbers, else fallback.
    """
    nums = [v for v in values.values() if v is not None]
    if not nums:
        return default
    return round(sum(nums) / len(nums), 3)


def _threat_level(pest: float, disease: float) -> str:
    avg = (pest + disease) / 2
    if avg > 0.7:
        return "high"
    if avg > 0.45:
        return "medium"
    return "low"


def _recommend(pest: float, disease: float, humidity_risk: Optional[float]) -> list:
    out = []
    if pest > 0.6:
        out.append("Increase scouting frequency; consider pheromone traps.")
    if disease > 0.6:
        out.append("Monitor moisture; consider preventive fungicide application.")
    if humidity_risk and humidity_risk > 0.6:
        out.append("High humidity — increased fungal risk. Improve airflow if possible.")
    if not out:
        out.append("Conditions stable. Continue routine monitoring.")
    return out


# ---------------------------------------------------------------------
# MAIN ENTRY
# ---------------------------------------------------------------------
def build_risk_dashboard(
    unit_id: str,
    protection_pest: Optional[float] = None,
    protection_disease: Optional[float] = None,
    prediction_pest: Optional[float] = None,
    prediction_disease: Optional[float] = None,
    weather_humidity_risk: Optional[float] = None,
    weather_rainfall_risk: Optional[float] = None,
    vision_pest_indicator: Optional[float] = None,
    vision_leaf_stress: Optional[float] = None,
    farmer_pest_sightings: Optional[float] = None,   # 0–1
    farmer_leaf_damage: Optional[float] = None,       # 0–1
    notes: Optional[str] = None
) -> Dict[str, Any]:

    dash_id = _new_id()

    # Aggregate pest sources
    pest_sources = {
        "protection": protection_pest,
        "predictions": prediction_pest,
        "vision": vision_pest_indicator,
        "farmer": farmer_pest_sightings,
    }
    pest_score = _weighted_score(pest_sources)

    # Aggregate disease sources
    disease_sources = {
        "protection": protection_disease,
        "predictions": prediction_disease,
        "weather_humidity": weather_humidity_risk,
        "farmer_leaf_damage": farmer_leaf_damage,
    }
    disease_score = _weighted_score(disease_sources)

    threat = _threat_level(pest_score, disease_score)
    recs = _recommend(pest_score, disease_score, weather_humidity_risk)

    record = {
        "id": dash_id,
        "unit_id": unit_id,
        "created_at": _now(),
        "inputs": {
            "pest_sources": pest_sources,
            "disease_sources": disease_sources,
            "weather_rainfall_risk": weather_rainfall_risk,
            "vision_leaf_stress": vision_leaf_stress,
            "notes": notes,
        },
        "pest_score": pest_score,
        "disease_score": disease_score,
        "threat_level": threat,
        "recommendations": recs,
    }

    _dashboard_store[dash_id] = record
    return record


def get_dashboard_record(dash_id: str) -> Optional[Dict[str, Any]]:
    return _dashboard_store.get(dash_id)


def list_dashboards(unit_id: Optional[str] = None) -> Dict[str, Any]:
    items = list(_dashboard_store.values())
    if unit_id:
        items = [i for i in items if i.get("unit_id") == unit_id]
    return {"count": len(items), "items": items}


def _clear_store():
    _dashboard_store.clear()
