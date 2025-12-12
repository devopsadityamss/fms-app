# backend/app/services/farmer/soil_nutrient_service.py

"""
Soil Nutrient Balance Engine + Fertilizer Recommendation System (in-memory)

Features:
 - Store soil test results per unit
 - Track N, P, K, OC, pH, EC and micronutrients (Zn, B, S optional)
 - Detect nutrient deficiencies/excesses
 - Recommend fertilizer dose based on crop & stage
 - Soil health scoring
 - Soil improvement suggestions
 - Full soil summary per unit
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
import uuid

# Storage
_soil_tests: Dict[str, Dict[str, Any]] = {}       # test_id -> record
_tests_by_unit: Dict[str, List[str]] = {}         # unit_id -> [test_ids]


def _now():
    return datetime.utcnow().isoformat()


# -----------------------------------------------------------
# RECORD SOIL TEST
# -----------------------------------------------------------
def record_soil_test(
    unit_id: str,
    n: float,
    p: float,
    k: float,
    oc: float,
    ph: float,
    ec: float,
    zn: Optional[float] = None,
    b: Optional[float] = None,
    s: Optional[float] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    
    tid = f"soil_{uuid.uuid4()}"
    rec = {
        "test_id": tid,
        "unit_id": str(unit_id),
        "n": n,
        "p": p,
        "k": k,
        "oc": oc,
        "ph": ph,
        "ec": ec,
        "zn": zn,
        "b": b,
        "s": s,
        "metadata": metadata or {},
        "created_at": _now()
    }

    _soil_tests[tid] = rec
    _tests_by_unit.setdefault(str(unit_id), []).append(tid)
    return rec


# -----------------------------------------------------------
# LIST LATEST TEST FOR A UNIT
# -----------------------------------------------------------
def get_latest_test(unit_id: str) -> Optional[Dict[str, Any]]:
    ids = _tests_by_unit.get(str(unit_id), [])
    if not ids:
        return None
    # return most recent by created_at
    tests = [_soil_tests[i] for i in ids]
    tests.sort(key=lambda x: x["created_at"], reverse=True)
    return tests[0]


# -----------------------------------------------------------
# DEFICIENCY DETECTION
# -----------------------------------------------------------
def detect_deficiencies(test: Dict[str, Any]) -> List[str]:
    issues = []

    if test["n"] < 250:
        issues.append("Nitrogen deficiency")
    if test["p"] < 20:
        issues.append("Phosphorus deficiency")
    if test["k"] < 150:
        issues.append("Potassium deficiency")
    if test["oc"] < 0.7:
        issues.append("Low organic carbon")
    if test["ph"] < 6 or test["ph"] > 8:
        issues.append("Soil pH imbalance")
    if test.get("zn") is not None and test["zn"] < 1:
        issues.append("Zinc deficiency")
    if test.get("b") is not None and test["b"] < 0.5:
        issues.append("Boron deficiency")

    return issues


# -----------------------------------------------------------
# CROP-STAGE FERTILIZER RECOMMENDATION
# -----------------------------------------------------------
FERT_REQUIREMENTS = {
    "paddy": {
        "initial": {"n": 40, "p": 20, "k": 20},
        "mid":     {"n": 30, "p": 0,  "k": 20},
        "late":    {"n": 20, "p": 0,  "k": 0},
    },
    "wheat": {
        "initial": {"n": 40, "p": 20, "k": 20},
        "mid":     {"n": 30, "p": 0,  "k": 20},
        "late":    {"n": 20, "p": 10, "k": 0},
    },
    "maize": {
        "initial": {"n": 40, "p": 20, "k": 20},
        "mid":     {"n": 40, "p": 0,  "k": 30},
        "late":    {"n": 20, "p": 0,  "k": 0},
    }
}


def recommend_fertilizer(crop: str, stage: str, area_acres: float) -> Dict[str, Any]:
    crop = crop.lower()
    stage = stage.lower()

    req_map = FERT_REQUIREMENTS.get(crop, {})
    dose = req_map.get(stage, {"n": 20, "p": 10, "k": 10})

    return {
        "crop": crop,
        "stage": stage,
        "recommended_npk_per_acre": dose,
        "total_for_area": {
            "n": round(dose["n"] * area_acres, 2),
            "p": round(dose["p"] * area_acres, 2),
            "k": round(dose["k"] * area_acres, 2),
        }
    }


# -----------------------------------------------------------
# SOIL HEALTH SCORE (0–100)
# -----------------------------------------------------------
def soil_health_score(test: Dict[str, Any]) -> int:

    score = 100

    # OC major weight
    if test["oc"] < 1:
        score -= 25
    if test["oc"] < 0.7:
        score -= 40

    # pH
    if test["ph"] < 6 or test["ph"] > 8:
        score -= 20

    # N P K
    if test["n"] < 250:
        score -= 10
    if test["p"] < 20:
        score -= 10
    if test["k"] < 150:
        score -= 10

    return max(0, score)


# -----------------------------------------------------------
# SUGGESTIONS
# -----------------------------------------------------------
def soil_improvement_suggestions(test: Dict[str, Any]) -> List[str]:
    s = []
    if test["oc"] < 1:
        s.append("Apply compost/FYM to increase organic carbon")
    if test["n"] < 250:
        s.append("Use nitrogenous fertilizers or green manure crops")
    if test["p"] < 20:
        s.append("Apply DAP/SSP based on crop requirement")
    if test["k"] < 150:
        s.append("Apply MOP or organic potash sources")
    if test["ph"] < 6:
        s.append("Apply lime to improve soil pH")
    if test["ph"] > 8:
        s.append("Use gypsum or organic amendments to lower pH")
    if not s:
        s.append("Soil health is good. Maintain organic matter & balanced fertilization.")
    return s


# -----------------------------------------------------------
# FULL SOIL SUMMARY
# -----------------------------------------------------------
def soil_summary(unit_id: str, crop: str, stage: str, area_acres: float) -> Dict[str, Any]:
    test = get_latest_test(unit_id)
    if not test:
        return {"error": "no_soil_data"}

    return {
        "unit_id": unit_id,
        "latest_test": test,
        "deficiencies": detect_deficiencies(test),
        "fertilizer_recommendation": recommend_fertilizer(crop, stage, area_acres),
        "soil_health_score": soil_health_score(test),
        "suggestions": soil_improvement_suggestions(test),
        "timestamp": _now()
    }
