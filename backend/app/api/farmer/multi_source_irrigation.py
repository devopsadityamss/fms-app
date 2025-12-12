from fastapi import APIRouter
from app.services.farmer.multi_source_irrigation_service import (
    add_water_source,
    list_water_sources,
    generate_daily_multi_source_plan,
    list_plans,
    multi_source_summary
)

router = APIRRouter()

@router.post("/water/source")
def api_add_source(payload: dict):
    return add_water_source(**payload)

@router.get("/water/{unit_id}/sources")
def api_list_sources(unit_id: str):
    return list_water_sources(unit_id)

@router.post("/water/{unit_id}/plan")
def api_generate_plan(unit_id: str, payload: dict):
    return generate_daily_multi_source_plan(
        unit_id=unit_id,
        date_iso=payload["date_iso"],
        required_liters=payload["required_liters"]
    )

@router.get("/water/{unit_id}/plans")
def api_list_plans(unit_id: str):
    return list_plans(unit_id)

@router.get("/water/{unit_id}/summary")
def api_multi_source_summary(unit_id: str):
    return multi_source_summary(unit_id)
