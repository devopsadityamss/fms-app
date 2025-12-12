"""
Disaster Preparedness Index Service (stub-ready)
------------------------------------------------

This module computes a simple disaster preparedness score for a production unit.

Inputs (all optional):
 - rainfall_mm (recent or forecasted)
 - temperature_c
 - wind_speed_kmh
 - soil_moisture (0–1)
 - flood_zone (bool)
 - drought_zone (bool)
 - hazard_level (regional early-warning stub: low/med/high)
 - notes

Outputs:
 - preparedness_index: 0–1
 - component_risks
 - recommended_actions
 - stored advisory record (in-memory)

This logic is stub-based but structured so ML/risk models can replace it later.
"""

from typing import Dict, Any, Optional
from datetime import datetime
import uuid


# ---------------------------------------------------------------------
# In-memory store
# ---------------------------------------------------------------------
_disaster_store: Dict[str, Dict[str, Any]] = {}


def _now() -> str:
    return datetime.utcnow().isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------
# Risk sub-calculators (stub)
# ---------------------------------------------------------------------
def _rainfall_risk(rainfall_mm: Optional[float]) -> float:
    if rainfall_mm is None:
        return 0.3
    if rainfall_mm > 200:
        return 0.9
    if rainfall_mm > 120:
        return 0.7
    if rainfall_mm < 20:
        return 0.6  # drought risk
    return 0.4


def _temperature_risk(temp: Optional[float]) -> float:
    if temp is None:
        return 0.3
    if temp > 40:
        return 0.85
    if temp < 5:
        return 0.7
    return 0.4


def _wind_risk(wind: Optional[float]) -> float:
    if wind is None:
        return 0.3
    if wind > 80:
        return 0.9
    if wind > 40:
        return 0.6
    return 0.3


def _moisture_risk(moisture: Optional[float]) -> float:
    if moisture is None:
        return 0.4
    if moisture < 0.2:
        return 0.7  # too dry
    if moisture > 0.9:
        return 0.8  # flood-like saturation
    return 0.4


def _zone_risk(flood_zone: Optional[bool], drought_zone: Optional[bool]) -> float:
    if flood_zone:
        return 0.8
    if drought_zone:
        return 0.6
    return 0.3


def _hazard_risk(level: Optional[str]) -> float:
    if not level:
        return 0.4
    l = level.lower()
    if l == "high":
        return 0.8
    if l == "medium":
        return 0.6
    return 0.4


def _suggest_actions(components: Dict[str, float]) -> list:
    out = []

    if components["rainfall"] > 0.7:
        out.append("Prepare drainage; avoid waterlogging-sensitive crops.")
    if components["temperature"] > 0.7:
        out.append("Implement heat mitigation: mulching, shade nets, misting.")
    if components["wind"] > 0.7:
        out.append("Secure structures; avoid spraying; protect loose materials.")
    if components["moisture"] > 0.7:
        out.append("Watch for flood impact; elevate seed/material storage.")
    if components["zone"] > 0.6:
        out.append("Cluster-level mitigation planning recommended.")
    if components["hazard"] > 0.6:
        out.append("Monitor official warnings and prepare emergency response.")

    if not out:
        out.append("No major preparedness actions required at this time.")

    return out


# ---------------------------------------------------------------------
# MAIN ENTRY: compute disaster preparedness index
# ---------------------------------------------------------------------
def evaluate_disaster_preparedness(
    unit_id: Optional[str],
    rainfall_mm: Optional[float],
    temperature_c: Optional[float],
    wind_speed_kmh: Optional[float],
    soil_moisture: Optional[float],
    flood_zone: Optional[bool],
    drought_zone: Optional[bool],
    hazard_level: Optional[str],
    notes: Optional[str] = None,
) -> Dict[str, Any]:

    eval_id = _new_id()

    # Compute risk components
    comp = {
        "rainfall": _rainfall_risk(rainfall_mm),
        "temperature": _temperature_risk(temperature_c),
        "wind": _wind_risk(wind_speed_kmh),
        "moisture": _moisture_risk(soil_moisture),
        "zone": _zone_risk(flood_zone, drought_zone),
        "hazard": _hazard_risk(hazard_level),
    }

    # Composite index = avg risk
    preparedness_index = round(sum(comp.values()) / len(comp), 3)

    actions = _suggest_actions(comp)

    record = {
        "id": eval_id,
        "unit_id": unit_id,
        "created_at": _now(),
        "inputs": {
            "rainfall_mm": rainfall_mm,
            "temperature_c": temperature_c,
            "wind_speed_kmh": wind_speed_kmh,
            "soil_moisture": soil_moisture,
            "flood_zone": flood_zone,
            "drought_zone": drought_zone,
            "hazard_level": hazard_level,
        },
        "risk_components": comp,
        "preparedness_index": preparedness_index,
        "recommended_actions": actions,
        "notes": notes,
    }

    _disaster_store[eval_id] = record
    return record


def get_preparedness_record(eval_id: str) -> Optional[Dict[str, Any]]:
    return _disaster_store.get(eval_id)


def list_preparedness(unit_id: Optional[str] = None) -> Dict[str, Any]:
    items = list(_disaster_store.values())
    if unit_id:
        items = [i for i in items if i.get("unit_id") == unit_id]
    return {"count": len(items), "items": items}


def _clear_store():
    _disaster_store.clear()
