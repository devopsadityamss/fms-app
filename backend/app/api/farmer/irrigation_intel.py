# backend/app/api/farmer/irrigation_intel.py

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from app.services.farmer.irrigation_intel_service import irrigation_intelligence

router = APIRouter()


class IrrigationPayload(BaseModel):
    unit_id: str
    crop: str
    stage: str
    et0: float                  # reference evapotranspiration
    rainfall_mm: float
    texture: str               # sandy / loamy / clay
    soil_moisture: Optional[float] = None  # %
    irrigation_flow_lph: Optional[float] = None  # liters per hour


@router.post("/farmer/irrigation/intel")
def api_irrigation_intel(req: IrrigationPayload):
    return irrigation_intelligence(
        unit_id=req.unit_id,
        crop=req.crop,
        stage=req.stage,
        et0=req.et0,
        rainfall_mm=req.rainfall_mm,
        texture=req.texture,
        soil_moisture=req.soil_moisture,
        irrigation_flow_lph=req.irrigation_flow_lph
    )
