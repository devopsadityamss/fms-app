# backend/app/api/farmer/execution_monitor.py

from fastapi import APIRouter, HTTPException, Body, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.services.farmer.execution_monitor_service import (
    create_execution_record,
    create_execution_from_action,
    mark_execution,
    auto_reconcile_executions,
    list_executions_for_unit,
    get_execution_summary,
    get_farmer_reliability
)

router = APIRouter()

class CreateExecRequest(BaseModel):
    farmer_id: Optional[str] = None
    action_title: str
    category: str
    priority: int = 50
    scheduled_at_iso: Optional[str] = None
    window_hours: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None

class MarkExecRequest(BaseModel):
    action_id: str
    status: str  # done | partial | skipped | failed
    actor: Optional[str] = None
    status_metadata: Optional[Dict[str, Any]] = None

class CreateFromActionRequest(BaseModel):
    action: Dict[str, Any]
    farmer_id: Optional[str] = None
    scheduled_at_iso: Optional[str] = None
    window_hours: Optional[int] = None

@router.post("/execution/{unit_id}/create")
def api_create_execution(unit_id: int, payload: CreateExecRequest = Body(...)):
    rec = create_execution_record(
        unit_id=str(unit_id),
        farmer_id=payload.farmer_id,
        action_title=payload.action_title,
        category=payload.category,
        priority=payload.priority,
        scheduled_at_iso=payload.scheduled_at_iso,
        window_hours=payload.window_hours,
        metadata=payload.metadata
    )
    return rec

@router.post("/execution/{unit_id}/create-from-action")
def api_create_from_action(unit_id: int, payload: CreateFromActionRequest = Body(...)):
    rec = create_execution_from_action(payload.action, str(unit_id), payload.farmer_id, scheduled_at_iso=payload.scheduled_at_iso, window_hours=payload.window_hours)
    return rec

@router.post("/execution/{unit_id}/mark")
def api_mark_execution(unit_id: int, payload: MarkExecRequest = Body(...)):
    res = mark_execution(str(unit_id), payload.action_id, payload.status, actor=payload.actor, status_metadata=payload.status_metadata)
    if res.get("error"):
        raise HTTPException(status_code=400, detail=res)
    return res

@router.post("/execution/auto-reconcile")
def api_auto_reconcile(mark_ignored_for_priority_threshold: Optional[int] = Query(50), now_iso: Optional[str] = Body(None)):
    res = auto_reconcile_executions(now_iso=now_iso, mark_ignored_for_priority_threshold=int(mark_ignored_for_priority_threshold))
    return res

@router.get("/execution/{unit_id}")
def api_list_executions(unit_id: int, limit: Optional[int] = Query(200)):
    return list_executions_for_unit(str(unit_id), limit=limit)

@router.get("/execution/{unit_id}/summary")
def api_execution_summary(unit_id: int):
    return get_execution_summary(str(unit_id))

@router.get("/execution/farmer/{farmer_id}/reliability")
def api_farmer_reliability(farmer_id: str):
    return get_farmer_reliability(farmer_id)
