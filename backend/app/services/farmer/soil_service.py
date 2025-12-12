# backend/app/services/farmer/soil_service.py

from datetime import datetime
from typing import Dict, Any, List, Optional
import uuid


# ===================================================================
# MOCK SOIL INTELLIGENCE (quick snapshot & recommendations for UI)
# ===================================================================

# Mock soil intelligence: moisture, nutrients, recommendations.
# No DB usage — returns mock values for frontend and API.

SOIL_MOCK = {
    "moisture_percent": 28,
    "ph": 6.4,
    "organic_matter_percent": 2.1,
    "nitrogen_ppm": 12,
    "phosphorus_ppm": 8,
    "potassium_ppm": 110,
}


def get_soil_snapshot(unit_id: int) -> Dict[str, Any]:
    """Return current soil snapshot (mock)."""
    return {
        "unit_id": unit_id,
        "timestamp": datetime.utcnow(),
        **SOIL_MOCK,
    }


def estimate_soil_moisture_trend(unit_id: int) -> Dict[str, Any]:
    """
    Mock trend for the next 7 days. Positive means increasing moisture.
    """
    return {
        "unit_id": unit_id,
        "trend_days": [
            {"day_offset": i, "expected_moisture_percent": SOIL_MOCK["moisture_percent"] + (i * 0.3)}
            for i in range(7)
        ],
    }


def get_nutrient_recommendations(unit_id: int, crop: str = "generic") -> List[Dict[str, Any]]:
    """
    Mock nutrient improvement suggestions based on soil snapshot and crop.
    """
    recs = []
    if SOIL_MOCK["nitrogen_ppm"] < 20:
        recs.append({
            "nutrient": "N",
            "recommendation": "Apply urea at light dose (split application recommended)",
            "priority": "medium",
        })
    if SOIL_MOCK["ph"] < 6.5:
        recs.append({
            "nutrient": "pH",
            "recommendation": "Apply lime to increase pH gradually",
            "priority": "low",
        })
    return recs


def get_soil_intelligence(unit_id: int, crop: str = "generic") -> Dict[str, Any]:
    """Unified soil intelligence response."""
    return {
        "unit_id": unit_id,
        "timestamp": datetime.utcnow(),
        "soil_snapshot": get_soil_snapshot(unit_id),
        "moisture_trend": estimate_soil_moisture_trend(unit_id),
        "nutrient_recommendations": get_nutrient_recommendations(unit_id, crop),
    }


# ===================================================================
# FULL SOIL TESTING & NUTRIENT RECOMMENDATION ENGINE (in-memory)
# ===================================================================

"""
Soil Testing & Nutrient Recommendation Engine (in-memory)
Functionalities:
 - store multiple soil test results per farmer unit
 - interpret NPK/pH/EC/OC/micronutrients
 - detect soil issues (salinity, acidity, alkalinity, nutrient deficiencies)
 - generate crop-specific fertilizer recommendations (base dose + correction)
 - track soil health trends
"""

# store: soil_test_id -> soil record
_soil_tests: Dict[str, Dict[str, Any]] = {}
# index by unit
_soil_by_unit: Dict[str, List[str]] = {}

def _now():
    return datetime.utcnow().isoformat()

# -------------------------------------------------------------
# CREATE / RETRIEVE SOIL TESTS
# -------------------------------------------------------------
def record_soil_test(
    farmer_id: str,
    unit_id: str,
    npk: Dict[str, float],
    ph: float,
    ec: float,
    oc: float,
    micronutrients: Optional[Dict[str, float]] = None,
    texture: Optional[str] = None,
    lab_name: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    sid = f"soil_{uuid.uuid4()}"
    rec = {
        "soil_test_id": sid,
        "farmer_id": farmer_id,
        "unit_id": unit_id,
        "npk": npk,
        "ph": float(ph),
        "ec": float(ec),
        "oc": float(oc),
        "micronutrients": micronutrients or {},
        "texture": texture,
        "lab_name": lab_name,
        "metadata": metadata or {},
        "created_at": _now()
    }
    _soil_tests[sid] = rec
    _soil_by_unit.setdefault(str(unit_id), []).append(sid)
    return rec

def list_soil_tests(unit_id: str) -> List[Dict[str, Any]]:
    ids = _soil_by_unit.get(str(unit_id), [])
    return [ _soil_tests[i] for i in ids ]

def get_latest_soil_test(unit_id: str) -> Optional[Dict[str, Any]]:
    tests = list_soil_tests(unit_id)
    if not tests:
        return None
    return sorted(tests, key=lambda x: x["created_at"], reverse=True)[0]

# -------------------------------------------------------------
# INTERPRETATION MODELS
# -------------------------------------------------------------
def interpret_ph(ph: float) -> str:
    if ph < 5.5:
        return "strongly acidic"
    if 5.5 <= ph < 6.5:
        return "moderately acidic"
    if 6.5 <= ph <= 7.5:
        return "neutral"
    if 7.5 < ph <= 8.5:
        return "alkaline"
    return "strongly alkaline"

def interpret_ec(ec: float) -> str:
    if ec < 0.8:
        return "normal salinity"
    if 0.8 <= ec < 1.5:
        return "moderately saline"
    return "highly saline"

def interpret_oc(oc: float) -> str:
    if oc < 0.5:
        return "low"
    if 0.5 <= oc < 0.75:
        return "medium"
    return "high"

def interpret_nutrient(n: float, p: float, k: float) -> Dict[str, str]:
    def classify(x, low, high):
        if x < low: return "low"
        if x > high: return "high"
        return "medium"
    return {
        "N_status": classify(n, 280, 450),
        "P_status": classify(p, 10, 25),
        "K_status": classify(k, 110, 280),
    }

# -------------------------------------------------------------
# SOIL ISSUE DETECTION
# -------------------------------------------------------------
def detect_soil_issues(test: Dict[str, Any]) -> List[str]:
    issues = []
    ph = test["ph"]
    ec = test["ec"]
    oc = test["oc"]
    if ph < 5.5:
        issues.append("Soil too acidic — apply lime.")
    elif ph > 8.5:
        issues.append("Soil too alkaline — apply gypsum.")
    if ec > 1.5:
        issues.append("High salinity — improve drainage and use tolerant varieties.")
    if oc < 0.5:
        issues.append("Low organic carbon — apply compost / FYM / green manure.")
    npk = test["npk"]
    interp = interpret_nutrient(npk.get("N",0), npk.get("P",0), npk.get("K",0))
    if interp["N_status"] == "low":
        issues.append("Nitrogen deficiency detected.")
    if interp["P_status"] == "low":
        issues.append("Phosphorus deficiency detected.")
    if interp["K_status"] == "low":
        issues.append("Potassium deficiency detected.")
    return issues

# -------------------------------------------------------------
# CROP-SPECIFIC FERTILIZER RECOMMENDATIONS
# -------------------------------------------------------------
DEFAULT_RECOMMENDATIONS = {
    "paddy": {"N": 120, "P": 60, "K": 40},
    "wheat": {"N": 150, "P": 60, "K": 40},
    "maize": {"N": 140, "P": 60, "K": 50},
    "cotton": {"N": 100, "P": 50, "K": 50},
}

def generate_fertilizer_plan(test: Dict[str, Any], crop: str) -> Dict[str, Any]:
    crop = crop.lower()
    base = DEFAULT_RECOMMENDATIONS.get(crop)
    if not base:
        # fallback generic recommendation
        base = {"N": 100, "P": 40, "K": 40}
    npk_status = interpret_nutrient(test["npk"]["N"], test["npk"]["P"], test["npk"]["K"])
    adjust = {"N": 0, "P": 0, "K": 0}
    # reduce or increase NPK relative to soil availability
    if npk_status["N_status"] == "high":
        adjust["N"] = -20
    elif npk_status["N_status"] == "low":
        adjust["N"] = +20
    if npk_status["P_status"] == "high":
        adjust["P"] = -10
    elif npk_status["P_status"] == "low":
        adjust["P"] = +10
    if npk_status["K_status"] == "high":
        adjust["K"] = -10
    elif npk_status["K_status"] == "low":
        adjust["K"] = +10
    plan = {
        "base_recommendation": base,
        "adjustment": adjust,
        "final_recommendation": {
            "N": base["N"] + adjust["N"],
            "P": base["P"] + adjust["P"],
            "K": base["K"] + adjust["K"]
        }
    }
    return plan

# -------------------------------------------------------------
# HIGH-LEVEL INTELLIGENCE SUMMARY
# -------------------------------------------------------------
def soil_intelligence_summary(unit_id: str, crop: str) -> Dict[str, Any]:
    test = get_latest_soil_test(unit_id)
    if not test:
        return {"error": "no_soil_test_found"}
    issues = detect_soil_issues(test)
    plan = generate_fertilizer_plan(test, crop)
    return {
        "unit_id": unit_id,
        "soil_test_id": test["soil_test_id"],
        "ph_interpretation": interpret_ph(test["ph"]),
        "ec_interpretation": interpret_ec(test["ec"]),
        "oc_interpretation": interpret_oc(test["oc"]),
        "npk_status": interpret_nutrient(test["npk"]["N"], test["npk"]["P"], test["npk"]["K"]),
        "issues_detected": issues,
        "fertilizer_plan": plan,
        "timestamp": _now(),
        "original_data": test
    }