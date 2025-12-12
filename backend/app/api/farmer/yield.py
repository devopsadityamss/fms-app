# backend/app/api/farmer/yield.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.services.farmer.yield_service import (
    record_field_measurement,
    list_measurements,
    record_harvest,
    list_harvests,
    predict_yield,
    plan_harvest,
    yield_trend
)

router = APIRouter()


class MeasurementPayload(BaseModel):
    unit_id: str
    measured_at_iso: Optional[str] = None
    ndvi: Optional[float] = None
    biomass_est: Optional[float] = None
    rainfall_mm: Optional[float] = None
    fertilizer_applied_kg: Optional[float] = None
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@router.post("/farmer/yield/measure")
def api_record_measure(req: MeasurementPayload):
    return record_field_measurement(
        req.unit_id, req.measured_at_iso, ndvi=req.ndvi, biomass_est=req.biomass_est,
        rainfall_mm=req.rainfall_mm, fertilizer_applied_kg=req.fertilizer_applied_kg,
        notes=req.notes, metadata=req.metadata
    )


@router.get("/farmer/yield/measurements/{unit_id}")
def api_list_measurements(unit_id: str, limit: Optional[int] = 50):
    return {"unit_id": unit_id, "measurements": list_measurements(unit_id, limit=limit or 50)}


class HarvestPayload(BaseModel):
    unit_id: str
    harvest_date_iso: Optional[str] = None
    yield_kg: float
    price_per_kg: Optional[float] = None
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@router.post("/farmer/yield/harvest")
def api_record_harvest(req: HarvestPayload):
    return record_harvest(req.unit_id, req.harvest_date_iso, req.yield_kg, price_per_kg=req.price_per_kg, notes=req.notes, metadata=req.metadata)


@router.get("/farmer/yield/harvests/{unit_id}")
def api_list_harvests(unit_id: str, limit: Optional[int] = 50):
    return {"unit_id": unit_id, "harvests": list_harvests(unit_id, limit=limit or 50)}


@router.get("/farmer/yield/predict/{unit_id}")
def api_predict(unit_id: str, crop: str, variety: Optional[str] = None, area_acres: float = 1.0, baseline_yield_per_acre: Optional[float] = None):
    res = predict_yield(unit_id, crop, variety, area_acres, baseline_yield_per_acre)
    return res


@router.get("/farmer/yield/plan/{unit_id}")
def api_plan(unit_id: str, predicted_total_kg: float, price_per_kg: Optional[float] = None, harvest_rate_kg_per_hour: Optional[float] = 100.0, laborers_available: Optional[int] = 2):
    res = plan_harvest(unit_id, predicted_total_kg, price_per_kg, harvest_rate_kg_per_hour, laborers_available)
    return res


@router.get("/farmer/yield/trend/{unit_id}")
def api_trend(unit_id: str, last_n: Optional[int] = 6):
    return yield_trend(unit_id, last_n or 6)
