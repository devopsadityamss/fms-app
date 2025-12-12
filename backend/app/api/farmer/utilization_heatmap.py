# backend/app/api/farmer/utilization_heatmap.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services.farmer.utilization_heatmap_service import (
    generate_utilization_heatmap,
    fleet_utilization_heatmap
)

router = APIRouter()


class HeatmapRequest(BaseModel):
    lookback_days: Optional[int] = 90


@router.post("/equipment/{equipment_id}/utilization/heatmap")
def api_equipment_heatmap(equipment_id: str, req: HeatmapRequest):
    res = generate_utilization_heatmap(equipment_id, lookback_days=req.lookback_days or 90)
    if res is None:
        raise HTTPException(status_code=404, detail="equipment_not_found")
    return res


@router.get("/fleet/utilization/heatmap")
def api_fleet_heatmap(lookback_days: int = 90):
    return fleet_utilization_heatmap(lookback_days=lookback_days)
