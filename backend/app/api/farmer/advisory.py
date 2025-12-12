# backend/app/api/farmer/advisory.py

from fastapi import APIRouter, Body
from typing import Dict, Any

from app.services.farmer.advisory_service import (
    # Legacy functions (KEEP)
    get_general_advice,
    get_stage_based_advice,
    get_weather_linked_advice,
    get_all_advisory,

    # Advanced advisory engine (NEW)
    smart_advice,
    combined_advice,
    stage_practices,
    fertilizer_recommendation,
    irrigation_suggestion,
    pest_triage,
    scouting_checklist,
    list_advisor_plugins,
    run_plugin,
)

from app.services.farmer.weather_service import get_current_weather

router = APIRouter()

# ---------------------------------------------------------
# ORIGINAL LEGACY ENDPOINTS — DO NOT TOUCH
# ---------------------------------------------------------

@router.get("/advisory/{unit_id}")
def advisory_overview(unit_id: int, stage: str):
    """
    Legacy endpoint.
    Returns:
    - general advice
    - stage-based advice
    - weather-based advice
    """
    weather = get_current_weather(unit_id)

    return get_all_advisory(
        unit_id=unit_id,
        stage_name=stage,
        weather=weather
    )


@router.get("/advisory/{unit_id}/general")
def advisory_general(unit_id: int):
    return get_general_advice(unit_id)


@router.get("/advisory/{unit_id}/stage")
def advisory_stage(unit_id: int, stage: str):
    return get_stage_based_advice(unit_id, stage)


@router.get("/advisory/{unit_id}/weather")
def advisory_weather(unit_id: int):
    weather = get_current_weather(unit_id)
    return get_weather_linked_advice(unit_id, weather)


# ---------------------------------------------------------
# NEW ADVANCED ADVISORY ENDPOINTS — OPTIONAL, MIGRATION PATH
# ---------------------------------------------------------

@router.post("/advisory/{unit_id}/smart")
def advisory_smart(unit_id: int, payload: Dict[str, Any] = Body(...)):
    """
    New recommended unified advisory endpoint.
    Accepts a payload:
      {
        crop, stage, area_ha, expected_yield_t_per_ha,
        soil_texture, soil_moisture_fraction,
        forecast_rain_mm_next_48h,
        symptoms_text,
        soil_nutrient: {N, P2O5, K2O}
      }
    Returns: combined advice (stage, fertilizer, irrigation, pest triage, plugins)
    """
    payload["unit_id"] = unit_id
    return smart_advice(payload)


@router.get("/advisory/{unit_id}/stage-practices")
def advisory_stage_practices(unit_id: int, crop: str, stage: str):
    return stage_practices(crop, stage)


@router.post("/advisory/{unit_id}/fertilizer")
def advisory_fertilizer(unit_id: int, payload: Dict[str, Any] = Body(...)):
    """
    Expected payload:
    {
      crop,
      area_ha,
      expected_yield_t_per_ha,
      soil_nutrient: {N, P2O5, K2O},
      target_recovery_pct
    }
    """
    return fertilizer_recommendation(
        payload.get("crop"),
        payload.get("area_ha"),
        payload.get("expected_yield_t_per_ha"),
        payload.get("soil_nutrient"),
        payload.get("target_recovery_pct", 0.5),
    )


@router.post("/advisory/{unit_id}/irrigation")
def advisory_irrigation(unit_id: int, payload: Dict[str, Any] = Body(...)):
    return irrigation_suggestion(
        soil_texture=payload.get("soil_texture", "medium"),
        current_soil_moisture_fraction=payload.get("soil_moisture_fraction"),
        crop_stage=payload.get("stage"),
        forecast_rain_mm_next_48h=payload.get("forecast_rain"),
    )


@router.post("/advisory/{unit_id}/pest-triage")
def advisory_pest_triage(unit_id: int, payload: Dict[str, Any] = Body(...)):
    return pest_triage(payload.get("symptoms_text", ""))


@router.get("/advisory/{unit_id}/scouting")
def advisory_scouting(unit_id: int, crop: str, stage: str):
    return scouting_checklist(crop, stage)


# ---------------------------------------------------------
# PLUGINS API (NEW)
# ---------------------------------------------------------

@router.get("/advisory-plugins")
def advisory_plugins():
    return {"plugins": list_advisor_plugins()}


@router.post("/advisory-plugin/{name}")
def advisory_plugin_run(name: str, payload: Dict[str, Any] = Body(...)):
    """
    Execute an advisory plugin.
    """
    return run_plugin(name, payload)
