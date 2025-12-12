# backend/app/services/marketplace/trade_service.py

from datetime import datetime
from threading import Lock
from typing import Dict, Any, List, Optional
import uuid

"""
Marketplace Trading Service (in-memory)

Concepts:
 - listings: farmer lists crop lots for sale
 - bids/offers: traders (or other farmers) place offers on listings
 - orders: when seller accepts a bid or buyer buys at listing price, an order is created
 - simple statuses: listing.active, bid.status (open/accepted/rejected), order.status (created/confirmed/completed/cancelled)
 - integration points: payments/escrow, logistics, notifications
"""

_lock = Lock()

# listing_id -> listing
_listings: Dict[str, Dict[str, Any]] = {}

# bid_id -> bid
_bids: Dict[str, Dict[str, Any]] = {}

# order_id -> order
_orders: Dict[str, Dict[str, Any]] = {}

# basic search index keys (by crop)
_index_by_crop: Dict[str, List[str]] = {}


def _now_iso() -> str:
    return datetime.utcnow().isoformat()


# -------------------------
# Create / manage listings
# -------------------------
def create_listing(
    farmer_id: str,
    crop: str,
    variety: Optional[str],
    quantity_kg: float,
    min_price_per_kg: float,
    location: Optional[str] = None,
    harvest_date_iso: Optional[str] = None,
    expires_at_iso: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    lid = f"list_{uuid.uuid4()}"
    rec = {
        "listing_id": lid,
        "farmer_id": farmer_id,
        "crop": crop.lower(),
        "variety": variety,
        "quantity_kg": float(quantity_kg),
        "available_kg": float(quantity_kg),
        "min_price_per_kg": float(min_price_per_kg),
        "location": location,
        "harvest_date_iso": harvest_date_iso,
        "expires_at_iso": expires_at_iso,
        "metadata": metadata or {},
        "active": True,
        "created_at": _now_iso(),
        "updated_at": _now_iso()
    }
    with _lock:
        _listings[lid] = rec
        _index_by_crop.setdefault(rec["crop"], []).append(lid)
    return rec


def update_listing(listing_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    with _lock:
        l = _listings.get(listing_id)
        if not l:
            return {"error": "listing_not_found"}
        l.update(updates)
        l["updated_at"] = _now_iso()
        _listings[listing_id] = l
    return l


def get_listing(listing_id: str) -> Dict[str, Any]:
    return _listings.get(listing_id, {})


def search_listings(crop: Optional[str] = None, min_price: Optional[float] = None, max_price: Optional[float] = None, location: Optional[str] = None, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
    with _lock:
        ids = []
        if crop:
            ids = list(_index_by_crop.get(crop.lower(), []))
        else:
            ids = list(_listings.keys())
        results = []
        for lid in ids:
            l = _listings.get(lid)
            if not l or not l.get("active"):
                continue
            if min_price is not None and l.get("min_price_per_kg", 0) < min_price:
                # listing min price lower than search min => still fine (buyer wants price <= max). We'll filter by price range differently:
                pass
            if max_price is not None and l.get("min_price_per_kg", 0) > max_price:
                continue
            if location and l.get("location") and location.lower() not in l.get("location","").lower():
                continue
            results.append(l)
    total = len(results)
    start = (page - 1) * per_page
    return {"total": total, "page": page, "per_page": per_page, "listings": results[start:start+per_page]}


# -------------------------
# Bids / Offers (by buyers/traders)
# -------------------------
def place_bid(
    bidder_id: str,
    listing_id: str,
    offered_price_per_kg: float,
    quantity_kg: float,
    expire_at_iso: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    listing = _listings.get(listing_id)
    if not listing or not listing.get("active"):
        return {"error": "listing_not_found_or_inactive"}
    if quantity_kg <= 0 or quantity_kg > listing.get("available_kg", 0):
        return {"error": "invalid_quantity"}

    bid_id = f"bid_{uuid.uuid4()}"
    rec = {
        "bid_id": bid_id,
        "listing_id": listing_id,
        "bidder_id": bidder_id,
        "offered_price_per_kg": float(offered_price_per_kg),
        "quantity_kg": float(quantity_kg),
        "expire_at_iso": expire_at_iso,
        "status": "open",
        "metadata": metadata or {},
        "created_at": _now_iso()
    }
    with _lock:
        _bids[bid_id] = rec
    return rec


def list_bids_for_listing(listing_id: str) -> List[Dict[str, Any]]:
    with _lock:
        items = [b for b in _bids.values() if b.get("listing_id") == listing_id]
    # sort by offered price desc (best offers first)
    items = sorted(items, key=lambda x: x.get("offered_price_per_kg", 0), reverse=True)
    return items


def respond_to_bid(listing_id: str, bid_id: str, seller_id: str, accept: bool) -> Dict[str, Any]:
    with _lock:
        l = _listings.get(listing_id)
        b = _bids.get(bid_id)
        if not l or not b:
            return {"error": "not_found"}
        if l.get("farmer_id") != seller_id:
            return {"error": "not_authorized"}
        if b.get("status") != "open":
            return {"error": "invalid_status"}

        if accept:
            # mark bid accepted, create order
            b["status"] = "accepted"
            order = _create_order_from_bid(b)
            _bids[bid_id] = b
            return {"status": "accepted", "bid": b, "order": order}
        else:
            b["status"] = "rejected"
            _bids[bid_id] = b
            return {"status": "rejected", "bid": b}


# -------------------------
# Orders (matching & direct buy)
# -------------------------
def _create_order_from_bid(bid: Dict[str, Any]) -> Dict[str, Any]:
    order_id = f"order_{uuid.uuid4()}"
    listing_id = bid.get("listing_id")
    l = _listings.get(listing_id)
    if not l:
        return {"error": "listing_not_found"}
    quantity = min(float(bid.get("quantity_kg", 0)), float(l.get("available_kg", 0)))
    total_amount = round(quantity * float(bid.get("offered_price_per_kg", 0)), 2)
    order = {
        "order_id": order_id,
        "listing_id": listing_id,
        "buyer_id": bid.get("bidder_id"),
        "seller_id": l.get("farmer_id"),
        "quantity_kg": quantity,
        "price_per_kg": float(bid.get("offered_price_per_kg", 0)),
        "total_amount": total_amount,
        "status": "created",
        "created_at": _now_iso(),
        "metadata": {}
    }
    # reduce available_kg on listing
    l["available_kg"] = max(0.0, float(l.get("available_kg",0)) - quantity)
    if l["available_kg"] <= 0:
        l["active"] = False
    _listings[listing_id] = l
    _orders[order_id] = order
    return order


def buy_now(listing_id: str, buyer_id: str, quantity_kg: float) -> Dict[str, Any]:
    l = _listings.get(listing_id)
    if not l or not l.get("active"):
        return {"error": "listing_not_found_or_inactive"}
    if quantity_kg <= 0 or quantity_kg > l.get("available_kg",0):
        return {"error": "invalid_quantity"}
    # buyer agrees to listing min_price_per_kg
    total = round(quantity_kg * float(l.get("min_price_per_kg",0)), 2)
    order_id = f"order_{uuid.uuid4()}"
    order = {
        "order_id": order_id,
        "listing_id": listing_id,
        "buyer_id": buyer_id,
        "seller_id": l.get("farmer_id"),
        "quantity_kg": float(quantity_kg),
        "price_per_kg": float(l.get("min_price_per_kg")),
        "total_amount": total,
        "status": "created",
        "created_at": _now_iso(),
        "metadata": {"type": "buy_now"}
    }
    # update listing
    l["available_kg"] = max(0.0, float(l.get("available_kg",0)) - quantity_kg)
    if l["available_kg"] <= 0:
        l["active"] = False
    with _lock:
        _listings[listing_id] = l
        _orders[order_id] = order
    return order


def get_order(order_id: str) -> Dict[str, Any]:
    return _orders.get(order_id, {})


def confirm_order(order_id: str, actor_id: str) -> Dict[str, Any]:
    """
    Buyer or seller confirms receipt/collection. If seller confirms pickup, order moves to confirmed.
    For simplicity we allow either party to mark confirmed; real flow would require receipts/logistics.
    """
    with _lock:
        o = _orders.get(order_id)
        if not o:
            return {"error": "order_not_found"}
        if o.get("status") not in ["created"]:
            return {"error": "invalid_status"}
        o["status"] = "confirmed"
        o["confirmed_by"] = actor_id
        o["confirmed_at"] = _now_iso()
        _orders[order_id] = o
    return {"status": "confirmed", "order": o}


def complete_order(order_id: str, actor_id: str) -> Dict[str, Any]:
    with _lock:
        o = _orders.get(order_id)
        if not o:
            return {"error": "order_not_found"}
        if o.get("status") not in ["confirmed"]:
            return {"error": "invalid_status"}
        o["status"] = "completed"
        o["completed_by"] = actor_id
        o["completed_at"] = _now_iso()
        _orders[order_id] = o
    return {"status": "completed", "order": o}


def cancel_order(order_id: str, actor_id: str) -> Dict[str, Any]:
    with _lock:
        o = _orders.get(order_id)
        if not o:
            return {"error": "order_not_found"}
        if o.get("status") in ["completed", "cancelled"]:
            return {"error": "invalid_status"}
        o["status"] = "cancelled"
        o["cancelled_by"] = actor_id
        o["cancelled_at"] = _now_iso()
        # on cancel, restore available_kg
        lid = o.get("listing_id")
        if lid and lid in _listings:
            l = _listings[lid]
            l["available_kg"] = float(l.get("available_kg",0)) + float(o.get("quantity_kg",0))
            l["active"] = True
            _listings[lid] = l
        _orders[order_id] = o
    return {"status": "cancelled", "order": o}


# -------------------------
# Queries
# -------------------------
def list_orders_for_user(user_id: str, role: Optional[str] = None) -> List[Dict[str, Any]]:
    with _lock:
        if role == "seller":
            return [o for o in _orders.values() if o.get("seller_id") == user_id]
        elif role == "buyer":
            return [o for o in _orders.values() if o.get("buyer_id") == user_id]
        else:
            return [o for o in _orders.values() if o.get("buyer_id") == user_id or o.get("seller_id") == user_id]


def list_listings_for_farmer(farmer_id: str) -> List[Dict[str, Any]]:
    with _lock:
        return [l for l in _listings.values() if l.get("farmer_id") == farmer_id]
