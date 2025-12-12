# backend/app/services/farmer/vision_service.py

"""
Vision Intelligence Service for Farmer POV
------------------------------------------

This service accepts an uploaded image (bytes) and performs:

 1. Image metadata extraction
 2. Basic color analysis
 3. Stubbed leaf health / crop stress detection
 4. Stubbed pest / disease scoring
 5. Stubbed nutrient deficiency suggestion
 6. Stubbed soil moisture estimation
 7. Optional: link insights to recommendation engine

All processing is in-memory. Real ML models can be dropped into the stub functions later.
"""

from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from io import BytesIO
from PIL import Image
import numpy as np
import uuid

# optional recommendation import
try:
    from app.services.farmer.recommendation_engine_service import generate_recommendations_for_unit
except:
    generate_recommendations_for_unit = None


# --------------------------------------
# In-memory store for processed images
# --------------------------------------
_vision_store: Dict[str, Dict[str, Any]] = {}


# --------------------------------------
# Utility: get basic metadata
# --------------------------------------
def _extract_metadata(img: Image.Image) -> Dict[str, Any]:
    return {
        "width": img.width,
        "height": img.height,
        "mode": img.mode,
        "format": img.format,
    }


# --------------------------------------
# Utility: dominant color estimation
# --------------------------------------
def _extract_dominant_color(img: Image.Image) -> Tuple[int, int, int]:
    """
    Simple color downsampling + k-means-like heuristic without heavy libs.
    """
    small = img.resize((64, 64))  # speed
    arr = np.array(small).reshape(-1, 3)
    mean_color = arr.mean(axis=0)
    return tuple(int(c) for c in mean_color)


# --------------------------------------
# Stub: detect leaf / crop health issues
# --------------------------------------
def _detect_leaf_health_stub(img: Image.Image) -> Dict[str, Any]:
    """
    Simple heuristic based on green-channel strength.
    """
    small = img.resize((64, 64))
    arr = np.array(small)
    green_mean = float(arr[:, :, 1].mean())

    if green_mean > 150:
        health = "healthy"
        score = 0.90
    elif green_mean > 110:
        health = "mild_stress"
        score = 0.65
    else:
        health = "stress_detected"
        score = 0.40

    return {
        "status": health,
        "confidence": round(score, 2),
        "green_mean": green_mean
    }


# --------------------------------------
# Stub: detect pest / disease
# --------------------------------------
def _detect_pest_disease_stub(img: Image.Image) -> Dict[str, Any]:
    """
    Heuristic: analyze brown/yellow pixel ratio.
    """
    small = img.resize((64, 64))
    arr = np.array(small).astype(float)

    # simple yellow/brown pixel heuristic
    yellowish = ((arr[:, :, 0] > 150) & (arr[:, :, 1] > 150)).mean()
    brownish = ((arr[:, :, 0] > 120) & (arr[:, :, 1] < 100)).mean()

    pest_score = round((yellowish * 0.4 + brownish * 0.6), 2)

    if pest_score > 0.45:
        state = "high_risk"
    elif pest_score > 0.25:
        state = "possible_risk"
    else:
        state = "low_risk"

    return {
        "state": state,
        "risk_score": pest_score,
        "yellowish_ratio": round(float(yellowish), 3),
        "brownish_ratio": round(float(brownish), 3)
    }


# --------------------------------------
# Stub: nutrient deficiency suggestions
# --------------------------------------
def _detect_nutrient_deficiency_stub(img: Image.Image) -> Dict[str, Any]:
    """
    Very primitive heuristic. Replace with model later.
    """
    small = img.resize((64, 64))
    arr = np.array(small).astype(float)

    # spot pale/yellowish regions
    yellow_ratio = ((arr[:, :, 1] > 150) & (arr[:, :, 2] < 120)).mean()

    if yellow_ratio > 0.30:
        suggestion = "possible_nitrogen_deficiency"
    elif yellow_ratio > 0.15:
        suggestion = "minor_nutrient_variation"
    else:
        suggestion = "no_major_deficiency_indicated"

    return {
        "suggestion": suggestion,
        "yellow_ratio": round(float(yellow_ratio), 3)
    }


# --------------------------------------
# Stub: soil moisture estimation
# --------------------------------------
def _estimate_soil_moisture_stub(img: Image.Image) -> Dict[str, Any]:
    """
    Checks darkness levels to heuristically guess soil wet/dry.
    """
    small = img.resize((64, 64))
    arr = np.array(small).astype(float)
    brightness = arr.mean()

    if brightness < 70:
        moisture = "wet"
    elif brightness < 130:
        moisture = "normal"
    else:
        moisture = "dry"

    return {
        "moisture": moisture,
        "brightness_mean": round(float(brightness), 2)
    }


# --------------------------------------
# Main pipeline
# --------------------------------------
def analyze_image(img_bytes: bytes, unit_id: Optional[str] = None, tags: Optional[list] = None) -> Dict[str, Any]:
    try:
        img = Image.open(BytesIO(img_bytes)).convert("RGB")
    except Exception as e:
        return {"error": "invalid_image", "details": str(e)}

    image_id = str(uuid.uuid4())

    metadata = _extract_metadata(img)
    dom_color = _extract_dominant_color(img)

    health = _detect_leaf_health_stub(img)
    pest = _detect_pest_disease_stub(img)
    nutrient = _detect_nutrient_deficiency_stub(img)
    moisture = _estimate_soil_moisture_stub(img)

    # optional: recommendations based on image results
    recs = None
    if unit_id and generate_recommendations_for_unit:
        try:
            recs = generate_recommendations_for_unit(unit_id)
        except:
            recs = None

    record = {
        "image_id": image_id,
        "unit_id": unit_id,
        "tags": tags or [],
        "captured_at": datetime.utcnow().isoformat(),
        "metadata": metadata,
        "dominant_color_rgb": dom_color,
        "health_assessment": health,
        "pest_assessment": pest,
        "nutrient_assessment": nutrient,
        "soil_moisture_assessment": moisture,
        "linked_recommendations": recs,
    }

    _vision_store[image_id] = record
    return record


def get_image_analysis(image_id: str) -> Dict[str, Any]:
    return _vision_store.get(image_id, {"error": "not_found"})


def list_images(unit_id: Optional[str] = None) -> Dict[str, Any]:
    items = list(_vision_store.values())
    if unit_id:
        items = [i for i in items if i.get("unit_id") == unit_id]
    return {"count": len(items), "items": items}
