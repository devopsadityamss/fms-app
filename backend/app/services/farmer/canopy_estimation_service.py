"""
Canopy Coverage Estimation Service (stub-ready)
-----------------------------------------------

This module estimates canopy coverage (%) based on:
 - Uploaded image bytes, OR
 - A previously stored photo timeline ID

In Phase-1 (stub):
 - Uses green-channel intensity heuristics
 - Uses pixel brightness distribution
 - Computes:
      canopy_percent          (0–100)
      ground_cover_fraction   (0–1)
      vegetative_density      (0–1)
      light_interception_idx  (0–1)
 - Optionally integrates with vision_service for better assessments
"""

from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from io import BytesIO
import uuid
import numpy as np
from PIL import Image

# in-memory store
_canopy_store: Dict[str, Dict[str, Any]] = {}

# optional imports
try:
    from app.services.farmer import vision_service as vision_svc
except Exception:
    vision_svc = None

try:
    from app.services.farmer import photo_timeline_service as photo_svc
except Exception:
    photo_svc = None


def _now() -> str:
    return datetime.utcnow().isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


# -------------------------------------------------------------
# Helper: convert bytes → PIL
# -------------------------------------------------------------
def _load_image(img_bytes: bytes) -> Optional[Image.Image]:
    try:
        return Image.open(BytesIO(img_bytes)).convert("RGB")
    except Exception:
        return None


# -------------------------------------------------------------
# Core canopy estimator (stub heuristic)
# -------------------------------------------------------------
def _estimate_canopy(img: Image.Image) -> Dict[str, Any]:
    """
    Very simple heuristic:
     - green channel mean indicates vegetation presence
     - brightness variance indicates canopy density variation
     - green histogram proportion = canopy %
    """

    arr = np.array(img.resize((128, 128)))  # small for speed
    green = arr[:, :, 1].astype(float)
    brightness = arr.mean(axis=2)

    green_mean = green.mean()
    green_ratio = (green > 120).mean()   # proportion of green pixels

    canopy_percent = round(green_ratio * 100, 2)
    ground_cover_fraction = round(min(1.0, green_ratio * 1.1), 3)
    vegetative_density = round(min(1.0, np.std(green) / 60), 3)
    light_interception_idx = round(min(1.0, green_mean / 255), 3)

    return {
        "canopy_percent": canopy_percent,
        "ground_cover_fraction": ground_cover_fraction,
        "vegetative_density": vegetative_density,
        "light_interception_idx": light_interception_idx,
        "green_mean": float(green_mean),
        "green_ratio": float(green_ratio)
    }


# -------------------------------------------------------------
# MAIN ENTRY
# -------------------------------------------------------------
def estimate_canopy_from_bytes(
    img_bytes: bytes,
    unit_id: Optional[str] = None,
    tags: Optional[list] = None
) -> Dict[str, Any]:
    img = _load_image(img_bytes)
    if img is None:
        return {"error": "invalid_image"}

    est = _estimate_canopy(img)

    # optional vision integration
    analysis = None
    if vision_svc:
        try:
            analysis = vision_svc.analyze_image(img_bytes, unit_id=unit_id, tags=tags)
        except Exception:
            analysis = None

    rec_id = _new_id()
    record = {
        "id": rec_id,
        "unit_id": unit_id,
        "source": "direct_bytes",
        "estimation": est,
        "vision_analysis": analysis,
        "tags": tags or [],
        "created_at": _now()
    }
    _canopy_store[rec_id] = record
    return record


def estimate_canopy_from_photo_id(
    photo_id: str,
    unit_id: Optional[str] = None
) -> Dict[str, Any]:
    if not photo_svc:
        return {"error": "photo_service_not_available"}

    result = photo_svc.get_photo_bytes(photo_id)
    if not result:
        return {"error": "photo_not_found"}

    img_bytes, _, _ = result
    return estimate_canopy_from_bytes(img_bytes, unit_id)


# -------------------------------------------------------------
# Accessors
# -------------------------------------------------------------
def get_canopy_record(canopy_id: str) -> Dict[str, Any]:
    return _canopy_store.get(canopy_id, {"error": "not_found"})


def list_canopy_records(unit_id: Optional[str] = None) -> Dict[str, Any]:
    items = list(_canopy_store.values())
    if unit_id:
        items = [i for i in items if i.get("unit_id") == unit_id]
    return {"count": len(items), "items": items}


def _clear_store():
    _canopy_store.clear()
