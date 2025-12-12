# backend/app/api/farmer/equipment_maintenance.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.services.farmer.equipment_maintenance_service import (
    register_equipment,
    get_equipment,
    list_equipment,
    log_usage,
    list_usage,
    create_maintenance_rule,
    list_maintenance_rules,
    assign_rule_to_equipment,
    estimate_next_service,
    create_service_ticket,
    update_ticket,
    list_tickets,
    record_maintenance_performed,
    maintenance_history,
    equipment_due_for_service,
    equipment_summary
)

router = APIRouter()


# Payloads
class EquipmentPayload(BaseModel):
    owner_id: str
    equipment_type: str
    model: str
    serial_no: Optional[str] = None
    capacity: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class UsagePayload(BaseModel):
    equipment_id: str
    hours: Optional[float] = 0.0
    km: Optional[float] = 0.0
    cycles: Optional[int] = 0
    notes: Optional[str] = None
    ts_iso: Optional[str] = None


class RulePayload(BaseModel):
    equipment_type: str
    interval_hours: Optional[int] = None
    interval_days: Optional[int] = None
    checklist: Optional[List[str]] = None


class AssignRulePayload(BaseModel):
    equipment_id: str
    rule_id: str


class TicketPayload(BaseModel):
    equipment_id: str
    reported_by: str
    issue: str
    priority: Optional[str] = "normal"
    metadata: Optional[Dict[str, Any]] = None


class TicketUpdatePayload(BaseModel):
    updates: Dict[str, Any]


class MaintenanceRecordPayload(BaseModel):
    equipment_id: str
    performed_by: str
    performed_at_iso: Optional[str] = None
    odometer_hours: Optional[float] = None
    notes: Optional[str] = None
    checklist_done: Optional[List[str]] = None


# Endpoints
@router.post("/farmer/equipment/register")
def api_register_equipment(req: EquipmentPayload):
    return register_equipment(req.owner_id, req.equipment_type, req.model, serial_no=req.serial_no, capacity=req.capacity, metadata=req.metadata)


@router.get("/farmer/equipment/{equipment_id}")
def api_get_equipment(equipment_id: str):
    res = get_equipment(equipment_id)
    if not res:
        raise HTTPException(status_code=404, detail="equipment_not_found")
    return res


@router.get("/farmer/equipment/list")
def api_list_equipment(owner_id: Optional[str] = None):
    return {"equipment": list_equipment(owner_id=owner_id)}


@router.post("/farmer/equipment/usage")
def api_log_usage(req: UsagePayload):
    res = log_usage(req.equipment_id, hours=req.hours or 0.0, km=req.km or 0.0, cycles=req.cycles or 0, notes=req.notes, ts_iso=req.ts_iso)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res


@router.get("/farmer/equipment/usage/{equipment_id}")
def api_list_usage(equipment_id: str, limit: Optional[int] = 200):
    return {"equipment_id": equipment_id, "usage": list_usage(equipment_id, limit=limit or 200)}


@router.post("/farmer/equipment/maintenance/rule")
def api_create_rule(req: RulePayload):
    return create_maintenance_rule(req.equipment_type, interval_hours=req.interval_hours, interval_days=req.interval_days, checklist=req.checklist)


@router.get("/farmer/equipment/maintenance/rules")
def api_list_rules(equipment_type: Optional[str] = None):
    return {"rules": list_maintenance_rules(equipment_type=equipment_type)}


@router.post("/farmer/equipment/maintenance/assign_rule")
def api_assign_rule(req: AssignRulePayload):
    res = assign_rule_to_equipment(req.equipment_id, req.rule_id)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res


@router.get("/farmer/equipment/maintenance/estimate/{equipment_id}")
def api_estimate_next(equipment_id: str):
    res = estimate_next_service(equipment_id)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res


@router.post("/farmer/equipment/ticket")
def api_create_ticket(req: TicketPayload):
    res = create_service_ticket(req.equipment_id, req.reported_by, req.issue, priority=req.priority, metadata=req.metadata)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res


@router.post("/farmer/equipment/ticket/{ticket_id}")
def api_update_ticket(ticket_id: str, req: TicketUpdatePayload):
    res = update_ticket(ticket_id, req.updates)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res


@router.get("/farmer/equipment/tickets")
def api_list_tickets(equipment_id: Optional[str] = None, status: Optional[str] = None):
    return {"tickets": list_tickets(equipment_id=equipment_id, status=status)}


@router.post("/farmer/equipment/maintenance/record")
def api_record_maintenance(req: MaintenanceRecordPayload):
    res = record_maintenance_performed(req.equipment_id, req.performed_by, performed_at_iso=req.performed_at_iso, odometer_hours=req.odometer_hours, notes=req.notes, checklist_done=req.checklist_done)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res


@router.get("/farmer/equipment/maintenance/history/{equipment_id}")
def api_history(equipment_id: str, limit: Optional[int] = 50):
    return {"equipment_id": equipment_id, "history": maintenance_history(equipment_id, limit=limit or 50)}


@router.get("/farmer/equipment/due")
def api_equipment_due(owner_id: Optional[str] = None):
    return {"due": equipment_due_for_service(owner_id=owner_id)}


@router.get("/farmer/equipment/summary/{equipment_id}")
def api_equipment_summary(equipment_id: str):
    res = equipment_summary(equipment_id)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res
