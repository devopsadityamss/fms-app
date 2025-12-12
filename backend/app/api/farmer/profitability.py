# backend/app/api/farmer/profitability.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict

from app.services.farmer.profitability_service import compute_profitability

router = APIRouter()


class ProfitabilityRequest(BaseModel):
    market_price_per_quintal: float
    seed_price_per_kg: Optional[float] = 50
    fertilizer_price_map: Optional[Dict[str, float]] = None
    pesticide_price_per_liter: Optional[float] = 300
    irrigation_cost_per_1000_liters: Optional[float] = 15
    labor_cost_total: Optional[float] = 0
    equipment_cost_total: Optional[float] = 0
    misc_cost_total: Optional[float] = 0


@router.post("/profit/forecast/{unit_id}")
def api_profit_forecast(unit_id: str, req: ProfitabilityRequest):
    result = compute_profitability(
        unit_id,
        market_price_per_quintal=req.market_price_per_quintal,
        seed_price_per_kg=req.seed_price_per_kg,
        fertilizer_price_map=req.fertilizer_price_map,
        pesticide_price_per_liter=req.pesticide_price_per_liter,
        irrigation_cost_per_1000_liters=req.irrigation_cost_per_1000_liters,
        labor_cost_total=req.labor_cost_total,
        equipment_cost_total=req.equipment_cost_total,
        misc_cost_total=req.misc_cost_total
    )

    if result.get("status") == "unit_not_found":
        raise HTTPException(status_code=404, detail="unit_not_found")

    return result
