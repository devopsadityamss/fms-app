# backend/app/services/marketplace/review_service.py

from datetime import datetime
from threading import Lock
from typing import Dict, Any, List, Optional
import uuid
import statistics

"""
Marketplace Ratings & Reviews (in-memory)

Stores:
 - _review_store: review_id -> review record
 - _provider_reviews_index: provider_id -> [review_ids]
 - _equipment_reviews_index: equipment_id -> [review_ids]

Basic rules:
 - rating is 1..5
 - reviews optionally linked to booking_id (preferred)
 - best-effort: if booking_id provided, check booking is 'completed' before accepting
 - moderation: reviews can be flagged and removed (flag_reason)
 - reputation: computed as weighted average, recent reviews get slightly higher weight
"""

_lock = Lock()
_review_store: Dict[str, Dict[str, Any]] = {}
_provider_index: Dict[str, List[str]] = {}
_equipment_index: Dict[str, List[str]] = {}

# For booking check (best-effort import)
try:
    from app.services.marketplace.equipment_service import get_booking
except Exception:
    def get_booking(booking_id: str) -> Dict[str, Any]:
        return {}

# -------------------------
# Helpers
# -------------------------
def _now_iso() -> str:
    return datetime.utcnow().isoformat()


# -------------------------
# Create a review
# -------------------------
def add_review(
    reviewer_id: str,
    provider_id: Optional[str] = None,
    equipment_id: Optional[str] = None,
    booking_id: Optional[str] = None,
    rating: int = 5,
    text: Optional[str] = None,
    anonymous: bool = False
) -> Dict[str, Any]:
    """
    Add a review. If booking_id provided, we check booking exists and is completed.
    rating: integer 1..5
    """
    if rating is None or not (1 <= int(rating) <= 5):
        return {"error": "invalid_rating"}

    # if booking provided, check completion
    if booking_id:
        b = get_booking(booking_id) or {}
        status = b.get("status")
        if status != "completed":
            # reject review if booking not completed
            return {"error": "booking_not_completed_or_invalid", "booking_status": status}

        # auto-set provider_id and equipment_id from booking if missing
        provider_id = provider_id or b.get("provider_id")
        equipment_id = equipment_id or b.get("equipment_id")

    if not provider_id and not equipment_id:
        return {"error": "must_provide_provider_or_equipment_or_valid_booking"}

    rid = f"rev_{uuid.uuid4()}"
    rec = {
        "review_id": rid,
        "reviewer_id": None if anonymous else reviewer_id,
        "provider_id": provider_id,
        "equipment_id": equipment_id,
        "booking_id": booking_id,
        "rating": int(rating),
        "text": text or "",
        "flagged": False,
        "flag_reason": None,
        "created_at": _now_iso(),
        "helpful_count": 0
    }
    with _lock:
        _review_store[rid] = rec
        if provider_id:
            _provider_index.setdefault(provider_id, []).append(rid)
        if equipment_id:
            _equipment_index.setdefault(equipment_id, []).append(rid)
    return rec


# -------------------------
# Get reviews
# -------------------------
def get_reviews_for_provider(provider_id: str, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
    with _lock:
        ids = list(_provider_index.get(provider_id, []))
    total = len(ids)
    start = (page - 1) * per_page
    page_ids = ids[start:start + per_page]
    reviews = [ _review_store.get(i) for i in page_ids ]
    return {"provider_id": provider_id, "total": total, "page": page, "per_page": per_page, "reviews": reviews}


def get_reviews_for_equipment(equipment_id: str, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
    with _lock:
        ids = list(_equipment_index.get(equipment_id, []))
    total = len(ids)
    start = (page - 1) * per_page
    page_ids = ids[start:start + per_page]
    reviews = [ _review_store.get(i) for i in page_ids ]
    return {"equipment_id": equipment_id, "total": total, "page": page, "per_page": per_page, "reviews": reviews}


def list_reviews(flagged: Optional[bool] = None, page: int = 1, per_page: int = 50) -> Dict[str, Any]:
    with _lock:
        items = list(_review_store.values())
    if flagged is not None:
        items = [r for r in items if r.get("flagged") == bool(flagged)]
    items = sorted(items, key=lambda x: x.get("created_at"), reverse=True)
    start = (page - 1) * per_page
    return {"total": len(items), "page": page, "per_page": per_page, "reviews": items[start:start + per_page]}


# -------------------------
# Moderation: flag / unflag / remove
# -------------------------
def flag_review(review_id: str, flag_reason: Optional[str] = None) -> Dict[str, Any]:
    with _lock:
        r = _review_store.get(review_id)
        if not r:
            return {"error": "not_found"}
        r["flagged"] = True
        r["flag_reason"] = flag_reason
        r["flagged_at"] = _now_iso()
        _review_store[review_id] = r
    return {"status": "flagged", "review": r}


def unflag_review(review_id: str) -> Dict[str, Any]:
    with _lock:
        r = _review_store.get(review_id)
        if not r:
            return {"error": "not_found"}
        r["flagged"] = False
        r["flag_reason"] = None
        _review_store[review_id] = r
    return {"status": "unflagged", "review": r}


def remove_review(review_id: str) -> Dict[str, Any]:
    with _lock:
        r = _review_store.pop(review_id, None)
        if not r:
            return {"error": "not_found"}
        pid = r.get("provider_id")
        eid = r.get("equipment_id")
        if pid and pid in _provider_index:
            try: _provider_index[pid].remove(review_id)
            except Exception: pass
        if eid and eid in _equipment_index:
            try: _equipment_index[eid].remove(review_id)
            except Exception: pass
    return {"status": "removed", "review_id": review_id}


# -------------------------
# Helpful vote
# -------------------------
def mark_review_helpful(review_id: str) -> Dict[str, Any]:
    with _lock:
        r = _review_store.get(review_id)
        if not r:
            return {"error": "not_found"}
        r["helpful_count"] = int(r.get("helpful_count", 0)) + 1
        _review_store[review_id] = r
    return {"status": "marked_helpful", "review": r}


# -------------------------
# Aggregation & reputation
# -------------------------
def aggregate_provider_ratings(provider_id: str) -> Dict[str, Any]:
    with _lock:
        ids = list(_provider_index.get(provider_id, []))
        recs = [ _review_store.get(i) for i in ids if _review_store.get(i) and not _review_store.get(i).get("flagged") ]
    ratings = [ r["rating"] for r in recs if r and r.get("rating") is not None ]
    count = len(ratings)
    if count == 0:
        return {"provider_id": provider_id, "count": 0, "average_rating": None, "distribution": {}}
    avg = round(statistics.mean(ratings), 2)
    dist = {}
    for star in range(1,6):
        dist[str(star)] = sum(1 for v in ratings if v == star)
    return {"provider_id": provider_id, "count": count, "average_rating": avg, "distribution": dist}


def compute_provider_reputation(provider_id: str) -> Dict[str, Any]:
    """
    A simple reputation score:
      - base on average rating (1..5 mapped to 0..100)
      - weight recent reviews more: recency factor = exp(-age_days/180)
      - helpful_count adds small boost
    """
    with _lock:
        ids = list(_provider_index.get(provider_id, []))
        recs = [ _review_store.get(i) for i in ids if _review_store.get(i) ]
    if not recs:
        return {"provider_id": provider_id, "reputation_score": None, "details": {}}

    weighted_sum = 0.0
    total_w = 0.0
    now = datetime.utcnow()
    for r in recs:
        if r.get("flagged"):
            continue
        rating = float(r.get("rating", 0))
        created = r.get("created_at")
        try:
            age_days = (now - datetime.fromisoformat(created)).days
        except Exception:
            age_days = 365
        recency_w = 1.0 / (1.0 + age_days / 180.0)  # recent ~1, older -> smaller
        helpful_w = 1.0 + (min(int(r.get("helpful_count",0)), 10) * 0.05)  # up to +50% weight
        w = recency_w * helpful_w
        weighted_sum += rating * w
        total_w += w

    if total_w == 0:
        return {"provider_id": provider_id, "reputation_score": None, "details": {}}
    avg_weighted_rating = weighted_sum / total_w
    # map 1..5 -> 0..100
    score = round(((avg_weighted_rating - 1.0) / 4.0) * 100.0, 2)
    return {"provider_id": provider_id, "reputation_score": score, "avg_weighted_rating": round(avg_weighted_rating, 2), "review_count": len(recs)}


# -------------------------
# Utility: provider quick summary
# -------------------------
def provider_summary(provider_id: str) -> Dict[str, Any]:
    agg = aggregate_provider_ratings(provider_id)
    rep = compute_provider_reputation(provider_id)
    return {"provider_id": provider_id, "ratings": agg, "reputation": rep}
