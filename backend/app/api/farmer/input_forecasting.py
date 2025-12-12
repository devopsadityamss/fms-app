# backend/app/api/farmer/input_forecasting.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services.farmer.input_forecasting_service import (
    forecast_inputs_for_unit
)

router = APIRouter()


@router.get("/inputs/forecast/{unit_id}")
def api_input_forecast(unit_id: str):
    res = forecast_inputs_for_unit(unit_id)
    if res.get("status") == "unit_not_found":
        raise HTTPException(status_code=404, detail="unit_not_found")
    return res
