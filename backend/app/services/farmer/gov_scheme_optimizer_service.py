"""
Government Scheme Optimization Engine (stub-ready)
--------------------------------------------------

Purpose:
 - Store government schemes with eligibility rules (stub)
 - Match farmer profile (unit-specific or global) to schemes
 - Score relevance
 - Estimate benefits (stub)
 - Provide recommendations + required document list

This is in-memory and designed for later integration with:
 - Real government databases
 - Mobile registration flows
 - Recommendation engine
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

_scheme_store: Dict[str, Dict[str, Any]] = {}


def _now() -> str:
    return datetime.utcnow().isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


# -------------------------------------------------------------
# CRUD: Add or modify schemes
# -------------------------------------------------------------
def add_scheme(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Expected fields:
     - name
     - category: subsidy | insurance | loan | training | certification
     - region (list or string)
     - crop_types (list)
     - eligibility: dict of conditions
         e.g. {"max_land_holding_ha": 2, "requires_irrigation": True}
     - estimated_benefit (stub)
     - required_documents (list)
    """

    sid = _new_id()
    rec = {
        "id": sid,
        "name": payload.get("name"),
        "category": payload.get("category", "misc"),
        "regions": payload.get("regions", []),
        "crop_types": payload.get("crop_types", []),
        "eligibility": payload.get("eligibility", {}),
        "estimated_benefit": payload.get("estimated_benefit", {}),
        "required_documents": payload.get("required_documents", []),
        "created_at": _now(),
        "updated_at": _now(),
        "meta": payload.get("meta", {})
    }
    _scheme_store[sid] = rec
    return rec


def update_scheme(scheme_id: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    rec = _scheme_store.get(scheme_id)
    if not rec:
        return None

    for k in (
        "name", "category", "regions", "crop_types", "eligibility",
        "estimated_benefit", "required_documents", "meta"
    ):
        if k in payload:
            rec[k] = payload[k]

    rec["updated_at"] = _now()
    return rec


def delete_scheme(scheme_id: str) -> bool:
    if scheme_id in _scheme_store:
        del _scheme_store[scheme_id]
        return True
    return False


def list_schemes(category: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    items = list(_scheme_store.values())
    if category:
        items = [i for i in items if i.get("category") == category]
    if region:
        items = [i for i in items if region in i.get("regions", [])]
    return {"count": len(items), "items": items}


# -------------------------------------------------------------
# MATCHING ENGINE
# -------------------------------------------------------------
def _score_scheme(scheme: Dict[str, Any], farmer: Dict[str, Any]) -> float:
    """
    farmer dict expected fields:
     - crop_type
     - region
     - land_holding_ha
     - irrigation: drip/sprinkler/flood/rainfed
     - organic_certified: bool
    """

    score = 0.0
    elig = scheme.get("eligibility", {})

    # crop match
    if farmer.get("crop_type") in scheme.get("crop_types", []):
        score += 0.4

    # region match
    if farmer.get("region") in scheme.get("regions", []):
        score += 0.2

    # land holding condition
    max_lh = elig.get("max_land_holding_ha")
    if max_lh is None or farmer.get("land_holding_ha", 999) <= max_lh:
        score += 0.1

    # irrigation requirement
    if elig.get("requires_irrigation") and farmer.get("irrigation") != "rainfed":
        score += 0.1
    elif not elig.get("requires_irrigation"):
        score += 0.05

    # organic requirement
    if elig.get("organic_required") and farmer.get("organic_certified"):
        score += 0.1
    elif not elig.get("organic_required"):
        score += 0.05

    return round(score, 3)


def match_schemes(farmer_profile: Dict[str, Any], top_n: int = 5) -> Dict[str, Any]:
    """
    Returns a ranked list of schemes based on matching score.
    """
    results = []
    for s in _scheme_store.values():
        sc = _score_scheme(s, farmer_profile)
        if sc > 0:
            results.append({
                "scheme_id": s["id"],
                "name": s["name"],
                "score": sc,
                "estimated_benefit": s.get("estimated_benefit"),
                "required_documents": s.get("required_documents"),
                "category": s.get("category")
            })

    results.sort(key=lambda x: x["score"], reverse=True)
    return {"count": len(results), "items": results[:top_n]}


def _clear_store():
    _scheme_store.clear()
