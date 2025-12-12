"""
API Routes — Vision -> Timeline Integration
------------------------------------------

Endpoints:
 - POST /farmer/vision/integrate          -> integrate an analysis into the timeline
 - GET  /farmer/vision/integration/{id}   -> get integration record
 - GET  /farmer/vision/integration        -> list integrations (optional filter by unit_id)
"""

from fastapi import APIRouter, HTTPException, Body, Query
from typing import Optional, Dict, Any

from app.services.farmer import vision_timeline_integration_service as svc

router = APIRouter()


@router.post("/farmer/vision/integrate")
async def api_integrate_analysis(
    payload: Dict[str, Any] = Body(...)
):
    """
    Payload options:
      - image_id: str  (optional if analysis provided)
      - analysis_record: dict (optional)
      - create_timeline_event: bool (default True)
      - event_category: str
      - event_title_prefix: str
      - notes: str

    Example:
    {
      "image_id": "uuid",
      "create_timeline_event": true,
      "notes": "auto-integration from mobile upload"
    }
    """
    image_id = payload.get("image_id")
    analysis_record = payload.get("analysis_record")
    create_event = payload.get("create_timeline_event", True)
    event_category = payload.get("event_category", "vision_analysis")
    event_title_prefix = payload.get("event_title_prefix", "Image Analysis")
    notes = payload.get("notes")

    res = svc.integrate_image_analysis(
        image_id=image_id,
        analysis_record=analysis_record,
        create_timeline_event=create_event,
        event_category=event_category,
        event_title_prefix=event_title_prefix,
        notes=notes
    )
    return res


@router.get("/farmer/vision/integration/{integration_id}")
def api_get_integration(integration_id: str):
    rec = svc.get_integration(integration_id)
    if not rec:
        raise HTTPException(status_code=404, detail="integration_not_found")
    return rec


@router.get("/farmer/vision/integration")
def api_list_integrations(unit_id: Optional[str] = Query(None)):
    return svc.list_integrations(unit_id=unit_id)
