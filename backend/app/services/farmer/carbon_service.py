# backend/app/services/farmer/carbon_service.py

"""
Farm Carbon Footprint & Sustainability Engine (in-memory)

Features:
 - Record emission or sequestration events
 - Estimate emissions from:
      fertilizer usage
      pesticide usage
      irrigation (electric or diesel)
      fuel usage (tractors, pumps)
      machinery hours
      tillage operations
 - Estimate sequestration:
      soil OC increase
      cover crops
      tree count (agroforestry)
 - Compute sustainability score
 - Provide suggestions
"""

from datetime import datetime
from typing import Dict, List, Any, Optional
import uuid

# Stores
_carbon_events: Dict[str, Dict[str, Any]] = {}
_carbon_by_unit: Dict[str, List[str]] = {}


def _now():
    return datetime.utcnow().isoformat()


# -------------------------------------------------------------
# RECORD EMISSION / SEQUESTRATION EVENT
# -------------------------------------------------------------
def record_carbon_event(
    farmer_id: str,
    unit_id: str,
    event_type: str,   # "emission" or "sequestration"
    category: str,     # fertilizer, fuel, irrigation, tillage, cover_crop, soil_oc, etc.
    value: float,      # CO₂e in kg
    description: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    eid = f"carbon_{uuid.uuid4()}"
    rec = {
        "event_id": eid,
        "farmer_id": farmer_id,
        "unit_id": str(unit_id),
        "event_type": event_type,
        "category": category,
        "value_kg_co2e": float(value),
        "description": description or "",
        "metadata": metadata or {},
        "timestamp": _now()
    }
    _carbon_events[eid] = rec
    _carbon_by_unit.setdefault(str(unit_id), []).append(eid)
    return rec


# -------------------------------------------------------------
# LIST EVENTS
# -------------------------------------------------------------
def list_carbon_events(unit_id: str) -> List[Dict[str, Any]]:
    ids = _carbon_by_unit.get(str(unit_id), [])
    return [_carbon_events[i] for i in ids]


# -------------------------------------------------------------
# CALCULATIONS
# -------------------------------------------------------------
def calculate_unit_carbon_balance(unit_id: str) -> Dict[str, Any]:
    events = list_carbon_events(unit_id)

    total_emissions = sum(e["value_kg_co2e"] for e in events if e["event_type"] == "emission")
    total_sequestration = sum(e["value_kg_co2e"] for e in events if e["event_type"] == "sequestration")

    net = total_emissions - total_sequestration

    return {
        "unit_id": unit_id,
        "total_emissions_kg": round(total_emissions, 2),
        "total_sequestration_kg": round(total_sequestration, 2),
        "net_carbon_kg": round(net, 2)
    }


# -------------------------------------------------------------
# SUSTAINABILITY SCORE (0–100)
# -------------------------------------------------------------
def sustainability_score(unit_id: str) -> Dict[str, Any]:
    bal = calculate_unit_carbon_balance(unit_id)

    emissions = bal["total_emissions_kg"]
    sequestration = bal["total_sequestration_kg"]

    # simple formula:
    #  high sequestration → high score
    #  high emissions → low score
    if emissions == 0:
        score = 100
    else:
        ratio = max(0, min(sequestration / emissions, 2))  # cap for sanity
        score = int(ratio * 50 + (50 - min(emissions / 1000, 50)))

    score = max(0, min(score, 100))

    return {
        "unit_id": unit_id,
        "score": score,
        "details": bal
    }


# -------------------------------------------------------------
# SUGGESTIONS
# -------------------------------------------------------------
def sustainability_suggestions(unit_id: str) -> Dict[str, Any]:
    bal = calculate_unit_carbon_balance(unit_id)
    suggestions = []

    if bal["total_emissions_kg"] > 200:
        suggestions.append("Reduce tractor tillage — switch to minimum till or zero till.")
    if bal["total_emissions_kg"] > 100:
        suggestions.append("Optimize fertilizer usage — consider soil testing & split application.")
    if bal["total_sequestration_kg"] < 50:
        suggestions.append("Introduce cover crops to enhance soil carbon.")
    if bal["total_sequestration_kg"] < 30:
        suggestions.append("Add compost/FYM to increase organic matter.")
    if bal["net_carbon_kg"] > 0:
        suggestions.append("Plant agroforestry trees to offset emissions.")
    if not suggestions:
        suggestions.append("Great job! You maintain excellent sustainability practices.")

    return {
        "unit_id": unit_id,
        "suggestions": suggestions
    }


# -------------------------------------------------------------
# FULL SUMMARY
# -------------------------------------------------------------
def carbon_summary(unit_id: str) -> Dict[str, Any]:
    return {
        "summary": calculate_unit_carbon_balance(unit_id),
        "sustainability_score": sustainability_score(unit_id),
        "suggestions": sustainability_suggestions(unit_id),
        "events": list_carbon_events(unit_id),
        "timestamp": _now()
    }

# -------------------------------------------------------------
# CARBON CREDITS CALCULATION (NEW EXTENSION)
# -------------------------------------------------------------

def calculate_carbon_credits(unit_id: str, price_per_t_co2: float = 6.0) -> Dict[str, Any]:
    """
    Uses existing carbon balance:
      - If net carbon is NEGATIVE => farmer is sequestering more than emitting
      - Eligible credits = (-net_carbon_kg / 1000)  # convert kg → tonnes CO2e
      - Otherwise no credits

    price_per_t_co2 = market / program price for carbon credit (USD or INR equivalent)

    Returns:
      - eligible_credits_t  (tCO2e)
      - estimated_value     (price × credits)
    """
    bal = calculate_unit_carbon_balance(unit_id)
    net_kg = bal["net_carbon_kg"]

    # Negative net = sequestration surplus (credit eligible)
    if net_kg < 0:
        eligible_tonnes = round(abs(net_kg) / 1000.0, 4)
    else:
        eligible_tonnes = 0.0

    estimated_value = round(eligible_tonnes * float(price_per_t_co2), 2)

    return {
        "unit_id": unit_id,
        "eligible_credits_t": eligible_tonnes,
        "estimated_value": estimated_value,
        "price_per_t_co2": price_per_t_co2,
        "carbon_balance": bal
    }


# -------------------------------------------------------------
# FULL SUMMARY INCLUDING CREDITS (NEW)
# -------------------------------------------------------------
def carbon_full_summary(unit_id: str, price_per_t_co2: float = 6.0) -> Dict[str, Any]:
    """
    Returns unified carbon profile including:
      - emissions
      - sequestration
      - net carbon
      - sustainability score
      - suggestions
      - eligible carbon credits
      - estimated revenue
      - raw events
    """

    credits = calculate_carbon_credits(unit_id, price_per_t_co2)
    summary = carbon_summary(unit_id)  # your existing summary function

    return {
        "unit_id": unit_id,
        "credits": credits,
        "summary": summary["summary"],
        "sustainability_score": summary["sustainability_score"],
        "suggestions": summary["suggestions"],
        "events": summary["events"],
        "timestamp": _now()
    }
