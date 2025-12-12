"""
Protection Advisory Service (stub-ready)
----------------------------------------

Responsibilities:
 - Provide pest & disease risk scores based on simple heuristics
 - Produce actionable recommendations (treatments, precautions)
 - Accept environmental inputs (humidity/temp) and crop stage
 - Store advisories in-memory for now
 - Future: integrate with Vision Intelligence for leaf/pest detection signals
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid


# ---------------------------------------------------------------------
# In-memory store
# ---------------------------------------------------------------------
_protect_store: Dict[str, Dict[str, Any]] = {}


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def _now() -> str:
    return datetime.utcnow().isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------
# Heuristic Risk Model (stub)
# ---------------------------------------------------------------------
def _risk_stub(crop_stage: Optional[str], humidity: Optional[float], temperature: Optional[float]) -> Dict[str, Any]:
    """
    Produces:
      - pest_risk (0–1)
      - disease_risk (0–1)
      - reason strings
    """

    # default climate
    humidity = humidity if humidity is not None else 55.0
    temperature = temperature if temperature is not None else 26.0

    base_pest = 0.2
    base_disease = 0.15

    # humidity effect
    if humidity > 70:
        base_disease += 0.25
    elif humidity > 60:
        base_disease += 0.1

    # temperature effect
    if temperature > 32:
        base_pest += 0.15
    if temperature < 20:
        base_disease -= 0.05

    # crop stage effect
    reason = []
    if crop_stage:
        stage = crop_stage.lower()
        if "vegetative" in stage:
            base_pest += 0.05
        if "flower" in stage or "blossom" in stage:
            base_disease += 0.2
        if "fruit" in stage:
            base_pest += 0.1

        reason.append(f"crop_stage={stage}")

    # clamp
    pest_score = min(1.0, max(0.0, base_pest))
    disease_score = min(1.0, max(0.0, base_disease))

    reason.append(f"humidity={humidity}")
    reason.append(f"temperature={temperature}")

    return {
        "pest_risk": round(pest_score, 2),
        "disease_risk": round(disease_score, 2),
        "reason": reason
    }


# ---------------------------------------------------------------------
# Recommendation Stub
# ---------------------------------------------------------------------
def _recommend_stub(pest_risk: float, disease_risk: float) -> List[str]:
    out = []

    # pest suggestions
    if pest_risk > 0.7:
        out.append("High pest risk — consider targeted pesticide application.")
    elif pest_risk > 0.4:
        out.append("Moderate pest risk — use pheromone traps or neem oil.")
    else:
        out.append("Low pest risk — maintain regular scouting.")

    # disease suggestions
    if disease_risk > 0.7:
        out.append("High disease risk — consider prophylactic fungicide spray.")
    elif disease_risk > 0.4:
        out.append("Moderate disease risk — ensure good irrigation spacing & airflow.")
    else:
        out.append("Low disease risk — continue routine monitoring.")

    # general advisory
    out.append("Ensure field sanitation and remove infected plant matter.")

    return out


# ---------------------------------------------------------------------
# MAIN ENTRY
# ---------------------------------------------------------------------
def generate_protection_advice(
    unit_id: Optional[str],
    crop_stage: Optional[str],
    humidity: Optional[float],
    temperature: Optional[float],
    notes: Optional[str]
) -> Dict[str, Any]:

    advisory_id = _new_id()

    risk = _risk_stub(crop_stage, humidity, temperature)
    recommendations = _recommend_stub(risk["pest_risk"], risk["disease_risk"])

    record = {
        "id": advisory_id,
        "unit_id": unit_id,
        "crop_stage": crop_stage,
        "environment": {
            "humidity": humidity,
            "temperature": temperature
        },
        "generated_at": _now(),
        "risk_assessment": risk,
        "recommendations": recommendations,
        "notes": notes,
    }

    _protect_store[advisory_id] = record
    return record


def get_advice(advisory_id: str) -> Optional[Dict[str, Any]]:
    return _protect_store.get(advisory_id)


def list_advice(unit_id: Optional[str] = None) -> Dict[str, Any]:
    items = list(_protect_store.values())
    if unit_id:
        items = [i for i in items if i.get("unit_id") == unit_id]
    return {"count": len(items), "items": items}


def _clear_store():
    """Test helper"""
    _protect_store.clear()
