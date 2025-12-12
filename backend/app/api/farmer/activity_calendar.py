"""
API Routes — Activity & Operation Calendar (Farmer POV)
-------------------------------------------------------

Endpoints:
 - POST   /farmer/calendar/event
 - GET    /farmer/calendar/event/{event_id}
 - PUT    /farmer/calendar/event/{event_id}
 - DELETE /farmer/calendar/event/{event_id}
 - GET    /farmer/calendar/events
 - GET    /farmer/calendar/agenda/{date_iso}
"""

from fastapi import APIRouter, HTTPException, Query, Body
from typing import Optional, Dict, Any

from app.services.farmer import activity_calendar_service as svc

router = APIRouter()


@router.post("/farmer/calendar/event")
async def api_create_event(payload: Dict[str, Any] = Body(...)):
    if "title" not in payload or "start_time" not in payload:
        raise HTTPException(status_code=400, detail="title and start_time are required")
    return svc.create_event(payload)


@router.get("/farmer/calendar/event/{event_id}")
def api_get_event(event_id: str):
    rec = svc.get_event(event_id)
    if not rec:
        raise HTTPException(status_code=404, detail="event_not_found")
    return rec


@router.put("/farmer/calendar/event/{event_id}")
async def api_update_event(event_id: str, payload: Dict[str, Any] = Body(...)):
    rec = svc.update_event(event_id, payload)
    if not rec:
        raise HTTPException(status_code=404, detail="event_not_found")
    return rec


@router.delete("/farmer/calendar/event/{event_id}")
def api_delete_event(event_id: str):
    ok = svc.delete_event(event_id)
    if not ok:
        raise HTTPException(status_code=404, detail="event_not_found")
    return {"success": True}


@router.get("/farmer/calendar/events")
def api_list_events(
    unit_id: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None)
):
    return svc.list_events(
        unit_id=unit_id,
        event_type=event_type,
        date_from=date_from,
        date_to=date_to
    )


@router.get("/farmer/calendar/agenda/{date_iso}")
def api_agenda_for_day(date_iso: str, unit_id: Optional[str] = Query(None)):
    return svc.agenda_for_day(unit_id=unit_id, day_iso=date_iso)
