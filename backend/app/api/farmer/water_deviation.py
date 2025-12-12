from fastapi import APIRouter
from app.services.farmer.water_deviation_service import (
    record_predicted_usage,
    record_actual_usage,
    water_deviation_summary
)

router = APIRouter()

@router.post("/water/predicted")
def api_record_predicted(payload: dict):
    return record_predicted_usage(**payload)

@router.post("/water/actual")
def api_record_actual(payload: dict):
    return record_actual_usage(**payload)

@router.get("/water/{unit_id}/deviation")
def api_water_deviation(unit_id: str):
    return water_deviation_summary(unit_id)
