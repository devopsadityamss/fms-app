# backend/app/services/farmer/chat_advisory_service.py

"""
Intermediate Chat Advisory Service (Feature 294, Option B)

- Rule-based intent detection (multi-intent)
- Crop & stage extraction (simple)
- Dispatcher that calls functions from advisory_service + weather_service
- Confidence scoring & multi-intent outputs
- In-memory FAQ / suggested questions
- Designed to be lightweight and easy to extend
"""

from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
import re

# reuse advisory utilities
from app.services.farmer.advisory_service import (
    fertilizer_recommendation,
    irrigation_suggestion,
    pest_triage,
    stage_practices,
    scouting_checklist,
    combined_advice,
    # legacy helpers could be used as fallback
    get_general_advice,
    get_stage_based_advice,
    get_weather_linked_advice,
)
from app.services.farmer.weather_service import get_current_weather

# Intent definitions and keywords
_INTENTS = {
    "pest": ["pest", "disease", "infection", "white", "spots", "yellow", "holes", "wilting", "mildew", "borer", "aphid", "caterpillar"],
    "fertilizer": ["fertilizer", "fertilise", "fertilize", "nutrient", "nitrogen", "npk", "phosphorus", "potash", "manure", "dose"],
    "irrigation": ["irrigat", "water", "soil moisture", "moisture", "dry", "wet", "drain", "rain", "watered"],
    "stage": ["stage", "sowing", "tillering", "vegetative", "flowering", "harvest", "panicle", "booting", "heading", "grain"],
    "weather": ["forecast", "weather", "rain", "temperature", "hot", "cold", "storm"],
    "scouting": ["scout", "checklist", "inspect", "inspection", "scouting"],
    "general": ["what", "how", "when", "should", "advice", "recommendation", "recommend"],
    "yield": ["yield", "produce", "productivity", "output"],
    "cost": ["cost", "expense", "price", "market"],
}

_SUPPORTED_CROPS = ["rice", "wheat", "maize", "cotton", "sugarcane", "soybean", "groundnut"]

_SUGGESTED_QUESTIONS = [
    "When should I irrigate this week?",
    "Leaves are yellowing — what to do?",
    "What fertilizer dose for expected yield of 2 t/ha?",
    "I see white powdery spots on leaves — what pest/disease is it?",
    "How many labor hours needed for harvest on 2 acres?",
    "Create a scouting checklist for flowering stage.",
]

_FAQ = {
    "when to irrigate": "Irrigation depends on crop stage, soil moisture and forecast. Supply current soil moisture and forecast if available for precise advice.",
    "yellow leaves": "Yellowing is often nitrogen deficiency or water stress — supply crop, stage and a photo if possible.",
    "white spots": "White powdery spots often indicate powdery mildew — inspect for fungal growth and consider recommended fungicide.",
}

# helper small regexes
_CROP_RE = re.compile(r"\b(" + "|".join(re.escape(c) for c in _SUPPORTED_CROPS) + r")\b", re.IGNORECASE)
_STAGE_RE = re.compile(r"\b(sowing|tillering|vegetative|flowering|harvest|panicle|booting|heading|grain_fill|grain)\b", re.IGNORECASE)

def _now_iso() -> str:
    return datetime.utcnow().isoformat()

# ---------- Intent detection ----------
def detect_intents_and_entities(query: str) -> Tuple[List[Tuple[str, float]], Dict[str, Any]]:
    """
    Returns:
      - intents: list of (intent_name, score) sorted descending
      - entities: dict with detected crop, stage, symptom_keywords, numeric values (like area, yield)
    Strategy:
      - Count keyword matches for each intent
      - Score = matches / sqrt(total words) (simple normalization)
    """
    q = (query or "").lower()
    words = re.findall(r"\w+", q)
    total_words = max(1, len(words))
    intent_scores: Dict[str, int] = {}
    for intent, kws in _INTENTS.items():
        cnt = 0
        for kw in kws:
            if kw in q:
                cnt += 1
        intent_scores[intent] = cnt

    # convert to normalized float scores
    intents_list = []
    for intent, cnt in intent_scores.items():
        score = float(cnt) / (total_words ** 0.5) if cnt > 0 else 0.0
        if score > 0:
            intents_list.append((intent, round(score, 4)))
    # sort
    intents_list.sort(key=lambda x: x[1], reverse=True)

    # extract crop
    crop_match = _CROP_RE.search(query)
    crop = crop_match.group(0).lower() if crop_match else None

    # extract stage
    stage_match = _STAGE_RE.search(query)
    stage = stage_match.group(0).lower() if stage_match else None

    # basic symptom extraction: look for symptom phrases in pest triage DB via advisory_service (we can't import the DB directly here),
    # but we'll capture key symptom words
    symptom_keywords = []
    # common symptom words
    for symptom_kw in ["yellow", "white", "spots", "holes", "wilting", "stunted", "powdery", "mildew", "brown", "curl"]:
        if symptom_kw in q:
            symptom_keywords.append(symptom_kw)

    # numeric extraction for area and yield
    nums = re.findall(r"(\d+(\.\d+)?)\s*(ha|acre|acres|t/ha|ton|tons|t)", query, re.IGNORECASE)
    area_ha = None
    expected_yield = None
    # a naive parse: if "ha" present set area; if "t/ha" or "t per ha" set expected yield
    for match in nums:
        val = float(match[0])
        unit = match[2].lower()
        if "ha" in unit:
            area_ha = val
        if "t" in unit or "ton" in unit:
            # if unit is "t/ha" treat as yield
            if "t/ha" in unit or "/ha" in query:
                expected_yield = val

    entities = {"crop": crop, "stage": stage, "symptoms": symptom_keywords, "area_ha": area_ha, "expected_yield_t_per_ha": expected_yield}
    return intents_list, entities

# ---------- Confidence helper ----------
def compute_confidence(primary_intent_score: float, secondary_scores: List[float], entity_strength: float = 0.0) -> float:
    """
    Combines primary intent score, presence of entities and secondary intent scores into a confidence metric 0..1
    """
    base = primary_intent_score
    secondary = sum(secondary_scores) * 0.25
    ent = entity_strength * 0.25
    conf = base + secondary + ent
    # scale -> sigmoid-like clamp between 0 and 1
    conf = max(0.0, min(conf, 1.0))
    return round(conf, 4)

# ---------- Dispatcher (routes question to appropriate advisory functions) ----------
def _call_pest_triage(query: str, crop: Optional[str], stage: Optional[str]) -> Dict[str, Any]:
    # pass the query to pest_triage which expects symptom text
    result = pest_triage(query)
    return result

def _call_fertilizer(query: str, crop: Optional[str], entities: Dict[str, Any]) -> Dict[str, Any]:
    # Need area and expected_yield; try entities, else fallback to conservative defaults
    area = entities.get("area_ha") or entities.get("area") or 0.0
    expected = entities.get("expected_yield_t_per_ha") or 1.0
    if not crop:
        # return a generic guidance note
        return {"error": "crop_required_for_precise_fertilizer", "note": "Please provide crop (e.g., rice, wheat) for fertilizer calculation."}
    return fertilizer_recommendation(crop, float(area), float(expected))

def _call_irrigation(query: str, crop: Optional[str], entities: Dict[str, Any], unit_id: Optional[int] = None) -> Dict[str, Any]:
    # Gather soil texture & moisture from query if present (very naive)
    # If unit_id is provided, try to get recent weather to decide forecast rain
    # We'll parse numbers mention like "soil moisture 0.3"
    moisture_match = re.search(r"soil moisture\s*[:=]?\s*(0?\.\d+|\d+%?)", query)
    soil_moisture = None
    if moisture_match:
        val = moisture_match.group(1)
        if val.endswith("%"):
            try:
                soil_moisture = float(val.strip("%")) / 100.0
            except:
                soil_moisture = None
        else:
            try:
                soil_moisture = float(val)
            except:
                soil_moisture = None

    # simple soil texture detection keywords
    soil_texture = "medium"
    for t in ["sandy", "clay", "loam", "heavy", "light"]:
        if t in query.lower():
            soil_texture = t
            break

    # forecast rain via weather service if unit_id provided
    forecast_rain = None
    if unit_id is not None:
        try:
            w = get_current_weather(unit_id) or {}
            # try to extract next_48h rainfall if weather service provides it (fallback)
            forecast_rain = w.get("forecast_rain_48h") or w.get("rainfall_next_48h") or None
        except Exception:
            forecast_rain = None

    if soil_moisture is None:
        # fallback suggestion: ask for soil moisture
        return {"error": "soil_moisture_required", "note": "Please provide current soil moisture (e.g., 'soil moisture 0.32' or sensor reading)."}

    return irrigation_suggestion(soil_texture, float(soil_moisture), crop_stage=entities.get("stage"), forecast_rain_mm_next_48h=forecast_rain)

def _call_stage_practices(query: str, crop: Optional[str], entities: Dict[str, Any]) -> Dict[str, Any]:
    if not crop or not entities.get("stage"):
        return {"error": "crop_and_stage_required", "note": "Provide crop and stage for stage-specific practices."}
    return stage_practices(crop, entities.get("stage"))

def _call_scouting(query: str, crop: Optional[str], entities: Dict[str, Any]) -> Dict[str, Any]:
    if not crop or not entities.get("stage"):
        return {"error": "crop_and_stage_required", "note": "Provide crop and stage for scouting checklist."}
    return scouting_checklist(crop, entities.get("stage"))

def _call_general(query: str, unit_id: Optional[int]) -> Dict[str, Any]:
    # Try weather-linked advice if unit_id present
    if unit_id:
        try:
            weather = get_current_weather(unit_id) or {}
            return get_weather_linked_advice(unit_id, weather)
        except Exception:
            pass
    # fallback to general list
    return {"general": get_general_advice(unit_id or 0)}

# ---------- Public service function ----------
def answer_query(query: str, unit_id: Optional[int] = None, crop: Optional[str] = None, stage: Optional[str] = None) -> Dict[str, Any]:
    """
    Main entrypoint. Returns a structured response including:
      - detected intents (ordered)
      - entities (crop, stage, etc.)
      - primary answer (best matched handler)
      - secondary answers (if multi-intent)
      - confidence scores
    """
    intents_scores, entities = detect_intents_and_entities(query)

    # allow provided crop/stage to override extracted
    if crop:
        entities["crop"] = (crop or "").lower()
    if stage:
        entities["stage"] = (stage or "").lower()

    # Build a ranked list of intents; if empty, fallback to 'general'
    if not intents_scores:
        intents_scores = [("general", 0.2)]

    primary_intent, primary_score = intents_scores[0]
    secondary_intents = [s for (_, s) in intents_scores[1:3]]

    # compute entity strength: presence of crop/stage/symptoms/area increases confidence
    entity_strength = 0.0
    if entities.get("crop"):
        entity_strength += 0.3
    if entities.get("stage"):
        entity_strength += 0.2
    if entities.get("symptoms"):
        entity_strength += 0.2
    if entities.get("area_ha") or entities.get("expected_yield_t_per_ha"):
        entity_strength += 0.1
    entity_strength = min(entity_strength, 0.9)

    confidence = compute_confidence(primary_score, [s for (__, s) in intents_scores[1:3]], entity_strength)

    # route to handler
    primary_result = {}
    source = None

    if primary_intent == "pest":
        primary_result = _call_pest_triage(" ".join(entities.get("symptoms") or [query]), entities.get("crop"), entities.get("stage"))
        source = "pest_triage"
    elif primary_intent == "fertilizer":
        primary_result = _call_fertilizer(query, entities.get("crop"), entities)
        source = "fertilizer_recommendation"
    elif primary_intent == "irrigation":
        primary_result = _call_irrigation(query, entities.get("crop"), entities, unit_id=unit_id)
        source = "irrigation_suggestion"
    elif primary_intent == "stage":
        primary_result = _call_stage_practices(query, entities.get("crop"), entities)
        source = "stage_practices"
    elif primary_intent == "scouting":
        primary_result = _call_scouting(query, entities.get("crop"), entities)
        source = "scouting_checklist"
    elif primary_intent == "weather":
        primary_result = _call_general(query, unit_id)
        source = "weather_linked_advice"
    else:
        # fallback / general
        primary_result = _call_general(query, unit_id)
        source = "general_advice"

    # also attempt one secondary handler if the top secondary intent score is non-zero (multi-intent)
    secondary_answer = None
    if len(intents_scores) > 1 and intents_scores[1][1] > 0.0:
        sec_intent = intents_scores[1][0]
        try:
            if sec_intent == "pest" and primary_intent != "pest":
                secondary_answer = _call_pest_triage(query, entities.get("crop"), entities.get("stage"))
            elif sec_intent == "fertilizer" and primary_intent != "fertilizer":
                secondary_answer = _call_fertilizer(query, entities.get("crop"), entities)
            elif sec_intent == "irrigation" and primary_intent != "irrigation":
                secondary_answer = _call_irrigation(query, entities.get("crop"), entities, unit_id=unit_id)
            elif sec_intent == "stage" and primary_intent != "stage":
                secondary_answer = _call_stage_practices(query, entities.get("crop"), entities)
        except Exception:
            secondary_answer = None

    # build final response
    response = {
        "query": query,
        "detected_intents": [{"intent": i, "score": s} for (i, s) in intents_scores],
        "entities": entities,
        "primary": {"intent": primary_intent, "confidence": confidence, "source": source, "result": primary_result},
        "secondary": {"result": secondary_answer} if secondary_answer else None,
        "faq_suggestion": None,
        "timestamp": _now_iso()
    }

    # quick FAQ lookup if primary is low-confidence and a known FAQ key exists
    if confidence < 0.2:
        for k, v in _FAQ.items():
            if k in query.lower():
                response["faq_suggestion"] = {"question": k, "answer": v}
                break

    return response

# ---------- utility endpoints ----------
def supported_intents() -> List[str]:
    return list(_INTENTS.keys())

def suggested_questions() -> List[str]:
    return _SUGGESTED_QUESTIONS
