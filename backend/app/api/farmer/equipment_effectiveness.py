# backend/app/api/farmer/equipment_effectiveness.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.services.farmer.equipment_effectiveness_service import (
    compute_equipment_effectiveness_for_crop,
    fleet_crop_effectiveness_ranking
)

router = APIRouter()


class EffectivenessRequest(BaseModel):
    crop: str
    unit_id: Optional[str] = None
    weight_config: Optional[Dict[str, float]] = None


@router.post("/equipment/{equipment_id}/effectiveness")
def api_equipment_effectiveness(equipment_id: str, req: EffectivenessRequest):
    res = compute_equipment_effectiveness_for_crop(equipment_id, req.crop, unit_id=req.unit_id, weight_config=req.weight_config)
    if res is None:
        raise HTTPException(status_code=404, detail="equipment_not_found")
    return res


@router.post("/equipment/effectiveness/ranking")
def api_fleet_effectiveness(req: EffectivenessRequest):
    return fleet_crop_effectiveness_ranking(req.crop, top_n=50, weight_config=req.weight_config)
