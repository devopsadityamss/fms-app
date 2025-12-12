"""
Buyer Preference Modelling (stub-ready)
--------------------------------------

Purpose:
 - Store buyer preference profiles (what buyers prefer: grade, packaging, delivery windows, price sensitivity)
 - Match buyers to farmer units / lots based on a simple preference-similarity heuristic
 - Provide CRUD for preference profiles and lightweight recommendation API
 - In-memory store for now; replace with ML/embedding models later

Data model (in-memory record keys):
 - id
 - buyer_id
 - preferred_grades: list (e.g. ["A","B"])
 - packaging_types: list (e.g. ["bulk","crate"])
 - preferred_delivery_windows: list of strings (e.g. ["morning","weekend"])
 - price_sensitivity: float (0–1, 1 = very sensitive to price)
 - quality_priority: float (0–1, 1 = very quality focused)
 - region_preference: list of region strings
 - last_updated
 - notes
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid
import math

_pref_store: Dict[str, Dict[str, Any]] = {}


def _new_id() -> str:
    return str(uuid.uuid4())


def _now() -> str:
    return datetime.utcnow().isoformat()


# -------------------------
# CRUD
# -------------------------
def create_preference(payload: Dict[str, Any]) -> Dict[str, Any]:
    pref_id = _new_id()
    record = {
        "id": pref_id,
        "buyer_id": payload.get("buyer_id"),
        "preferred_grades": payload.get("preferred_grades", []),
        "packaging_types": payload.get("packaging_types", []),
        "preferred_delivery_windows": payload.get("preferred_delivery_windows", []),
        "price_sensitivity": float(payload.get("price_sensitivity", 0.5)),
        "quality_priority": float(payload.get("quality_priority", 0.5)),
        "region_preference": payload.get("region_preference", []),
        "notes": payload.get("notes"),
        "created_at": _now(),
        "last_updated": _now(),
    }
    _pref_store[pref_id] = record
    return record


def get_preference(pref_id: str) -> Optional[Dict[str, Any]]:
    return _pref_store.get(pref_id)


def update_preference(pref_id: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    rec = _pref_store.get(pref_id)
    if not rec:
        return None

    for k in (
        "preferred_grades",
        "packaging_types",
        "preferred_delivery_windows",
        "price_sensitivity",
        "quality_priority",
        "region_preference",
        "notes",
    ):
        if k in payload:
            # enforce sensible types
            if k in ("price_sensitivity", "quality_priority"):
                rec[k] = float(payload[k])
            else:
                rec[k] = payload[k]
    rec["last_updated"] = _now()
    _pref_store[pref_id] = rec
    return rec


def delete_preference(pref_id: str) -> bool:
    if pref_id in _pref_store:
        del _pref_store[pref_id]
        return True
    return False


def list_preferences(buyer_id: Optional[str] = None) -> Dict[str, Any]:
    items = list(_pref_store.values())
    if buyer_id:
        items = [i for i in items if i.get("buyer_id") == buyer_id]
    return {"count": len(items), "items": items}


# -------------------------
# Simple matching heuristic / recommender (stub)
# -------------------------
def _jaccard(a: List[str], b: List[str]) -> float:
    if not a and not b:
        return 0.0
    set_a, set_b = set(a or []), set(b or [])
    inter = set_a.intersection(set_b)
    union = set_a.union(set_b)
    return float(len(inter)) / (len(union) if union else 1)


def score_match(pref: Dict[str, Any], unit_profile: Dict[str, Any]) -> float:
    """
    Compute a 0..1 score indicating how well a buyer preference matches a unit/profile.
    unit_profile may contain:
      - grade (string)
      - packaging (string)
      - delivery_window (string)
      - region (string)
      - expected_price (float)
      - quality_metric (0..1)
    Weighting (stub):
      - grade & packaging via Jaccard (0.4)
      - delivery & region (0.2)
      - price sensitivity check (0.2)
      - quality priority match (0.2)
    """
    score = 0.0

    # grade + packaging
    grade_match = _jaccard(pref.get("preferred_grades", []), [unit_profile.get("grade")] if unit_profile.get("grade") else [])
    pack_match = _jaccard(pref.get("packaging_types", []), [unit_profile.get("packaging")] if unit_profile.get("packaging") else [])
    score += 0.4 * ((grade_match + pack_match) / 2.0)

    # delivery + region
    delivery_match = 1.0 if unit_profile.get("delivery_window") in pref.get("preferred_delivery_windows", []) else 0.0
    region_match = 1.0 if unit_profile.get("region") in pref.get("region_preference", []) else 0.0
    score += 0.2 * ((delivery_match + region_match) / 2.0)

    # price sensitivity
    expected_price = unit_profile.get("expected_price")
    if expected_price is not None:
        # if buyer is price sensitive and expected_price is high, penalize
        price_sens = pref.get("price_sensitivity", 0.5)
        # normalize expected_price roughly into 0..1 using a soft heuristic (stub)
        price_norm = 1.0 / (1.0 + math.exp((expected_price - 30) / 10))  # higher price => lower norm
        price_component = 1.0 - (price_sens * (1.0 - price_norm))
        score += 0.2 * price_component
    else:
        score += 0.2 * 0.5

    # quality priority
    quality_priority = pref.get("quality_priority", 0.5)
    unit_quality = unit_profile.get("quality_metric", 0.5)
    quality_component = 1.0 - abs(quality_priority - unit_quality)  # closer is better
    score += 0.2 * quality_component

    return round(max(0.0, min(1.0, score)), 3)


def recommend_buyers_for_unit(unit_profile: Dict[str, Any], top_n: int = 5) -> Dict[str, Any]:
    """
    Returns top-N buyer preferences ranked by match score.
    unit_profile: same shape as used in score_match
    """
    all_prefs = list(_pref_store.values())
    scored = []
    for p in all_prefs:
        s = score_match(p, unit_profile)
        scored.append({"pref_id": p["id"], "buyer_id": p.get("buyer_id"), "score": s, "preference": p})
    scored.sort(key=lambda x: x["score"], reverse=True)
    return {"count": len(scored), "items": scored[:top_n]}


def _clear_store():
    _pref_store.clear()
