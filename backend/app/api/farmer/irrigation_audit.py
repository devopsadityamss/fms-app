from fastapi import APIRouter
from app.services.farmer.irrigation_audit_service import (
    audit_irrigation_event,
    audit_moisture_update,
    audit_weather_update,
    audit_system_recommendation,
    audit_override,
    audit_deviation,
    audit_leakage_alert,
    list_audit_logs,
    audit_summary
)

router = APIRouter()

# AUDIT RECORDS
@router.get("/irrigation/audit/{unit_id}")
def api_list_audit(unit_id: str, types: str = None):
    type_list = types.split(",") if types else None
    return list_audit_logs(unit_id, type_list)


@router.get("/irrigation/audit/{unit_id}/summary")
def api_audit_summary(unit_id: str):
    return audit_summary(unit_id)
