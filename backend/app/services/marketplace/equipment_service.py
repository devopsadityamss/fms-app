# backend/app/services/marketplace/equipment_service.py

from datetime import datetime, timedelta, date
from threading import Lock
from typing import Dict, Any, List, Optional
import uuid

"""
Equipment Marketplace & Booking (in-memory)

Stores:
 - _equipment_store: equipment_id -> equipment metadata (owned by provider_id)
 - _booking_store: booking_id -> booking record (farmer_id, equipment_id, start_date, end_date, status)
 - _provider_store: provider_id -> provider metadata (simple registry)

Booking statuses:
 - pending (created by farmer)
 - approved (provider accepted)
 - rejected
 - cancelled
 - completed
"""

_equip_lock = Lock()
_equipment_store: Dict[str, Dict[str, Any]] = {}

_book_lock = Lock()
_booking_store: Dict[str, Dict[str, Any]] = {}

_provider_lock = Lock()
_provider_store: Dict[str, Dict[str, Any]] = {}

# -----------------------
# Provider registry
# -----------------------
def register_provider(provider_id: Optional[str], name: str, contact: Optional[str] = None) -> Dict[str, Any]:
    pid = provider_id or f"prov_{uuid.uuid4()}"
    rec = {"provider_id": pid, "name": name, "contact": contact, "registered_at": datetime.utcnow().isoformat()}
    with _provider_lock:
        _provider_store[pid] = rec
    return rec


def get_provider(provider_id: str) -> Dict[str, Any]:
    return _provider_store.get(provider_id, {})


# -----------------------
# Equipment CRUD / Listing
# -----------------------
def register_equipment(
    provider_id: str,
    title: str,
    description: str,
    daily_rate: float,
    available_from_iso: Optional[str] = None,
    available_to_iso: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    eid = f"equip_{uuid.uuid4()}"
    rec = {
        "equipment_id": eid,
        "provider_id": provider_id,
        "title": title,
        "description": description,
        "daily_rate": float(daily_rate),
        "available_from_iso": available_from_iso,
        "available_to_iso": available_to_iso,
        "metadata": metadata or {},
        "created_at": datetime.utcnow().isoformat(),
        "active": True
    }
    with _equip_lock:
        _equipment_store[eid] = rec
    return rec


def update_equipment(equipment_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    with _equip_lock:
        rec = _equipment_store.get(equipment_id)
        if not rec:
            return {"error": "not_found"}
        rec.update(updates)
        rec["updated_at"] = datetime.utcnow().isoformat()
        _equipment_store[equipment_id] = rec
    return rec


def list_equipment(provider_id: Optional[str] = None, active_only: bool = True) -> List[Dict[str, Any]]:
    with _equip_lock:
        items = list(_equipment_store.values())
    if provider_id:
        items = [i for i in items if i.get("provider_id") == provider_id]
    if active_only:
        items = [i for i in items if i.get("active", True)]
    return items


def get_equipment(equipment_id: str) -> Dict[str, Any]:
    return _equipment_store.get(equipment_id, {})


# -----------------------
# Availability helpers
# -----------------------
def _parse_date_iso(d: Optional[str]) -> Optional[date]:
    if not d:
        return None
    try:
        return datetime.fromisoformat(d).date()
    except Exception:
        try:
            return datetime.strptime(d, "%Y-%m-%d").date()
        except Exception:
            return None


def check_equipment_availability(equipment_id: str, start_iso: str, end_iso: str) -> Dict[str, Any]:
    """
    Returns whether the equipment is available for the requested window (inclusive).
    Basic rule: no overlapping approved or pending bookings for the period.
    """
    start = _parse_date_iso(start_iso)
    end = _parse_date_iso(end_iso)
    if not start or not end or end < start:
        return {"error": "invalid_dates"}

    with _book_lock:
        for b in _booking_store.values():
            if b["equipment_id"] != equipment_id:
                continue
            if b["status"] in ["rejected", "cancelled", "completed"]:
                continue
            # compare date ranges (overlap)
            bstart = _parse_date_iso(b["start_date"])
            bend = _parse_date_iso(b["end_date"])
            if not bstart or not bend:
                continue
            if not (end < bstart or start > bend):
                # overlap
                return {"available": False, "conflict_booking": b}
    return {"available": True}


# -----------------------
# Booking lifecycle
# -----------------------
def create_booking(farmer_id: str, equipment_id: str, start_iso: str, end_iso: str, notes: Optional[str] = None) -> Dict[str, Any]:
    # check equipment exists
    equip = get_equipment(equipment_id)
    if not equip:
        return {"error": "equipment_not_found"}

    # availability
    avail = check_equipment_availability(equipment_id, start_iso, end_iso)
    if not avail.get("available"):
        return {"error": "not_available", "conflict": avail.get("conflict_booking")}

    # compute price = daily_rate * days
    start = _parse_date_iso(start_iso)
    end = _parse_date_iso(end_iso)
    days = (end - start).days + 1
    price = round(equip.get("daily_rate", 0.0) * max(1, days), 2)

    bid = f"booking_{uuid.uuid4()}"
    rec = {
        "booking_id": bid,
        "equipment_id": equipment_id,
        "provider_id": equip.get("provider_id"),
        "farmer_id": farmer_id,
        "start_date": start_iso,
        "end_date": end_iso,
        "days": days,
        "price": price,
        "notes": notes or "",
        "status": "pending",  # provider must approve
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }
    with _book_lock:
        _booking_store[bid] = rec
    return rec


def provider_respond_booking(provider_id: str, booking_id: str, accept: bool, provider_notes: Optional[str] = None) -> Dict[str, Any]:
    with _book_lock:
        b = _booking_store.get(booking_id)
        if not b:
            return {"error": "booking_not_found"}
        if b.get("provider_id") != provider_id:
            return {"error": "not_authorized"}
        if b["status"] != "pending":
            return {"error": "invalid_status"}

        if accept:
            # mark as approved
            b["status"] = "approved"
            b["provider_notes"] = provider_notes or ""
            b["updated_at"] = datetime.utcnow().isoformat()
            # optionally create quick hold (we already check overlaps on create)
            _booking_store[booking_id] = b
            return {"status": "approved", "booking": b}
        else:
            b["status"] = "rejected"
            b["provider_notes"] = provider_notes or ""
            b["updated_at"] = datetime.utcnow().isoformat()
            _booking_store[booking_id] = b
            return {"status": "rejected", "booking": b}


def cancel_booking_by_farmer(farmer_id: str, booking_id: str) -> Dict[str, Any]:
    with _book_lock:
        b = _booking_store.get(booking_id)
        if not b:
            return {"error": "booking_not_found"}
        if b.get("farmer_id") != farmer_id:
            return {"error": "not_authorized"}
        if b["status"] in ["cancelled", "completed", "rejected"]:
            return {"error": "invalid_status"}
        b["status"] = "cancelled"
        b["updated_at"] = datetime.utcnow().isoformat()
        _booking_store[booking_id] = b
    return {"status": "cancelled", "booking": b}


def complete_booking_by_provider(provider_id: str, booking_id: str) -> Dict[str, Any]:
    with _book_lock:
        b = _booking_store.get(booking_id)
        if not b:
            return {"error": "booking_not_found"}
        if b.get("provider_id") != provider_id:
            return {"error": "not_authorized"}
        if b["status"] != "approved":
            return {"error": "invalid_status"}
        b["status"] = "completed"
        b["completed_at"] = datetime.utcnow().isoformat()
        _booking_store[booking_id] = b
    return {"status": "completed", "booking": b}


# -----------------------
# Queries / summaries
# -----------------------
def list_bookings_for_provider(provider_id: str, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    with _book_lock:
        items = [b for b in _booking_store.values() if b.get("provider_id") == provider_id]
    if status_filter:
        items = [i for i in items if i.get("status") == status_filter]
    return items


def list_bookings_for_farmer(farmer_id: str, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    with _book_lock:
        items = [b for b in _booking_store.values() if b.get("farmer_id") == farmer_id]
    if status_filter:
        items = [i for i in items if i.get("status") == status_filter]
    return items


def get_booking(booking_id: str) -> Dict[str, Any]:
    return _booking_store.get(booking_id, {})


def equipment_calendar(equipment_id: str, from_iso: Optional[str] = None, to_iso: Optional[str] = None) -> Dict[str, Any]:
    """
    Returns bookings (all statuses except rejected/cancelled) for an equipment in a date range
    """
    f = _parse_date_iso(from_iso) if from_iso else None
    t = _parse_date_iso(to_iso) if to_iso else None
    with _book_lock:
        items = [b for b in _booking_store.values() if b.get("equipment_id") == equipment_id and b.get("status") in ["pending","approved","completed"]]
    filtered = []
    for b in items:
        bstart = _parse_date_iso(b["start_date"])
        bend = _parse_date_iso(b["end_date"])
        if f and bend < f:
            continue
        if t and bstart > t:
            continue
        filtered.append(b)
    return {"equipment_id": equipment_id, "bookings": filtered}


def weekly_demand_summary(provider_id: Optional[str] = None, weeks: int = 8) -> Dict[str, Any]:
    """
    Returns weekly aggregated booking-days demand per equipment for provider_id (or all providers).
    """
    end = datetime.utcnow().date()
    start = end - timedelta(weeks=weeks)
    buckets = {}
    with _book_lock:
        for b in _booking_store.values():
            if provider_id and b.get("provider_id") != provider_id:
                continue
            if b.get("status") in ["rejected", "cancelled"]:
                continue
            bstart = _parse_date_iso(b["start_date"])
            bend = _parse_date_iso(b["end_date"])
            if not bstart or not bend:
                continue
            # clip to window
            cur = max(bstart, start)
            while cur <= min(bend, end):
                wk = cur.isocalendar()[1]
                key = f"{b.get('equipment_id')}::wk_{wk}"
                buckets[key] = buckets.get(key, 0) + 1  # booking-day
                cur = cur + timedelta(days=1)
    # transform to structured output
    out = {}
    for k, v in buckets.items():
        eq, wk = k.split("::")
        out.setdefault(eq, {})[wk] = v
    return {"weeks": weeks, "summary": out}
