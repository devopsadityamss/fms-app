# backend/app/api/farmer/route_optimization.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from app.services.farmer.route_optimization_service import (
    optimize_route_for_tasks
)

router = APIRouter()


class TaskPayload(BaseModel):
    task_id: str
    lat: float
    lon: float
    estimated_hours: Optional[float] = None
    operator_id: Optional[str] = None


class RouteRequest(BaseModel):
    equipment_id: str
    tasks: List[TaskPayload]
    weight_config: Optional[Dict[str, float]] = None


@router.post("/route/optimize")
def api_optimize_route(req: RouteRequest):
    res = optimize_route_for_tasks(
        equipment_id=req.equipment_id,
        tasks=[t.dict() for t in req.tasks],
        weight_config=req.weight_config
    )
    return res
