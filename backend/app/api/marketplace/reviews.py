# backend/app/api/marketplace/reviews.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.services.marketplace.review_service import (
    add_review,
    get_reviews_for_provider,
    get_reviews_for_equipment,
    list_reviews,
    flag_review,
    unflag_review,
    remove_review,
    mark_review_helpful,
    aggregate_provider_ratings,
    compute_provider_reputation,
    provider_summary
)

router = APIRouter()


class ReviewPayload(BaseModel):
    reviewer_id: str
    provider_id: Optional[str] = None
    equipment_id: Optional[str] = None
    booking_id: Optional[str] = None
    rating: int
    text: Optional[str] = None
    anonymous: Optional[bool] = False


@router.post("/market/review/add")
def api_add_review(req: ReviewPayload):
    res = add_review(
        reviewer_id=req.reviewer_id,
        provider_id=req.provider_id,
        equipment_id=req.equipment_id,
        booking_id=req.booking_id,
        rating=req.rating,
        text=req.text,
        anonymous=req.anonymous
    )
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res


@router.get("/market/reviews/provider/{provider_id}")
def api_get_reviews_provider(provider_id: str, page: Optional[int] = 1, per_page: Optional[int] = 20):
    return get_reviews_for_provider(provider_id, page=page or 1, per_page=per_page or 20)


@router.get("/market/reviews/equipment/{equipment_id}")
def api_get_reviews_equipment(equipment_id: str, page: Optional[int] = 1, per_page: Optional[int] = 20):
    return get_reviews_for_equipment(equipment_id, page=page or 1, per_page=per_page or 20)


@router.get("/market/reviews")
def api_list_reviews(flagged: Optional[bool] = None, page: Optional[int] = 1, per_page: Optional[int] = 50):
    return list_reviews(flagged=flagged, page=page or 1, per_page=per_page or 50)


@router.post("/market/review/{review_id}/flag")
def api_flag_review(review_id: str, flag_reason: Optional[str] = None):
    res = flag_review(review_id, flag_reason=flag_reason)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res


@router.post("/market/review/{review_id}/unflag")
def api_unflag_review(review_id: str):
    res = unflag_review(review_id)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res


@router.delete("/market/review/{review_id}")
def api_remove_review(review_id: str):
    res = remove_review(review_id)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res


@router.post("/market/review/{review_id}/helpful")
def api_mark_helpful(review_id: str):
    res = mark_review_helpful(review_id)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res


@router.get("/market/provider/{provider_id}/ratings")
def api_provider_ratings(provider_id: str):
    return aggregate_provider_ratings(provider_id)


@router.get("/market/provider/{provider_id}/reputation")
def api_provider_reputation(provider_id: str):
    return compute_provider_reputation(provider_id)


@router.get("/market/provider/{provider_id}/summary")
def api_provider_summary(provider_id: str):
    return provider_summary(provider_id)
