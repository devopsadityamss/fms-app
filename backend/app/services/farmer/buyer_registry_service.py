"""
Buyer Registry Service (stub-ready)
-----------------------------------

Allows farmers to maintain a registry of buyers:
 - name, type, region
 - contact details
 - buyer preference attributes (stub)
 - simple rating score
 - purchase summary (stub)

Everything stored in-memory for now.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid


_buyer_store: Dict[str, Dict[str, Any]] = {}


def _new_id() -> str:
    return str(uuid.uuid4())


def _now() -> str:
    return datetime.utcnow().isoformat()


# -------------------------------------------------------------
# CRUD Operations
# -------------------------------------------------------------
def create_buyer(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Expected fields:
     - name
     - buyer_type: wholesaler | retailer | processor | exporter | misc
     - region
     - contact_phone
     - contact_email
     - rating_score: float (0–5)
     - preferences: dict (stub)
     - notes: optional
    """

    buyer_id = _new_id()

    record = {
        "id": buyer_id,
        "name": payload.get("name"),
        "buyer_type": payload.get("buyer_type", "misc"),
        "region": payload.get("region"),
        "contact_phone": payload.get("contact_phone"),
        "contact_email": payload.get("contact_email"),
        "rating_score": payload.get("rating_score", 3.0),
        "preferences": payload.get("preferences", {}),  # stub
        "meta": payload.get("meta", {}),
        "notes": payload.get("notes"),
        "created_at": _now(),
        "updated_at": _now(),
    }

    _buyer_store[buyer_id] = record
    return record


def get_buyer(buyer_id: str) -> Optional[Dict[str, Any]]:
    return _buyer_store.get(buyer_id)


def update_buyer(buyer_id: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    rec = _buyer_store.get(buyer_id)
    if not rec:
        return None

    for key in (
        "name",
        "buyer_type",
        "region",
        "contact_phone",
        "contact_email",
        "rating_score",
        "preferences",
        "meta",
        "notes",
    ):
        if key in payload:
            rec[key] = payload[key]

    rec["updated_at"] = _now()
    _buyer_store[buyer_id] = rec
    return rec


def delete_buyer(buyer_id: str) -> bool:
    if buyer_id in _buyer_store:
        del _buyer_store[buyer_id]
        return True
    return False


# -------------------------------------------------------------
# Listing / Filtering
# -------------------------------------------------------------
def list_buyers(
    region: Optional[str] = None,
    buyer_type: Optional[str] = None,
    min_rating: Optional[float] = None
) -> Dict[str, Any]:

    items = list(_buyer_store.values())

    if region:
        items = [i for i in items if i.get("region") == region]

    if buyer_type:
        items = [i for i in items if i.get("buyer_type") == buyer_type]

    if min_rating is not None:
        items = [i for i in items if float(i.get("rating_score", 0)) >= min_rating]

    return {"count": len(items), "items": items}


# -------------------------------------------------------------
# Simple Scoring Stub
# -------------------------------------------------------------
def compute_buyer_score(buyer_id: str) -> Optional[Dict[str, Any]]:
    """
    Stub logic:
      rating_score + preference match score (fake) + recency bonus (fake)
    """

    rec = _buyer_store.get(buyer_id)
    if not rec:
        return None

    rating = float(rec.get("rating_score", 3.0))

    # preference stub score
    prefs = rec.get("preferences", {})
    pref_score = 0.2 if prefs else 0.1

    # recency stub
    recency_score = 0.3

    final_score = round(rating + pref_score + recency_score, 2)

    return {
        "buyer_id": buyer_id,
        "final_score": final_score,
        "rating": rating,
        "preference_score": pref_score,
        "recency_score": recency_score
    }


def _clear_store():
    _buyer_store.clear()
