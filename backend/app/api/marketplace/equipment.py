# backend/app/api/marketplace/equipment.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.services.marketplace.equipment_service import (
    register_provider,
    register_equipment,
    update_equipment,
    list_equipment,
    get_equipment,
    check_equipment_availability,
    create_booking,
    provider_respond_booking,
    cancel_booking_by_farmer,
    complete_booking_by_provider,
    list_bookings_for_provider,
    list_bookings_for_farmer,
    get_booking,
    equipment_calendar,
    weekly_demand_summary
)

router = APIRouter()


# ---------- Payloads ----------
class ProviderPayload(BaseModel):
    provider_id: Optional[str] = None
    name: str
    contact: Optional[str] = None


class EquipmentPayload(BaseModel):
    provider_id: str
    title: str
    description: str
    daily_rate: float
    available_from_iso: Optional[str] = None
    available_to_iso: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class EquipmentUpdatePayload(BaseModel):
    equipment_id: str
    updates: Dict[str, Any]


class BookingPayload(BaseModel):
    farmer_id: str
    equipment_id: str
    start_date: str  # YYYY-MM-DD
    end_date: str
    notes: Optional[str] = None


class ProviderRespondPayload(BaseModel):
    provider_id: str
    booking_id: str
    accept: bool
    provider_notes: Optional[str] = None


# ---------- Endpoints ----------
@router.post("/market/provider/register")
def api_register_provider(req: ProviderPayload):
    return register_provider(req.provider_id, req.name, contact=req.contact)


@router.post("/market/equipment/register")
def api_register_equipment(req: EquipmentPayload):
    return register_equipment(
        req.provider_id, req.title, req.description, req.daily_rate,
        available_from_iso=req.available_from_iso, available_to_iso=req.available_to_iso, metadata=req.metadata
    )


@router.post("/market/equipment/update")
def api_update_equipment(req: EquipmentUpdatePayload):
    res = update_equipment(req.equipment_id, req.updates)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res


@router.get("/market/equipment")
def api_list_equipment(provider_id: Optional[str] = None, active_only: Optional[bool] = True):
    return list_equipment(provider_id=provider_id, active_only=bool(active_only))


@router.get("/market/equipment/{equipment_id}")
def api_get_equipment(equipment_id: str):
    res = get_equipment(equipment_id)
    if not res:
        raise HTTPException(status_code=404, detail="equipment_not_found")
    return res


@router.get("/market/equipment/{equipment_id}/availability")
def api_check_availability(equipment_id: str, start_date: str, end_date: str):
    res = check_equipment_availability(equipment_id, start_date, end_date)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res


@router.post("/market/booking/create")
def api_create_booking(req: BookingPayload):
    res = create_booking(req.farmer_id, req.equipment_id, req.start_date, req.end_date, notes=req.notes)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res


@router.post("/market/booking/respond")
def api_provider_respond(req: ProviderRespondPayload):
    res = provider_respond_booking(req.provider_id, req.booking_id, req.accept, provider_notes=req.provider_notes)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res


@router.post("/market/booking/cancel")
def api_cancel_booking(farmer_id: str, booking_id: str):
    res = cancel_booking_by_farmer(farmer_id, booking_id)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res


@router.post("/market/booking/complete")
def api_complete_booking(provider_id: str, booking_id: str):
    res = complete_booking_by_provider(provider_id, booking_id)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res


@router.get("/market/bookings/provider/{provider_id}")
def api_list_bookings_provider(provider_id: str, status: Optional[str] = None):
    return list_bookings_for_provider(provider_id, status_filter=status)


@router.get("/market/bookings/farmer/{farmer_id}")
def api_list_bookings_farmer(farmer_id: str, status: Optional[str] = None):
    return list_bookings_for_farmer(farmer_id, status_filter=status)


@router.get("/market/booking/{booking_id}")
def api_get_booking(booking_id: str):
    res = get_booking(booking_id)
    if not res:
        raise HTTPException(status_code=404, detail="booking_not_found")
    return res


@router.get("/market/equipment/{equipment_id}/calendar")
def api_equipment_calendar(equipment_id: str, from_iso: Optional[str] = None, to_iso: Optional[str] = None):
    return equipment_calendar(equipment_id, from_iso=from_iso, to_iso=to_iso)


@router.get("/market/demand/weekly")
def api_weekly_demand(provider_id: Optional[str] = None, weeks: Optional[int] = 8):
    return weekly_demand_summary(provider_id=provider_id, weeks=weeks or 8)
