# backend/app/services/farmer/profitability_service.py

from datetime import datetime
from typing import Dict, Any, Optional

from app.services.farmer.input_forecasting_service import forecast_inputs_for_unit
from app.services.farmer.yield_forecasting_service import forecast_yield_for_unit
from app.services.farmer.unit_service import _unit_store


"""
Profitability Calculator

Formula:
--------------------------------------------
Revenue = Expected_Yield_Quintal × Market_Price

Cost = 
    Seed_cost
  + Fertilizer_cost
  + Pesticide_cost
  + Irrigation_cost
  + Labor_cost
  + Equipment_cost
  + Misc_cost

Profit = Revenue - Cost

Breakeven_Yield = Cost / Market_Price
Breakeven_Price = Cost / Expected_Yield
--------------------------------------------

Everything is computed using:
- Input forecast
- Yield forecast
- Farmer-provided cost parameters (unit prices)
"""


def compute_profitability(
    unit_id: str,
    market_price_per_quintal: float,
    seed_price_per_kg: float = 50,
    fertilizer_price_map: Optional[Dict[str, float]] = None,
    pesticide_price_per_liter: float = 300,
    irrigation_cost_per_1000_liters: float = 15,
    labor_cost_total: float = 0,
    equipment_cost_total: float = 0,
    misc_cost_total: float = 0
) -> Dict[str, Any]:

    unit = _unit_store.get(unit_id)
    if not unit:
        return {"status": "unit_not_found", "unit_id": unit_id}

    # Forecast inputs
    input_data = forecast_inputs_for_unit(unit_id)
    total_inputs = input_data.get("total_inputs", {})

    seed_kg = total_inputs.get("seed_kg", 0)
    fert = total_inputs.get("fertilizer", {})
    pesticide_liters = total_inputs.get("pesticide_liters", 0)
    irrigation_liters = total_inputs.get("irrigation_liters", 0)

    # ------------------------
    # Compute Input Costs
    # ------------------------
    seed_cost = seed_kg * seed_price_per_kg

    fertilizer_cost = 0
    fertilizer_price_map = fertilizer_price_map or {}
    for nutrient, qty in fert.items():
        price = fertilizer_price_map.get(nutrient, 40)  # generic per kg price
        fertilizer_cost += price * qty

    pesticide_cost = pesticide_liters * pesticide_price_per_liter
    irrigation_cost = (irrigation_liters / 1000) * irrigation_cost_per_1000_liters

    # Farmer-provided additional costs
    labor_cost = labor_cost_total
    equipment_cost = equipment_cost_total
    misc_cost = misc_cost_total

    total_cost = (
        seed_cost +
        fertilizer_cost +
        pesticide_cost +
        irrigation_cost +
        labor_cost +
        equipment_cost +
        misc_cost
    )

    # ------------------------
    # Compute Yield & Revenue
    # ------------------------
    yield_data = forecast_yield_for_unit(
        unit_id,
        crop_price_per_quintal=market_price_per_quintal
    )

    expected_yield = yield_data.get("expected_yield_quintal", 0)
    optimistic_yield = yield_data.get("optimistic_yield_quintal", 0)
    pessimistic_yield = yield_data.get("pessimistic_yield_quintal", 0)

    revenue = expected_yield * market_price_per_quintal
    revenue_opt = optimistic_yield * market_price_per_quintal
    revenue_pes = pessimistic_yield * market_price_per_quintal

    # ------------------------
    # Profit Calculations
    # ------------------------
    profit = revenue - total_cost
    profit_opt = revenue_opt - total_cost
    profit_pes = revenue_pes - total_cost

    margin = (profit / total_cost * 100) if total_cost > 0 else None

    breakeven_yield = total_cost / market_price_per_quintal if market_price_per_quintal > 0 else None
    breakeven_price = total_cost / expected_yield if expected_yield > 0 else None

    return {
        "unit_id": unit_id,
        "crop": unit.get("crop"),
        "area_acre": unit.get("area"),
        "cost_breakdown": {
            "seed_cost": round(seed_cost, 2),
            "fertilizer_cost": round(fertilizer_cost, 2),
            "pesticide_cost": round(pesticide_cost, 2),
            "irrigation_cost": round(irrigation_cost, 2),
            "labor_cost": round(labor_cost, 2),
            "equipment_cost": round(equipment_cost, 2),
            "misc_cost": round(misc_cost, 2),
            "total_cost": round(total_cost, 2),
        },
        "yield_forecast": {
            "expected_quintal": expected_yield,
            "optimistic_quintal": optimistic_yield,
            "pessimistic_quintal": pessimistic_yield,
        },
        "revenue_forecast": {
            "expected_revenue": round(revenue, 2),
            "optimistic_revenue": round(revenue_opt, 2),
            "pessimistic_revenue": round(revenue_pes, 2),
        },
        "profit_forecast": {
            "expected_profit": round(profit, 2),
            "optimistic_profit": round(profit_opt, 2),
            "pessimistic_profit": round(profit_pes, 2),
        },
        "margin_percent": round(margin, 2) if margin is not None else None,
        "breakeven_yield_quintal": breakeven_yield,
        "breakeven_price_per_quintal": breakeven_price,
        "explainability": {
            "inputs_used": total_inputs,
            "yield_model": yield_data,
        },
        "generated_at": datetime.utcnow().isoformat()
    }
