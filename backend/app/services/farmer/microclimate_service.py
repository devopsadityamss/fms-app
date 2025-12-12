"""
Microclimate Generator Service (stub-ready)
-------------------------------------------

Produces simple microclimate snapshots for a production unit.
All values are heuristic stubs and intended to be replaced by model or sensor inputs later.

Record shape:
{
  "id": "<uuid>",
  "unit_id": "unit-12",
  "generated_at": "ISO",
  "location": {"lat": ..., "lon": ..., "elevation_m": ...},
  "inputs": {"canopy_percent": ..., "irrigation": True/False, "season": "dry/wet"},
  "microclimate": {
       "air_temperature_c": 29.4,
       "relative_humidity_pct": 62.3,
       "wind_speed_m_s": 1.8,
       "solar_rad_w_m2": 520,
       "evapotranspiration_index": 0.56,
       "dew_point_c": 21.0,
       "frost_risk": "low"
  }
}
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid
import math

# in-memory store
_micro_store: Dict[str, Dict[str, Any]] = {}

# optional integrations
try:
    from app.services.farmer import canopy_estimation_service as canopy_svc
except Exception:
    canopy_svc = None

try:
    from app.services.farmer import weather_service as weather_svc
except Exception:
    weather_svc = None


def _now() -> str:
    return datetime.utcnow().isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


# -------------------------------------------------------------
# Helper heuristics
# -------------------------------------------------------------
def _season_from_month(month: int) -> str:
    # very simple: assume northern hemisphere
    if month in (12, 1, 2):
        return "winter"
    if month in (3, 4, 5):
        return "spring"
    if month in (6, 7, 8):
        return "summer"
    return "autumn"


def _base_temperature_by_season(season: str) -> float:
    # stub baseline temperatures (°C)
    mapping = {"winter": 15.0, "spring": 22.0, "summer": 30.0, "autumn": 24.0}
    return mapping.get(season, 22.0)


def _elevation_temp_lapse(elevation_m: Optional[float]) -> float:
    # lapse rate ~0.0065 °C per meter
    if elevation_m is None:
        return 0.0
    return -0.0065 * float(elevation_m)


def _canopy_effects(canopy_pct: Optional[float]) -> Dict[str, float]:
    """
    Returns modifiers for microclimate depending on canopy cover:
     - higher canopy reduces temperature extremes, increases humidity, reduces wind, reduces solar radiation at ground
    """
    if canopy_pct is None:
        canopy_pct = 0.0
    c = max(0.0, min(100.0, float(canopy_pct)))
    frac = c / 100.0
    return {
        "temp_delta": -1.5 * frac,              # cooler under canopy
        "humidity_delta_pct": 8.0 * frac,       # more humid
        "wind_reduction_frac": 0.5 * frac,      # reduce wind up to 50%
        "solar_reduction_frac": 0.7 * frac      # reduce incident solar up to 70%
    }


def _estimate_evapotranspiration(temp_c: float, solar_w_m2: float, humidity_pct: float, wind_m_s: float) -> float:
    """
    Very coarse ET index between 0..1
    Higher temp & solar & wind increase ET; higher humidity lowers ET.
    """
    t_norm = max(0.0, min(1.0, (temp_c - 10) / 25.0))
    s_norm = max(0.0, min(1.0, solar_w_m2 / 1000.0))
    w_norm = max(0.0, min(1.0, wind_m_s / 5.0))
    h_factor = 1.0 - max(0.0, min(1.0, humidity_pct / 100.0))
    et = (0.5 * t_norm + 0.3 * s_norm + 0.2 * w_norm) * h_factor
    return round(float(et), 3)


def _dew_point(temp_c: float, rh_pct: float) -> float:
    # Approximate Magnus formula (simplified)
    a = 17.27
    b = 237.7
    alpha = (a * temp_c) / (b + temp_c) + math.log(max(rh_pct, 0.01) / 100.0)
    dp = (b * alpha) / (a - alpha)
    return round(float(dp), 2)


# -------------------------------------------------------------
# Main generator
# -------------------------------------------------------------
def generate_microclimate(
    unit_id: Optional[str] = None,
    location: Optional[Dict[str, Any]] = None,   # {"lat":..,"lon":..,"elevation_m":..}
    canopy_percent: Optional[float] = None,
    irrigation_on: Optional[bool] = False,
    use_weather_service: bool = True
) -> Dict[str, Any]:
    """
    Create a microclimate snapshot using heuristics and optional integrations.

    If weather_service exists and use_weather_service=True, try to fetch base weather for the location.
    """
    season = _season_from_month(datetime.utcnow().month)
    base_temp = _base_temperature_by_season(season)

    # elevation effect
    elev = location.get("elevation_m") if location else None
    base_temp += _elevation_temp_lapse(elev)

    # try to get actual weather snapshot if available
    weather_snapshot = None
    if weather_svc and use_weather_service and location and location.get("lat") and location.get("lon"):
        try:
            # expect weather_svc.current_weather(lat, lon) -> dict with keys: temp_c, rh_pct, wind_m_s, solar_w_m2
            weather_snapshot = weather_svc.current_weather(location["lat"], location["lon"])
        except Exception:
            weather_snapshot = None

    # canopy integration heuristics
    canopy_pct = canopy_percent
    if canopy_pct is None and canopy_svc and unit_id:
        # optionally try to get latest canopy estimate for unit
        try:
            lst = canopy_svc.list_canopy_records(unit_id)
            if lst.get("count", 0) > 0:
                # use most recent
                canopy_pct = lst["items"][0]["estimation"].get("canopy_percent")
        except Exception:
            canopy_pct = None

    canopy_mod = _canopy_effects(canopy_pct)

    # Compose microclimate: prefer weather snapshot if available
    if weather_snapshot:
        temp_c = float(weather_snapshot.get("temp_c", base_temp)) + canopy_mod["temp_delta"]
        rh_pct = float(weather_snapshot.get("rh_pct", 50.0)) + canopy_mod["humidity_delta_pct"]
        wind_m_s = float(weather_snapshot.get("wind_m_s", 1.5)) * (1.0 - canopy_mod["wind_reduction_frac"])
        solar_w_m2 = float(weather_snapshot.get("solar_w_m2", 600.0)) * (1.0 - canopy_mod["solar_reduction_frac"])
    else:
        # heuristic defaults
        temp_c = base_temp + canopy_mod["temp_delta"]
        # irrigation cools temp slightly and raises humidity
        temp_c += -0.8 if irrigation_on else 0.0
        rh_base = 60.0 if season == "summer" else 75.0 if season == "winter" else 65.0
        rh_pct = rh_base + canopy_mod["humidity_delta_pct"] + (8.0 if irrigation_on else 0.0)
        wind_m_s = 1.5 * (1.0 - canopy_mod["wind_reduction_frac"])
        solar_w_m2 = 650.0 * (1.0 - canopy_mod["solar_reduction_frac"])

    # clamp values into reasonable ranges
    temp_c = round(float(max(-30.0, min(50.0, temp_c))), 2)
    rh_pct = round(float(max(0.0, min(100.0, rh_pct))), 2)
    wind_m_s = round(float(max(0.0, min(20.0, wind_m_s))), 2)
    solar_w_m2 = round(float(max(0.0, min(2000.0, solar_w_m2))), 2)

    evap_idx = _estimate_evapotranspiration(temp_c, solar_w_m2, rh_pct, wind_m_s)
    dew_c = _dew_point(temp_c, rh_pct)

    # frost risk (very simplistic)
    frost_risk = "low"
    if temp_c <= 0:
        frost_risk = "high"
    elif temp_c <= 3:
        frost_risk = "medium"

    rec_id = _new_id()
    record = {
        "id": rec_id,
        "unit_id": unit_id,
        "generated_at": _now(),
        "location": location or {},
        "inputs": {
            "canopy_percent": canopy_pct,
            "irrigation_on": bool(irrigation_on),
            "season": season
        },
        "microclimate": {
            "air_temperature_c": temp_c,
            "relative_humidity_pct": rh_pct,
            "wind_speed_m_s": wind_m_s,
            "solar_rad_w_m2": solar_w_m2,
            "evapotranspiration_index": evap_idx,
            "dew_point_c": dew_c,
            "frost_risk": frost_risk
        }
    }

    _micro_store[rec_id] = record
    return record


# -------------------------------------------------------------
# Accessors
# -------------------------------------------------------------
def get_microclimate(rec_id: str) -> Dict[str, Any]:
    return _micro_store.get(rec_id, {"error": "not_found"})


def list_microclimates(unit_id: Optional[str] = None) -> Dict[str, Any]:
    items = list(_micro_store.values())
    if unit_id:
        items = [i for i in items if i.get("unit_id") == unit_id]
    # sort by generated_at desc
    items_sorted = sorted(items, key=lambda x: x.get("generated_at", ""), reverse=True)
    return {"count": len(items_sorted), "items": items_sorted}


def _clear_store():
    _micro_store.clear()
