# backend/app/api/farmer/operator_equipment_match.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from app.services.farmer.operator_equipment_match_service import (
    match_operators_to_equipment,
    match_equipment_to_operator,
    confirm_assignment,
    list_assignments,
    cancel_assignment
)

router = APIRouter()


# Payloads
class TaskMeta(BaseModel):
    crop: Optional[str] = None
    stage: Optional[str] = None
    priority: Optional[int] = 5
    estimated_hours: Optional[float] = 4.0
    extra: Optional[Dict[str, Any]] = None


class MatchOperatorsRequest(BaseModel):
    operator_ids: Optional[List[str]] = None
    task_meta: Optional[TaskMeta] = None
    top_n: Optional[int] = 5


class MatchEquipmentsRequest(BaseModel):
    equipment_ids: Optional[List[str]] = None
    task_meta: Optional[TaskMeta] = None
    top_n: Optional[int] = 5


class ConfirmAssignmentRequest(BaseModel):
    operator_id: str
    equipment_id: str
    task_meta: Optional[TaskMeta] = None


# Endpoints

@router.post("/match/equipment/{equipment_id}")
def api_match_operators(equipment_id: str, req: MatchOperatorsRequest):
    tm = req.task_meta.dict() if req.task_meta else {}
    res = match_operators_to_equipment(equipment_id, candidate_operator_ids=req.operator_ids, task_meta=tm, top_n=req.top_n or 5)
    return res


@router.post("/match/operator/{operator_id}")
def api_match_equipments(operator_id: str, req: MatchEquipmentsRequest):
    tm = req.task_meta.dict() if req.task_meta else {}
    res = match_equipment_to_operator(operator_id, candidate_equipment_ids=req.equipment_ids, task_meta=tm, top_n=req.top_n or 5)
    return res


@router.post("/match/confirm")
def api_confirm_assignment(req: ConfirmAssignmentRequest):
    rec = confirm_assignment(req.operator_id, req.equipment_id, task_meta=req.task_meta.dict() if req.task_meta else {})
    return {"success": True, "assignment": rec}


@router.get("/match/assignments")
def api_list_assignments(operator_id: Optional[str] = None, equipment_id: Optional[str] = None):
    return list_assignments(operator_id=operator_id, equipment_id=equipment_id)


@router.post("/match/assignments/{assignment_id}/cancel")
def api_cancel_assignment(assignment_id: str):
    res = cancel_assignment(assignment_id)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res
