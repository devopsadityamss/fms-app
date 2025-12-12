"""
Weather Impact Analyzer (stub-ready)
------------------------------------

Evaluates weather effects on crop conditions and farmer operations.

Inputs:
 - temperature_c
 - humidity
 - rainfall_mm
 - wind_speed_kmh
 - heatwave_warning (bool)
 - coldwave_warning (bool)
 - notes

Outputs:
 - impact_score (0–1)
 - categorized impacts (heat, humidity, rainfall, wind)
 - operational suggestions
 - store each evaluation in-memory

Replace stub with real weather service + crop models later.
"""

from typing import Dict, Any, Optional
from datetime import datetime
import uuid


_weather_store: Dict[str, Dict[str, Any]] = {}


def _new_id() -> str:
    return str(uuid.uuid4())


def _now() -> str:
    return datetime.utcnow().isoformat()


# ---------------------------------------------------------------------
# Stubbed impact models
# ---------------------------------------------------------------------
def _heat_impact(temp: Optional[float]) -> float:
    if temp is None:
        return 0.3
    if temp > 40:
        return 0.85
    if temp > 35:
        return 0.65
    if temp < 15:
        return 0.2
    return 0.4


def _humidity_impact(h: Optional[float]) -> float:
    if h is None:
        return 0.3
    if h > 80:
        return 0.7  # disease risk
    if h < 20:
        return 0.6  # desiccation risk
    return 0.4


def _rainfall_impact(rain: Optional[float]) -> float:
    if rain is None:
        return 0.3
    if rain > 150:
        return 0.9  # flood risk
    if rain > 80:
        return 0.6  # waterlogging concern
    if rain < 5:
        return 0.5  # drought risk
    return 0.4


def _wind_impact(wind: Optional[float]) -> float:
    if wind is None:
        return 0.3
    if wind > 70:
        return 0.9
    if wind > 40:
        return 0.6
    return 0.3


def _event_impact(heatwave: Optional[bool], coldwave: Optional[bool]) -> float:
    if heatwave:
        return 0.8
    if coldwave:
        return 0.7
    return 0.3


def _suggest_actions(components: Dict[str, float]) -> list:
    out = []

    if components["heat"] > 0.6:
        out.append("Use shading nets or misting to reduce heat stress.")

    if components["humidity"] > 0.6:
        out.append("Monitor for fungal diseases; consider preventive spray.")

    if components["rainfall"] > 0.7:
        out.append("Ensure drainage; avoid field operations on wet soil.")

    if components["wind"] > 0.6:
        out.append("Secure equipment; avoid pesticide spraying under high wind.")

    if components["events"] > 0.6:
        out.append("Follow local advisories for severe weather events.")

    if not out:
        out.append("Weather conditions stable; no special action required.")

    return out


# ---------------------------------------------------------------------
# MAIN ENTRY
# ---------------------------------------------------------------------
def evaluate_weather_impact(
    unit_id: Optional[str],
    temperature_c: Optional[float],
    humidity: Optional[float],
    rainfall_mm: Optional[float],
    wind_speed_kmh: Optional[float],
    heatwave_warning: Optional[bool],
    coldwave_warning: Optional[bool],
    notes: Optional[str] = None
) -> Dict[str, Any]:

    eval_id = _new_id()

    components = {
        "heat": _heat_impact(temperature_c),
        "humidity": _humidity_impact(humidity),
        "rainfall": _rainfall_impact(rainfall_mm),
        "wind": _wind_impact(wind_speed_kmh),
        "events": _event_impact(heatwave_warning, coldwave_warning),
    }

    # Composite impact
    impact_score = round(sum(components.values()) / len(components), 3)

    suggestions = _suggest_actions(components)

    record = {
        "id": eval_id,
        "unit_id": unit_id,
        "created_at": _now(),
        "inputs": {
            "temperature_c": temperature_c,
            "humidity": humidity,
            "rainfall_mm": rainfall_mm,
            "wind_speed_kmh": wind_speed_kmh,
            "heatwave_warning": heatwave_warning,
            "coldwave_warning": coldwave_warning,
        },
        "components": components,
        "impact_score": impact_score,
        "suggestions": suggestions,
        "notes": notes,
    }

    _weather_store[eval_id] = record
    return record


def get_weather_impact(eval_id: str) -> Optional[Dict[str, Any]]:
    return _weather_store.get(eval_id)


def list_weather_impacts(unit_id: Optional[str] = None) -> Dict[str, Any]:
    items = list(_weather_store.values())
    if unit_id:
        items = [i for i in items if i.get("unit_id") == unit_id]
    return {"count": len(items), "items": items}


def _clear_store():
    _weather_store.clear()
