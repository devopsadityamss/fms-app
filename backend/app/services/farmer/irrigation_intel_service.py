# backend/app/services/farmer/irrigation_intel_service.py

"""
Irrigation Intelligence Engine (in-memory)

Features:
 - Estimate crop evapotranspiration (ETc)
 - Use soil texture + crop stage + irrigation system to compute water requirement
 - Incorporate rainfall forecast and soil moisture
 - Generate irrigation recommendation (mm & liters)
 - Compute irrigation duration based on system flow rate
 - Provide weekly irrigation schedule
 - Detect water stress (deficit or excess)
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# -----------------------------
# Internal helpers
# -----------------------------
TEXTURE_FIELD_CAPACITY = {
    "sandy": 0.07,
    "loamy": 0.18,
    "clay": 0.30
}

CROP_COEFFICIENTS = {
    "paddy": {"initial": 1.1, "mid": 1.2, "late": 0.9},
    "wheat": {"initial": 0.7, "mid": 1.15, "late": 0.6},
    "maize": {"initial": 0.7, "mid": 1.15, "late": 0.8},
    "cotton": {"initial": 0.4, "mid": 1.15, "late": 0.8}
}

def _now():
    return datetime.utcnow().isoformat()


# -----------------------------
# ET calculation
# -----------------------------
def estimate_etc(et0: float, crop: str, stage: str) -> float:
    """
    ETc = ET0 * Kc (crop coefficient)
    """
    crop = crop.lower()
    stage = stage.lower()

    kc_map = CROP_COEFFICIENTS.get(crop)

    if not kc_map:
        # fallback coefficients
        kc_map = {"initial": 0.7, "mid": 1.0, "late": 0.7}

    kc = kc_map.get(stage, kc_map["mid"])
    return round(et0 * kc, 2)


# -----------------------------
# Soil moisture balance
# -----------------------------
def compute_water_requirement(
    etc: float,
    rainfall_mm: float,
    soil_moisture: Optional[float],
    texture: str
) -> Dict[str, Any]:

    field_capacity = TEXTURE_FIELD_CAPACITY.get(texture.lower(), 0.18)

    # Net water needed before SOC corrections
    net_ET = max(etc - rainfall_mm, 0)

    # if soil moisture sensor available
    moisture_adj = 0
    if soil_moisture is not None:
        # soil_moisture is % volumetric, normalize
        field_capacity_pct = field_capacity * 100
        if soil_moisture > field_capacity_pct:
            moisture_adj = -0.2 * net_ET  # reduce advice
        elif soil_moisture < (0.5 * field_capacity_pct):
            moisture_adj = +0.2 * net_ET  # increase advice

    final_mm = max(net_ET + moisture_adj, 0)
    return {
        "net_et_mm": net_ET,
        "final_mm": round(final_mm, 2),
        "soil_adjustment_mm": round(moisture_adj, 2),
        "field_capacity": field_capacity
    }


# -----------------------------
# Convert water depth to volume
# -----------------------------
def mm_to_liters_per_acre(mm: float) -> float:
    """
    1 mm water = 4046.86 liters per acre.
    """
    return round(mm * 4046.86, 2)


def compute_duration_liters(flow_lph: float, liters_required: float) -> float:
    if flow_lph <= 0:
        return 0
    hours = liters_required / flow_lph
    return round(hours, 2)


# -----------------------------
# Weekly Schedule
# -----------------------------
def weekly_schedule(final_mm_today: float) -> Dict[str, Any]:
    """
    Creates a simple weekly distribution:
    - Mid-season crops get more frequent irrigation
    - Initial & late get less
    """

    schedule = []
    base = final_mm_today

    # Distribute mm across 7 days
    for i in range(7):
        day_mm = round(base * (0.8 if i in [1,3,5] else 0.5), 2)
        schedule.append({
            "day": i + 1,
            "recommended_mm": day_mm,
            "recommended_liters_per_acre": mm_to_liters_per_acre(day_mm)
        })

    return {"days": schedule}


# -----------------------------
# Water Stress Analysis
# -----------------------------
def detect_water_stress(etc: float, final_mm: float, soil_moisture: Optional[float]) -> Optional[str]:
    if soil_moisture is not None and soil_moisture < 30:
        return "high_water_deficit"
    if final_mm > etc * 1.5:
        return "overwatering_risk"
    if final_mm < etc * 0.5:
        return "underwatering_risk"
    return None


# -----------------------------
# Full irrigation intelligence summary
# -----------------------------
def irrigation_intelligence(
    unit_id: str,
    crop: str,
    stage: str,
    et0: float,
    rainfall_mm: float,
    texture: str,
    soil_moisture: Optional[float],
    irrigation_flow_lph: Optional[float]
):
    """
    Returns:
     - ETc
     - Daily requirement (mm / liters)
     - Irrigation duration
     - Weekly schedule
     - Water stress status
    """

    etc = estimate_etc(et0, crop, stage)

    req = compute_water_requirement(
        etc=etc,
        rainfall_mm=rainfall_mm,
        soil_moisture=soil_moisture,
        texture=texture
    )

    liters = mm_to_liters_per_acre(req["final_mm"])

    duration_hours = None
    if irrigation_flow_lph:
        duration_hours = compute_duration_liters(irrigation_flow_lph, liters)

    stress = detect_water_stress(etc, req["final_mm"], soil_moisture)

    return {
        "unit_id": unit_id,
        "crop": crop,
        "stage": stage,
        "etc_mm": etc,
        "soil_adjustments": req,
        "liters_per_acre": liters,
        "irrigation_duration_hours": duration_hours,
        "weekly_schedule": weekly_schedule(req["final_mm"]),
        "water_stress": stress,
        "timestamp": _now()
    }
