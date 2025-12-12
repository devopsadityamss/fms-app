# backend/app/api/farmer/operator_behavior.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services.farmer.operator_behavior_service import (
    add_operator,
    log_operator_usage,
    compute_operator_behavior,
    fleet_operator_behavior_ranking
)

router = APIRouter()


# -------------------------
# Payloads
# -------------------------

class OperatorCreate(BaseModel):
    operator_id: str
    name: str
    phone: Optional[str] = None


class UsageLogPayload(BaseModel):
    operator_id: str
    equipment_id: str
    hours: float
    task_type: str


# -------------------------
# Routes
# -------------------------

@router.post("/operator")
def api_add_operator(req: OperatorCreate):
    return add_operator(req.operator_id, req.name, req.phone)


@router.post("/operator/usage")
def api_log_usage(req: UsageLogPayload):
    return log_operator_usage(req.operator_id, req.equipment_id, req.hours, req.task_type)


@router.get("/operator/{operator_id}/behavior")
def api_operator_behavior(operator_id: str):
    res = compute_operator_behavior(operator_id)
    if res.get("status") == "operator_not_found":
        raise HTTPException(status_code=404, detail="operator_not_found")
    return res


@router.get("/operator/behavior/fleet")
def api_fleet_behavior():
    return fleet_operator_behavior_ranking()
