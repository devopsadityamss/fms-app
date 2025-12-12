# backend/app/services/farmer/water_forecast_service.py

"""
Feature 319 — Water Demand Forecasting (7-day prediction)

Inputs:
 - unit crop, stage, area
 - ET0 forecast (list of {date, et0_mm})
 - Rainfall forecast (mm)
 - Irrigation method efficiency
 - Soil moisture reserve (optional)
Outputs:
 - daily predicted net water need
 - gross water requirement (liters)
 - cumulative 7-day load
"""

from datetime import datetime, date
from typing import Dict, List, Any, Optional
import math

try:
    from app.services.farmer.irrigation_service import METHOD_EFFICIENCY, Kc_TABLE
except:
    METHOD_EFFICIENCY = {"flood": 0.5, "sprinkler": 0.75, "drip": 0.9}
    Kc_TABLE = {"generic": {"initial": 0.7, "mid": 1.0, "late": 0.8}}

try:
    from app.services.farmer.unit_service import _unit_store
except:
    _unit_store = {}

def _area_to_m2(acres: float) -> float:
    return float(acres) * 4046.85642

def _kc(crop: str, stage: str) -> float:
    c = crop.lower()
    st = stage.lower()
    if c in Kc_TABLE and st in Kc_TABLE[c]:
        return Kc_TABLE[c][st]
    if "generic" in Kc_TABLE and st in Kc_TABLE["generic"]:
        return Kc_TABLE["generic"][st]
    return 1.0

def predict_water_demand(
    unit_id: str,
    stage: str,
    et0_forecast: List[Dict[str, Any]],
    rainfall_forecast: List[Dict[str, Any]],
    method: str = "flood",
    soil_moisture_pct: Optional[float] = None
) -> Dict[str, Any]:

    unit = _unit_store.get(str(unit_id))
    if not unit:
        return {"error": "unit_not_found"}

    crop = unit.get("crop")
    area = float(unit.get("area", 1.0))
    area_m2 = _area_to_m2(area)

    kc = _kc(crop, stage)
    eff = METHOD_EFFICIENCY.get(method, 0.7)

    out = []
    cumulative_liters = 0.0

    # Optional soil moisture bonus: reduce first day need
    soil_correction_mm = 0
    if soil_moisture_pct is not None:
        if soil_moisture_pct > 60:
            soil_correction_mm = 3
        elif soil_moisture_pct > 40:
            soil_correction_mm = 1

    for i in range(min(len(et0_forecast), 7)):

        et0 = float(et0_forecast[i].get("et0_mm", 4))
        rain = float(rainfall_forecast[i].get("rain_mm", 0))

        etc = et0 * kc
        net = max(0, etc - rain)

        # First-day soil correction
        if i == 0:
            net = max(0, net - soil_correction_mm)

        gross_mm = net / eff
        liters = gross_mm * area_m2

        cumulative_liters += liters

        out.append({
            "day_index": i,
            "date": et0_forecast[i].get("date"),
            "et0_mm": round(et0, 2),
            "rain_mm": round(rain, 2),
            "kc": round(kc, 2),
            "net_mm": round(net, 2),
            "gross_mm": round(gross_mm, 2),
            "liters": round(liters, 2)
        })

    return {
        "unit_id": unit_id,
        "crop": crop,
        "stage": stage,
        "method": method,
        "forecast_days": out,
        "total_7_day_liters": round(cumulative_liters, 2),
        "generated_at": datetime.utcnow().isoformat()
    }
