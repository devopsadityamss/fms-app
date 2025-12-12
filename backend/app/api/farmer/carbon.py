# backend/app/api/farmer/carbon.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.services.farmer.carbon_service import (
    record_carbon_event,
    list_carbon_events,
    calculate_unit_carbon_balance,
    sustainability_score,
    sustainability_suggestions,
    carbon_summary,
    calculate_carbon_credits,
    carbon_full_summary
)


router = APIRouter()


class CarbonEventPayload(BaseModel):
    farmer_id: str
    unit_id: str
    event_type: str     # emission / sequestration
    category: str
    value: float
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@router.post("/farmer/carbon/record")
def api_record_carbon(req: CarbonEventPayload):
    if req.event_type not in ["emission", "sequestration"]:
        raise HTTPException(status_code=400, detail="Invalid event_type")
    return record_carbon_event(
        farmer_id=req.farmer_id,
        unit_id=req.unit_id,
        event_type=req.event_type,
        category=req.category,
        value=req.value,
        description=req.description,
        metadata=req.metadata
    )


@router.get("/farmer/carbon/events/{unit_id}")
def api_list_events(unit_id: str):
    return {"unit_id": unit_id, "events": list_carbon_events(unit_id)}


@router.get("/farmer/carbon/balance/{unit_id}")
def api_balance(unit_id: str):
    return calculate_unit_carbon_balance(unit_id)


@router.get("/farmer/carbon/score/{unit_id}")
def api_score(unit_id: str):
    return sustainability_score(unit_id)


@router.get("/farmer/carbon/suggestions/{unit_id}")
def api_suggestions(unit_id: str):
    return sustainability_suggestions(unit_id)


@router.get("/farmer/carbon/summary/{unit_id}")
def api_summary(unit_id: str):
    return carbon_summary(unit_id)



@router.get("/farmer/carbon/credits/{unit_id}")
def api_carbon_credits(
    unit_id: str,
    price_per_t_co2: float = Query(6.0)
):
    return calculate_carbon_credits(unit_id, price_per_t_co2)


@router.get("/farmer/carbon/full-summary/{unit_id}")
def api_carbon_full_summary(
    unit_id: str,
    price_per_t_co2: float = Query(6.0)
):
    return carbon_full_summary(unit_id, price_per_t_co2)
