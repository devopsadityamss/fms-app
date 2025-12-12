# backend/app/api/farmer/soil_nutrient.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.services.farmer.soil_nutrient_service import (
    record_soil_test,
    get_latest_test,
    detect_deficiencies,
    recommend_fertilizer,
    soil_health_score,
    soil_improvement_suggestions,
    soil_summary
)

router = APIRouter()


class SoilTestPayload(BaseModel):
    unit_id: str
    n: float
    p: float
    k: float
    oc: float
    ph: float
    ec: float
    zn: Optional[float] = None
    b: Optional[float] = None
    s: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


@router.post("/farmer/soil/record")
def api_record_test(req: SoilTestPayload):
    return record_soil_test(
        req.unit_id, req.n, req.p, req.k, req.oc,
        req.ph, req.ec, req.zn, req.b, req.s, req.metadata
    )


@router.get("/farmer/soil/latest/{unit_id}")
def api_latest(unit_id: str):
    data = get_latest_test(unit_id)
    if not data:
        raise HTTPException(status_code=404, detail="No soil tests found")
    return data


@router.get("/farmer/soil/deficiencies/{unit_id}")
def api_deficiencies(unit_id: str):
    test = get_latest_test(unit_id)
    if not test:
        raise HTTPException(status_code=404, detail="No soil test available")
    return {"unit_id": unit_id, "deficiencies": detect_deficiencies(test)}


@router.get("/farmer/soil/fertilizer")
def api_fertilizer(crop: str, stage: str, area_acres: float):
    return recommend_fertilizer(crop, stage, area_acres)


@router.get("/farmer/soil/summary/{unit_id}")
def api_summary(unit_id: str, crop: str, stage: str, area_acres: float = 1):
    return soil_summary(unit_id, crop, stage, area_acres)
