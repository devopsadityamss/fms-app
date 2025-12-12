# backend/app/services/farmer/advisory_service.py

"""
Unified Advisory Service (merged, Option C)

This file MERGES:
 - Your original lightweight advisory functions (kept verbatim and unchanged for backward compatibility):
   - get_general_advice
   - get_stage_based_advice
   - get_weather_linked_advice
   - get_all_advisory

 - The advanced advisory engine (Feature #293) added below:
   - plugin registry (register_advisor_plugin, list_advisor_plugins, run_plugin)
   - stage_practices
   - fertilizer_recommendation
   - irrigation_suggestion
   - pest_triage
   - scouting_checklist
   - combined_advice (the unified smart advisor)
   - helpers and analytics

Strategy (Option C):
 - Keep existing functions exactly as they were so nothing breaks.
 - Add advanced functions and a new `smart_advice` / `combined_advice` entrypoint which your frontend can migrate to.
 - No existing function signatures are changed.
"""

# -----------------------
# ORIGINAL (LEGACY) ADVISORY BLOCK — kept verbatim
# -----------------------
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from threading import Lock
import math
import uuid

# NOTE:
# This file provides mock advisory logic for farmer guidance.
# The real implementation will combine:
# - crop type
# - stage of growth
# - upcoming tasks
# - weather forecast
# - soil & sensor inputs
# - historical yield patterns
# For now: mock responses to support UI + API development.


def get_general_advice(unit_id: int) -> List[Dict[str, Any]]:
    """
    Returns general crop advisory suggestions.
    These are static/mock but will later be generated dynamically.
    """

    return [
        {
            "id": 1,
            "title": "Irrigation Recommendation",
            "description": "Based on current weather, maintain moderate irrigation. Avoid over-watering.",
            "type": "irrigation",
            "priority": "medium",
            "timestamp": datetime.utcnow(),
        },
        {
            "id": 2,
            "title": "Fertilizer Guidance",
            "description": "Apply nitrogen-rich fertilizer if crop is in early vegetative stage.",
            "type": "fertilizer",
            "priority": "high",
            "timestamp": datetime.utcnow(),
        },
        {
            "id": 3,
            "title": "Pest Prevention",
            "description": "Monitor for signs of leaf miner infestation. Use organic repellent if needed.",
            "type": "pest",
            "priority": "low",
            "timestamp": datetime.utcnow(),
        },
    ]


def get_stage_based_advice(unit_id: int, stage_name: str) -> List[Dict[str, Any]]:
    """
    Returns advisory suggestions specific to the crop stage.
    """

    mock_stage_advice = {
        "sowing": [
            {
                "title": "Seed Treatment",
                "description": "Treat seeds with fungicide to minimize early-stage disease risks.",
                "priority": "high",
            }
        ],
        "vegetative": [
            {
                "title": "Nutrient Application",
                "description": "Apply nitrogen fertilizer to support leaf growth.",
                "priority": "medium",
            },
            {
                "title": "Weed Control",
                "description": "Inspect field and remove weeds manually or with safe herbicide.",
                "priority": "medium",
            }
        ],
        "flowering": [
            {
                "title": "Potassium Supplement",
                "description": "Apply potassium to improve flowering and fruit formation.",
                "priority": "high",
            }
        ],
        "harvest": [
            {
                "title": "Harvest Preparation",
                "description": "Ensure tools, storage bags, and labor are ready.",
                "priority": "medium",
            }
        ],
    }

    return [
        {
            "stage": stage_name,
            "timestamp": datetime.utcnow(),
            **advice,
        }
        for advice in mock_stage_advice.get(stage_name.lower(), [])
    ]


def get_weather_linked_advice(unit_id: int, weather: Dict[str, Any]):
    """
    Generates simple weather-linked advice based on mock weather data.
    """

    temperature = weather.get("temperature", 28)
    rainfall = weather.get("rainfall_mm", 0)

    advice_list = []

    if temperature > 33:
        advice_list.append(
            {
                "title": "High Temperature Alert",
                "description": "Due to heat, irrigate during early morning or late evening.",
                "priority": "high",
            }
        )

    if rainfall > 10:
        advice_list.append(
            {
                "title": "Rain Alert",
                "description": "Heavy rainfall expected — avoid fertilizer application.",
                "priority": "high",
            }
        )

    return {
        "unit_id": unit_id,
        "timestamp": datetime.utcnow(),
        "weather_advice": advice_list,
    }


def get_all_advisory(unit_id: int, stage_name: str, weather: Dict[str, Any]) -> Dict[str, Any]:
    """
    Combines general + stage-based + weather-based advisory.
    This will be the most used endpoint for farmer insights.
    """

    return {
        "unit_id": unit_id,
        "timestamp": datetime.utcnow(),
        "general": get_general_advice(unit_id),
        "stage_based": get_stage_based_advice(unit_id, stage_name),
        "weather_based": get_weather_linked_advice(unit_id, weather),
    }

# -----------------------
# END LEGACY BLOCK
# -----------------------

# -----------------------
# ADVANCED ADVISORY ENGINE (Feature #293) — added below
# -----------------------

_lock = Lock()

# In-memory plugin registry: name -> callable(payload)->dict
_plugin_registry: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}

# Simple crop stage practice rules (example crops: rice, wheat, maize, cotton)
_STAGE_PRACTICES = {
    "rice": {
        "land_preparation": ["Plough field to remove weeds", "Level field for uniform water", "Apply recommended basal fertilizer"],
        "sowing": ["Use certified seeds", "Maintain seedbed moisture", "Seed treatment for common fungi"],
        "tillering": ["Monitor for stem borer", "Apply split N fertilizer as per schedule"],
        "panicle_initiation": ["Apply K and P if deficient", "Monitor for blast disease"],
        "grain_filling": ["Ensure adequate irrigation", "Avoid late N application"],
        "harvest": ["Drain field 7–10 days before harvest", "Use clean harvesting tools"]
    },
    "wheat": {
        "land_preparation": ["Prepare firm seedbed", "Apply basal phosphate and potash as recommended"],
        "sowing": ["Sow at recommended seed rate", "Seed treatment for rust and smut"],
        "tillering": ["First split N application", "Monitor for aphids"],
        "heading": ["Ensure potassium supply", "Irrigate during booting if dry"],
        "grain_filling": ["Avoid late nitrogen", "Monitor moisture for timely harvest"],
        "harvest": ["Timely combine harvesting to reduce losses"]
    },
    "maize": {
        "land_preparation": ["Deep ploughing if soil compacted", "Fertilize with basal NPK"],
        "sowing": ["Row spacing as per variety", "Ensure good seed-to-soil contact"],
        "vegetative": ["Side-dress N", "Weed management"],
        "flowering": ["Avoid water stress during silking", "Pest monitoring"],
        "grain_fill": ["Ensure moisture; avoid late stress"],
        "harvest": ["Dry properly to 12-14% moisture"]
    }
}

# Typical nutrient requirement per crop (kg nutrient per ton of expected yield) - very simplified
_CROP_NUTRIENT_FACTORS = {
    "rice": {"N": 20, "P2O5": 10, "K2O": 15},    # kg nutrient per ton yield
    "wheat": {"N": 18, "P2O5": 8, "K2O": 12},
    "maize": {"N": 22, "P2O5": 9, "K2O": 14},
    "cotton": {"N": 25, "P2O5": 10, "K2O": 20}
}

# Soil fertility default (kg/ha available nutrients) - placeholders
_SOIL_DEFAULTS = {"N": 50, "P2O5": 20, "K2O": 80}

# Irrigation thresholds (soil moisture fraction of field capacity) — illustrative
_IRRIGATION_THRESHOLD = {
    "light": 0.25,   # sandy soils - trigger when moisture < 25% FC
    "medium": 0.35,  # loam
    "heavy": 0.45    # clay
}

def _now_iso():
    return datetime.utcnow().isoformat()

def _newid(prefix="id"):
    return f"{prefix}_{uuid.uuid4()}"

# ---------------------------
# Plugin registry
# ---------------------------
def register_advisor_plugin(name: str, fn: Callable[[Dict[str, Any]], Dict[str, Any]]) -> Dict[str, Any]:
    """
    Register a plugin function that takes a payload dict and returns a dict result.
    """
    with _lock:
        _plugin_registry[name] = fn
    return {"status": "registered", "name": name}

def list_advisor_plugins() -> List[str]:
    with _lock:
        return list(_plugin_registry.keys())

def run_plugin(name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    fn = _plugin_registry.get(name)
    if not fn:
        return {"error": "plugin_not_found"}
    try:
        return fn(payload)
    except Exception as e:
        return {"error": "plugin_error", "message": str(e)}

# ---------------------------
# Stage-based recommendations
# ---------------------------
def stage_practices(crop: str, stage: str) -> Dict[str, Any]:
    crop = (crop or "").lower()
    stage = (stage or "").lower()
    practices = _STAGE_PRACTICES.get(crop, {})
    if not practices:
        return {"crop": crop, "stage": stage, "practices": [], "note": "no_rules_for_crop"}
    return {"crop": crop, "stage": stage, "practices": practices.get(stage, []), "generated_at": _now_iso()}

# ---------------------------
# Fertilizer calculation
# ---------------------------
def fertilizer_recommendation(
    crop: str,
    area_ha: float,
    expected_yield_t_per_ha: float,
    soil_nutrient: Optional[Dict[str, float]] = None,
    target_recovery_pct: float = 0.5
) -> Dict[str, Any]:
    """
    Very simple recommendation:
      - total_nutrient_need = factor_per_ton * expected_yield_t_per_ha * area_ha
      - subtract available soil nutrients (soil_nutrient defaults)
      - apply recovery factor (target_recovery_pct) to compute fertilizer amounts required
    Returns nutrient amounts (kg) and a suggested split (basal/split) as a simple plan.
    """
    crop = (crop or "").lower()
    soil = soil_nutrient or _SOIL_DEFAULTS
    factors = _CROP_NUTRIENT_FACTORS.get(crop)
    if not factors:
        return {"error": "no_crop_nutrient_data", "crop": crop}

    # total nutrient removal by crop (kg)
    total = {}
    for nut, per_t in factors.items():
        need = per_t * expected_yield_t_per_ha * area_ha
        avail = float(soil.get(nut, 0))
        deficit = max(0.0, need - avail)
        # account for recovery (fertilizer inefficiencies)
        required_fertilizer = round(deficit / max(0.01, target_recovery_pct), 2)
        total[nut] = {"need_kg": round(need,2), "soil_available_kg": round(avail,2), "deficit_kg": round(deficit,2), "fertilizer_required_kg": required_fertilizer}
    # simple split suggestion: N split 1/2 basal, 1/2 topdress; P and K mostly basal
    split = {
        "N": {"basal": round(total.get("N",{}).get("fertilizer_required_kg",0) * 0.5,2), "topdress": round(total.get("N",{}).get("fertilizer_required_kg",0) * 0.5,2)},
        "P2O5": {"basal": round(total.get("P2O5",{}).get("fertilizer_required_kg",0),2), "topdress": 0.0},
        "K2O": {"basal": round(total.get("K2O",{}).get("fertilizer_required_kg",0),2), "topdress": 0.0}
    }
    return {"crop": crop, "area_ha": area_ha, "expected_yield_t_per_ha": expected_yield_t_per_ha, "nutrient_plan": total, "split_suggestion": split, "generated_at": _now_iso()}

# ---------------------------
# Irrigation scheduling
# ---------------------------
def irrigation_suggestion(
    soil_texture: str,
    current_soil_moisture_fraction: float,   # 0..1 fraction of field capacity
    crop_stage: Optional[str] = None,
    forecast_rain_mm_next_48h: Optional[float] = None
) -> Dict[str, Any]:
    """
    Very simple heuristic:
     - choose threshold by soil texture
     - if moisture < threshold and no significant rain expected -> suggest irrigation
     - if crop stage is critical (flowering/grain_fill) be more conservative
    """
    st = soil_texture.lower() if soil_texture else "medium"
    threshold = _IRRIGATION_THRESHOLD.get("medium", 0.35)
    if st in ("sandy", "light"):
        threshold = _IRRIGATION_THRESHOLD["light"]
    elif st in ("clay", "heavy"):
        threshold = _IRRIGATION_THRESHOLD["heavy"]
    # stage multiplier
    critical = False
    if crop_stage:
        cs = crop_stage.lower()
        if cs in ("flowering", "grain_filling", "silking", "booting", "panicle_initiation"):
            critical = True
    # evaluate
    expect_rain = (forecast_rain_mm_next_48h or 0) >= 10.0
    recommend = False
    reason = []
    if current_soil_moisture_fraction is None:
        return {"error": "missing_soil_moisture"}
    if current_soil_moisture_fraction < threshold:
        if expect_rain:
            recommend = False
            reason.append("Rain expected in next 48h; delay irrigation")
        else:
            recommend = True
            reason.append("Soil moisture below threshold")
    else:
        reason.append("Soil moisture above threshold; no immediate irrigation needed")
    # if critical stage, recommend even if slightly above threshold
    if critical and current_soil_moisture_fraction < (threshold + 0.05):
        if not expect_rain:
            recommend = True
            reason.append("Crop at critical stage; maintain moisture")
    return {"soil_texture": st, "threshold": threshold, "current_moisture_fraction": round(current_soil_moisture_fraction,2), "forecast_rain_mm_next_48h": forecast_rain_mm_next_48h or 0.0, "recommend_irrigation": recommend, "reasons": reason, "generated_at": _now_iso()}

# ---------------------------
# Pest / disease triage (heuristic)
# ---------------------------
_PEST_SYMPTOM_DB = {
    "yellowing leaves": {"likely": ["nitrogen_deficiency", "viral_disease", "root_rot"], "advice": ["Check soil N, take foliar N test", "Inspect roots for rot", "Send sample to extension center"]},
    "white powdery spots": {"likely": ["powdery_mildew"], "advice": ["Apply recommended fungicide", "Ensure airflow between rows", "Avoid overhead irrigation in evening"]},
    "holes in leaves": {"likely": ["chewing_insects", "caterpillar"], "advice": ["Inspect for larvae underside", "Light trap at night", "Use biological control or targeted pesticide"]},
    "stunted growth": {"likely": ["nutrient_deficiency", "root_issues", "virus"], "advice": ["Soil test for nutrients", "Check for nematodes", "Isolate affected patches"]}
}

def pest_triage(symptoms_text: str) -> Dict[str, Any]:
    text = (symptoms_text or "").lower()
    results = []
    for key, info in _PEST_SYMPTOM_DB.items():
        if key in text:
            results.append({"symptom": key, "likely": info["likely"], "advice": info["advice"]})
    if not results:
        # fallback: keyword search
        matches = []
        for key in _PEST_SYMPTOM_DB.keys():
            if any(word in text for word in key.split()):
                matches.append(key)
        if matches:
            return {"matches": matches, "note": "partial_match", "generated_at": _now_iso()}
        return {"note": "no_match", "suggestion": "Collect image and send to expert or upload to field lab", "generated_at": _now_iso()}
    return {"results": results, "generated_at": _now_iso()}

# ---------------------------
# Scouting checklist
# ---------------------------
def scouting_checklist(crop: str, stage: str) -> Dict[str, Any]:
    crop = (crop or "").lower()
    stage = (stage or "").lower()
    checklist = [
        "Check for pest damage (leaf holes, discoloration)",
        "Measure soil moisture at multiple points",
        "Inspect irrigation uniformity",
        "Look for signs of nutrient deficiencies (yellowing, purpling)",
        "Check nearby fields for outbreak indicators"
    ]
    # add stage-specific items
    stage_items = []
    sp = _STAGE_PRACTICES.get(crop, {}).get(stage)
    if sp:
        stage_items.extend([f"Follow practice: {s}" for s in sp])
    return {"crop": crop, "stage": stage, "checklist": checklist + stage_items, "generated_at": _now_iso()}

# ---------------------------
# Combined advisory function (unified smart advisor)
# ---------------------------
def combined_advice(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Payload may include: crop, stage, area_ha, expected_yield_t_per_ha, soil_texture, soil_moisture_fraction,
    forecast_rain_mm_next_48h, symptoms_text, soil_nutrient (dict)
    """
    crop = payload.get("crop")
    stage = payload.get("stage")
    area = float(payload.get("area_ha", 0) or 0)
    expected_yield = float(payload.get("expected_yield_t_per_ha", 0) or 0)
    soil_texture = payload.get("soil_texture", "medium")
    soil_moisture = payload.get("soil_moisture_fraction")
    forecast_rain = payload.get("forecast_rain_mm_next_48h")
    soil_nutrient = payload.get("soil_nutrient")

    res = {"requested_at": _now_iso(), "crop": crop, "stage": stage, "components": {}}

    # Stage practices
    if crop and stage:
        res["components"]["stage_practices"] = stage_practices(crop, stage)

    # Fertilizer plan
    if crop and area > 0 and expected_yield > 0:
        res["components"]["fertilizer"] = fertilizer_recommendation(crop, area, expected_yield, soil_nutrient)

    # Irrigation
    if soil_moisture is not None:
        res["components"]["irrigation"] = irrigation_suggestion(soil_texture, float(soil_moisture), crop_stage=stage, forecast_rain_mm_next_48h=forecast_rain)

    # Pest triage
    symptoms = payload.get("symptoms_text")
    if symptoms:
        res["components"]["pest_triage"] = pest_triage(symptoms)

    # scouting checklist
    if crop and stage:
        res["components"]["scouting_checklist"] = scouting_checklist(crop, stage)

    # run any registered plugins (optional)
    plugin_results = {}
    with _lock:
        for name, fn in _plugin_registry.items():
            try:
                plugin_results[name] = fn(payload)
            except Exception as e:
                plugin_results[name] = {"error": str(e)}
    if plugin_results:
        res["components"]["plugins"] = plugin_results

    return res

# Expose alias for migration: smart_advice -> combined_advice
def smart_advice(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    New recommended unified API: frontend should migrate to this.
    Keeps the advanced combined_advice semantics.
    """
    return combined_advice(payload)

# ---------------------------
# Convenience: keep get_all_advisory and others untouched (legacy),
# while offering smart_advice for richer responses.
# ---------------------------

# End of advisory_service.py
