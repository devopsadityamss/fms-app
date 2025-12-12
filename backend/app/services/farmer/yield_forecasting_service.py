# backend/app/services/farmer/yield_forecasting_service.py

from datetime import datetime
from typing import Dict, Any, Optional
import math

# Reuse farmer's internal stores
from app.services.farmer.unit_service import _unit_store
from app.services.farmer.stage_service import _stage_template_store
from app.services.farmer.input_forecasting_service import forecast_inputs_for_unit


"""
Yield Forecaster Logic (Simple ML-inspired Heuristic):

Yield is influenced by:
 1. Area
 2. Seed rate
 3. Fertilizer adequacy (NPK)
 4. Weather score (rainfall + temperature suitability)
 5. Soil quality score (optional input)
 6. Stage completion & delays
 7. Farming practice quality (if available)

Output:
  - base_yield_estimate
  - adjusted_yield_estimate
  - optimistic & pessimistic bounds
  - confidence score
  - explainability
"""


# -----------------------------------------------------------
# Helper functions
# -----------------------------------------------------------
def _safe_float(v, d=0.0):
    try:
        return float(v)
    except Exception:
        return d


def _compute_weather_score(weather: Optional[Dict[str, Any]]) -> float:
    """
    weather = {
        "rain_mm": <float>,
        "temp_c": <float>,
        "humidity": <float>
    }
    Output: score 0–100
    """
    if not weather:
        return 70.0  # neutral

    rain = _safe_float(weather.get("rain_mm"), 20)
    temp = _safe_float(weather.get("temp_c"), 30)

    # Rainfall suitability heuristics
    if rain < 5:
        rain_score = 50
    elif rain < 20:
        rain_score = 70
    elif rain < 60:
        rain_score = 85
    else:
        rain_score = 60

    # Temperature suitability heuristics
    if temp < 18:
        temp_score = 60
    elif 18 <= temp <= 32:
        temp_score = 85
    else:
        temp_score = 50

    return (rain_score * 0.6) + (temp_score * 0.4)


def _compute_fertilizer_score(unit_inputs: Dict[str, Any]) -> float:
    fert = unit_inputs.get("total_inputs", {}).get("fertilizer", {})

    # Expected nutrients per acre (heuristic baseline)
    EXPECTED = {
        "N": 50,   # kg/acre
        "P": 25,   # kg/acre
        "K": 25    # kg/acre
    }

    score = 0
    max_score = 0

    for nutrient, recommended in EXPECTED.items():
        applied = fert.get(nutrient, 0)
        # Score 100 if applied >= recommended
        max_score += 100
        if applied >= recommended:
            score += 100
        else:
            score += (applied / recommended) * 100

    if max_score == 0:
        return 70

    return score / 3


def _compute_seed_rate_score(unit_inputs: Dict[str, Any], area: float) -> float:
    seed_kg = unit_inputs.get("total_inputs", {}).get("seed_kg", 0)
    if area <= 0:
        return 70
    seed_rate = seed_kg / area

    # Ideal seed rate ranges (kg per acre)
    if seed_rate <= 0:
        return 40
    if 8 <= seed_rate <= 20:
        return 90
    if 4 <= seed_rate < 8:
        return 75
    return 60


def _compute_soil_score(soil_quality: Optional[Dict[str, Any]]) -> float:
    """
    soil_quality = {
        "ph": ...,
        "organic_carbon": ...,
        "ec": ...
    }
    """
    if not soil_quality:
        return 70  # neutral baseline

    ph = _safe_float(soil_quality.get("ph"), 7)
    oc = _safe_float(soil_quality.get("organic_carbon"), 0.5)

    # PH scoring
    if 6.0 <= ph <= 7.5:
        ph_score = 90
    else:
        ph_score = 65

    # Organic carbon scoring
    if oc > 0.75:
        oc_score = 90
    elif oc > 0.5:
        oc_score = 70
    else:
        oc_score = 55

    return (ph_score * 0.6) + (oc_score * 0.4)


def _compute_stage_progress_score(unit: Dict[str, Any]) -> float:
    """
    If unit contains progress tracker later, we integrate.
    For now assume neutral score.
    """
    return 75.0


# -----------------------------------------------------------
# MAIN YIELD FORECAST FUNCTION
# -----------------------------------------------------------
def forecast_yield_for_unit(
    unit_id: str,
    crop_price_per_quintal: Optional[float] = None,
    weather: Optional[Dict[str, Any]] = None,
    soil_quality: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:

    unit = _unit_store.get(unit_id)
    if not unit:
        return {"status": "unit_not_found", "unit_id": unit_id}

    crop = unit.get("crop")
    area = _safe_float(unit.get("area"), 1.0)

    # 1. Input forecast (reuse previous intelligence)
    inputs = forecast_inputs_for_unit(unit_id)

    # 2. Compute component scores
    fertilizer_score = _compute_fertilizer_score(inputs)
    seed_score = _compute_seed_rate_score(inputs, area)
    weather_score = _compute_weather_score(weather)
    soil_score = _compute_soil_score(soil_quality)
    stage_score = _compute_stage_progress_score(unit)

    # 3. Weighted yield strength score
    yield_strength = (
        fertilizer_score * 0.35 +
        seed_score * 0.15 +
        weather_score * 0.25 +
        soil_score * 0.15 +
        stage_score * 0.10
    ) / 100

    # 4. Base yield potential per acre (VERY crop-dependent)
    # For now we use generic values (can refine later)
    BASE_YIELD = {
        "wheat": 18,   # quintals per acre
        "rice": 20,
        "maize": 25,
        "cotton": 10,
        "soybean": 12
    }
    base_yield_per_acre = BASE_YIELD.get(str(crop).lower(), 15)

    # 5. Compute actual yield forecast
    expected_yield_quintal = base_yield_per_acre * area * yield_strength

    # 6. Generate optimistic/pessimistic range
    optimistic = expected_yield_quintal * 1.15
    pessimistic = expected_yield_quintal * 0.85

    # 7. Revenue estimate
    revenue_est = None
    if crop_price_per_quintal:
        revenue_est = round(expected_yield_quintal * crop_price_per_quintal, 2)

    # 8. Confidence score
    # Based on how balanced the scores are
    score_std = math.sqrt(
        ((fertilizer_score - 70) ** 2 +
         (seed_score - 70) ** 2 +
         (weather_score - 70) ** 2 +
         (soil_score - 70) ** 2 +
         (stage_score - 70) ** 2) / 5
    )
    confidence = max(40, 100 - score_std)

    return {
        "unit_id": unit_id,
        "crop": crop,
        "area_acre": area,
        "expected_yield_quintal": round(expected_yield_quintal, 2),
        "optimistic_yield_quintal": round(optimistic, 2),
        "pessimistic_yield_quintal": round(pessimistic, 2),
        "yield_strength_factor": round(yield_strength, 3),
        "confidence_score": round(confidence, 2),
        "component_scores": {
            "fertilizer_score": round(fertilizer_score, 2),
            "seed_score": round(seed_score, 2),
            "weather_score": round(weather_score, 2),
            "soil_score": round(soil_score, 2),
            "stage_score": round(stage_score, 2),
        },
        "revenue_estimate": revenue_est,
        "explainability": {
            "weather_used": weather,
            "soil_used": soil_quality,
            "input_summary": inputs["total_inputs"]
        },
        "generated_at": datetime.utcnow().isoformat()
    }
