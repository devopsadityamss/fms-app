"""
Phenology Progress Estimator (stub-ready)
----------------------------------------

Purpose:
 - Estimate crop phenological stage based on:
      - crop type
      - sowing date
      - days after sowing (DAS)
      - accumulated growing degree days (GDD)
      - optional inputs: canopy %, health condition, pest stress
 - Output:
      - current stage
      - progress percent (0–100)
      - expected next stage
      - estimated days to harvest
"""

from typing import Dict, Any, Optional
from datetime import datetime, date
import uuid

try:
    from app.services.farmer import canopy_estimation_service as canopy_svc
except Exception:
    canopy_svc = None

try:
    from app.services.farmer import vision_service as vision_svc
except Exception:
    vision_svc = None


_phenology_store: Dict[str, Dict[str, Any]] = {}


# -------------------------------------------------------------
# Helpers
# -------------------------------------------------------------
def _now() -> str:
    return datetime.utcnow().isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


def _days_between(start_date: str, end_date: Optional[str] = None) -> int:
    try:
        s = date.fromisoformat(start_date)
    except:
        return 0
    e = date.fromisoformat(end_date) if end_date else date.today()
    return (e - s).days


# -------------------------------------------------------------
# Stage heuristic tables (you can extend for more crops)
# -------------------------------------------------------------
PHENOLOGY_TABLE = {
    "paddy": [
        ("germination", 0, 10),
        ("seedling", 11, 25),
        ("tillering", 26, 45),
        ("panicle_initiation", 46, 65),
        ("booting", 66, 85),
        ("heading", 86, 105),
        ("flowering", 106, 120),
        ("grain_filling", 121, 140),
        ("maturity", 141, 160)
    ],
    "wheat": [
        ("germination", 0, 12),
        ("tillering", 13, 35),
        ("stem_elongation", 36, 60),
        ("booting", 61, 80),
        ("heading", 81, 95),
        ("flowering", 96, 110),
        ("grain_filling", 111, 130),
        ("maturity", 131, 150)
    ]
    # Add more crops in future
}


def _estimate_stage(crop: str, das: int) -> Dict[str, Any]:
    """
    Uses a DAS-based table to estimate growth stage.
    """
    table = PHENOLOGY_TABLE.get(crop.lower())
    if not table:
        return {
            "stage": "unknown",
            "progress": 0,
            "next_stage": None,
            "days_to_harvest": None
        }

    for stage, start_das, end_das in table:
        if start_das <= das <= end_das:
            stage_length = end_das - start_das + 1
            progress = round((das - start_das) / stage_length * 100, 2)
            next_stage = None
            idx = table.index((stage, start_das, end_das))
            if idx < len(table) - 1:
                next_stage = table[idx + 1][0]

            days_to_harvest = table[-1][2] - das

            return {
                "stage": stage,
                "progress": progress,
                "next_stage": next_stage,
                "days_to_harvest": max(0, days_to_harvest)
            }

    # beyond maturity
    return {
        "stage": "post_maturity",
        "progress": 100,
        "next_stage": None,
        "days_to_harvest": 0
    }


# -------------------------------------------------------------
# MAIN ANALYSIS
# -------------------------------------------------------------
def analyze_phenology(
    unit_id: str,
    crop_type: str,
    sowing_date: str,
    canopy_photo_id: Optional[str] = None,
    field_notes: Optional[str] = None
) -> Dict[str, Any]:

    das = _days_between(sowing_date)
    base_est = _estimate_stage(crop_type, das)

    canopy_est = None
    if canopy_photo_id and canopy_svc:
        try:
            canopy_est = canopy_svc.estimate_canopy_from_photo_id(canopy_photo_id, unit_id)
        except:
            canopy_est = None

    # optional “soft correction” using canopy percent
    if canopy_est and "error" not in canopy_est:
        c = canopy_est["estimation"]["canopy_percent"]
        if c < 20 and das > 40:
            base_est["stage"] = base_est["stage"] + "_slow"
        elif c > 70 and das < 30:
            base_est["stage"] = base_est["stage"] + "_fast"

    # optional health integration if available
    vision_snapshot = None
    if canopy_est and canopy_est.get("vision_analysis"):
        vision_snapshot = canopy_est.get("vision_analysis")

    pid = _new_id()
    record = {
        "id": pid,
        "unit_id": unit_id,
        "crop_type": crop_type,
        "sowing_date": sowing_date,
        "days_after_sowing": das,
        "phenology": base_est,
        "canopy_reference": canopy_photo_id,
        "canopy_estimation": canopy_est,
        "vision_snapshot": vision_snapshot,
        "field_notes": field_notes,
        "created_at": _now()
    }

    _phenology_store[pid] = record
    return record


# -------------------------------------------------------------
# Accessors
# -------------------------------------------------------------
def get_record(phenology_id: str) -> Dict[str, Any]:
    return _phenology_store.get(phenology_id, {"error": "not_found"})


def list_records(unit_id: Optional[str] = None) -> Dict[str, Any]:
    items = list(_phenology_store.values())
    if unit_id:
        items = [i for i in items if i.get("unit_id") == unit_id]
    return {"count": len(items), "items": items}


def _clear_store():
    _phenology_store.clear()
