# backend/app/api/farmer/soil.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
from app.services.farmer.soil_service import (
    record_soil_test,
    list_soil_tests,
    soil_intelligence_summary,
    get_soil_intelligence,      # ← ADDED from mock version
    get_soil_snapshot,          # ← ADDED from mock version
)

router = APIRouter()

# ===========================
# REAL SOIL TEST ENDPOINTS
# ===========================

class SoilTestPayload(BaseModel):
    farmer_id: str
    unit_id: str
    npk: Dict[str, float]
    ph: float
    ec: float
    oc: float
    micronutrients: Optional[Dict[str, float]] = None
    texture: Optional[str] = None
    lab_name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

@router.post("/farmer/soil/record")
def api_record_soil(req: SoilTestPayload):
    return record_soil_test(
        req.farmer_id, req.unit_id, req.npk,
        req.ph, req.ec, req.oc,
        micronutrients=req.micronutrients, texture=req.texture,
        lab_name=req.lab_name, metadata=req.metadata
    )

@router.get("/farmer/soil/tests/{unit_id}")
def api_list_tests(unit_id: str):
    return {"tests": list_soil_tests(unit_id)}

@router.get("/farmer/soil/summary/{unit_id}")
def api_summary(unit_id: str, crop: str):
    res = soil_intelligence_summary(unit_id, crop)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res


# ===========================
# MOCK SOIL INTELLIGENCE ENDPOINTS
# ===========================

@router.get("/soil/{unit_id}")
def soil_overview(unit_id: int, crop: str = "generic"):
    return get_soil_intelligence(unit_id, crop)

@router.get("/soil/{unit_id}/snapshot")
def soil_snapshot(unit_id: int):
    return get_soil_snapshot(unit_id)