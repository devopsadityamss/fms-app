# backend/app/api/marketplace/trade.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.services.marketplace.trade_service import (
    create_listing,
    update_listing,
    get_listing,
    search_listings,
    place_bid,
    list_bids_for_listing,
    respond_to_bid,
    buy_now,
    get_order,
    confirm_order,
    complete_order,
    cancel_order,
    list_orders_for_user,
    list_listings_for_farmer
)

router = APIRouter()


# ---------- Payloads ----------
class ListingPayload(BaseModel):
    farmer_id: str
    crop: str
    variety: Optional[str] = None
    quantity_kg: float
    min_price_per_kg: float
    location: Optional[str] = None
    harvest_date_iso: Optional[str] = None
    expires_at_iso: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ListingUpdatePayload(BaseModel):
    listing_id: str
    updates: Dict[str, Any]


class BidPayload(BaseModel):
    bidder_id: str
    listing_id: str
    offered_price_per_kg: float
    quantity_kg: float
    expire_at_iso: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class BuyNowPayload(BaseModel):
    listing_id: str
    buyer_id: str
    quantity_kg: float


class OrderActionPayload(BaseModel):
    order_id: str
    actor_id: str


# ---------- Endpoints ----------
@router.post("/market/trade/listing/create")
def api_create_listing(req: ListingPayload):
    return create_listing(
        req.farmer_id, req.crop, req.variety, req.quantity_kg, req.min_price_per_kg,
        location=req.location, harvest_date_iso=req.harvest_date_iso, expires_at_iso=req.expires_at_iso, metadata=req.metadata
    )


@router.post("/market/trade/listing/update")
def api_update_listing(req: ListingUpdatePayload):
    res = update_listing(req.listing_id, req.updates)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res


@router.get("/market/trade/listing/{listing_id}")
def api_get_listing(listing_id: str):
    res = get_listing(listing_id)
    if not res:
        raise HTTPException(status_code=404, detail="listing_not_found")
    return res


@router.get("/market/trade/search")
def api_search_listings(crop: Optional[str] = None, min_price: Optional[float] = None, max_price: Optional[float] = None, location: Optional[str] = None, page: Optional[int] = 1, per_page: Optional[int] = 20):
    return search_listings(crop=crop, min_price=min_price, max_price=max_price, location=location, page=page or 1, per_page=per_page or 20)


@router.post("/market/trade/bid")
def api_place_bid(req: BidPayload):
    res = place_bid(req.bidder_id, req.listing_id, req.offered_price_per_kg, req.quantity_kg, expire_at_iso=req.expire_at_iso, metadata=req.metadata)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res


@router.get("/market/trade/listing/{listing_id}/bids")
def api_list_bids(listing_id: str):
    return list_bids_for_listing(listing_id)


@router.post("/market/trade/listing/{listing_id}/bid/{bid_id}/respond")
def api_respond_to_bid(listing_id: str, bid_id: str, seller_id: str, accept: bool):
    res = respond_to_bid(listing_id, bid_id, seller_id, accept)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res


@router.post("/market/trade/listing/{listing_id}/buy")
def api_buy_now(req: BuyNowPayload):
    res = buy_now(req.listing_id, req.buyer_id, req.quantity_kg)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res


@router.get("/market/trade/order/{order_id}")
def api_get_order(order_id: str):
    res = get_order(order_id)
    if not res:
        raise HTTPException(status_code=404, detail="order_not_found")
    return res


@router.post("/market/trade/order/confirm")
def api_confirm_order(req: OrderActionPayload):
    res = confirm_order(req.order_id, req.actor_id)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res


@router.post("/market/trade/order/complete")
def api_complete_order(req: OrderActionPayload):
    res = complete_order(req.order_id, req.actor_id)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res


@router.post("/market/trade/order/cancel")
def api_cancel_order(req: OrderActionPayload):
    res = cancel_order(req.order_id, req.actor_id)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res


@router.get("/market/trade/orders/user/{user_id}")
def api_list_orders_user(user_id: str, role: Optional[str] = None):
    return list_orders_for_user(user_id, role=role)


@router.get("/market/trade/listings/farmer/{farmer_id}")
def api_listings_for_farmer(farmer_id: str):
    return list_listings_for_farmer(farmer_id)
