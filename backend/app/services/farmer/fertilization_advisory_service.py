"""
Fertilization Advisory Service (stub-ready)
------------------------------------------

Responsibilities:
 - Provide NPK recommendations based on simple heuristics
 - Accept optional soil & crop parameters
 - Generate advisory notes (timing, caution, deficiency hints)
 - Store each advisory request & result (in-memory)
 - Future-ready: Replace stub rules with ML / agronomy engines

This module does NOT depend on DB or external services yet.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

# ---------------------------------------------------------------------
# In-memory store: advisory_id -> advisory record
# ---------------------------------------------------------------------
_fert_store: Dict[str, Dict[str, Any]] = {}


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def _now() -> str:
    return datetime.utcnow().isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------
# Stub-Based Fertilization Logic
# ---------------------------------------------------------------------
def _npk_stub(soil_n: Optional[float], soil_p: Optional[float], soil_k: Optional[float]) -> Dict[str, Any]:
    """
    Very basic heuristic:
     - Low N -> recommend higher nitrogen
     - Low P -> recommend higher phosphorus
     - Low K -> recommend higher potassium

    Replace with ML or agronomy model later.
    """

    # Default mid-range values if none provided
    soil_n = soil_n if soil_n is not None else 0.5
    soil_p = soil_p if soil_p is not None else 0.5
    soil_k = soil_k if soil_k is not None else 0.5

    rec_n = 50 if soil_n < 0.4 else 30
    rec_p = 40 if soil_p < 0.4 else 20
    rec_k = 40 if soil_k < 0.4 else 25

    return {
        "recommended_n": rec_n,
        "recommended_p": rec_p,
        "recommended_k": rec_k,
        "soil_profile": {"n": soil_n, "p": soil_p, "k": soil_k},
    }


def _timing_stub(crop_stage: Optional[str]) -> str:
    """
    Suggest fertilization timing based on crop growth stage.
    """
    if not crop_stage:
        return "Apply during early vegetative stage for best nutrient uptake."

    crop_stage = crop_stage.lower()

    if "vegetative" in crop_stage:
        return "Ideal time: split application during vegetative growth."
    if "flowering" in crop_stage:
        return "Reduce nitrogen; focus on P & K to support reproductive growth."
    if "fruiting" in crop_stage or "pod" in crop_stage:
        return "Avoid late N application; encourage potassium supplementation."

    return "Use balanced fertilizers unless agronomy data suggests otherwise."


def _deficiency_stub(soil_n: float, soil_p: float, soil_k: float) -> List[str]:
    out = []
    if soil_n < 0.3:
        out.append("Possible nitrogen deficiency")
    if soil_p < 0.3:
        out.append("Possible phosphorus deficiency")
    if soil_k < 0.3:
        out.append("Possible potassium deficiency")
    return out or ["No major deficiencies indicated"]


# ---------------------------------------------------------------------
# Main Entry
# ---------------------------------------------------------------------
def generate_fertilization_advice(
    unit_id: Optional[str],
    crop_stage: Optional[str],
    soil_n: Optional[float],
    soil_p: Optional[float],
    soil_k: Optional[float],
    notes: Optional[str] = None
) -> Dict[str, Any]:

    advisory_id = _new_id()

    npk = _npk_stub(soil_n, soil_p, soil_k)
    timing = _timing_stub(crop_stage)
    deficiencies = _deficiency_stub(npk["soil_profile"]["n"], npk["soil_profile"]["p"], npk["soil_profile"]["k"])

    record = {
        "id": advisory_id,
        "unit_id": unit_id,
        "crop_stage": crop_stage,
        "soil_inputs": {"n": soil_n, "p": soil_p, "k": soil_k},
        "generated_at": _now(),
        "npk_recommendation": npk,
        "timing_suggestion": timing,
        "deficiency_hints": deficiencies,
        "notes": notes,
    }

    _fert_store[advisory_id] = record
    return record


def get_advisory(advisory_id: str) -> Dict[str, Any]:
    return _fert_store.get(advisory_id)


def list_advisories(unit_id: Optional[str] = None) -> Dict[str, Any]:
    items = list(_fert_store.values())
    if unit_id:
        items = [i for i in items if i.get("unit_id") == unit_id]
    return {"count": len(items), "items": items}


def _clear_store():
    """For testing only."""
    _fert_store.clear()
