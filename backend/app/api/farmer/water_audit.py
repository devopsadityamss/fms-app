from fastapi import APIRouter
from app.services.farmer.water_audit_service import (
    list_audit,
    list_audit_by_type
)

router = APIRouter()


@router.get("/water/{unit_id}/audit")
def api_water_audit(unit_id: str, limit: int = 200):
    """
    Returns unified water audit logs.
    """
    return list_audit(unit_id, limit)


@router.get("/water/{unit_id}/audit/{event_type}")
def api_water_audit_type(unit_id: str, event_type: str, limit: int = 200):
    """
    Returns audit logs filtered by event type.
    Event types:
      - irrigation
      - weather
      - moisture
      - schedule
      - deficit
      - manual
    """
    return list_audit_by_type(unit_id, event_type, limit)
