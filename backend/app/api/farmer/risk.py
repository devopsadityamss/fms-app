# backend/app/api/farmer/risk.py

from fastapi import APIRouter
from app.services.farmer.risk_service import compute_unified_risk

# Import required intelligence modules
from app.services.farmer.weather_service import get_current_weather
from app.services.farmer.pest_service import get_pest_intel
from app.services.farmer.health_service import get_crop_health_score
from app.services.farmer.soil_service import get_soil_intelligence
from app.services.farmer.cost_service import get_cost_analysis
from app.services.farmer.market_service import get_market_intelligence

router = APIRouter()


@router.get("/risk/{unit_id}")
def risk_overview(unit_id: int, stage: str, crop: str = "generic"):
    weather = get_current_weather(unit_id)
    pest = get_pest_intel(unit_id, stage, weather)
    health = get_crop_health_score(unit_id, stage, weather)
    soil = get_soil_intelligence(unit_id, crop)
    cost = get_cost_analysis(unit_id, stage, actual_cost_spent=0)
    market = get_market_intelligence(unit_id, crop)

    return compute_unified_risk(
        unit_id=unit_id,
        weather=weather,
        pest_intel=pest,
        health=health,
        soil=soil,
        cost=cost,
        market=market,
    )
