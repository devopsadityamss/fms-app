# backend/app/api/farmer/recommendation.py

from fastapi import APIRouter

from app.services.farmer.recommendation_service import get_recommendation_report

# Required service imports
from app.services.farmer.risk_service import compute_unified_risk
from app.services.farmer.health_service import get_crop_health_score
from app.services.farmer.weather_service import get_current_weather
from app.services.farmer.soil_service import get_soil_intelligence
from app.services.farmer.pest_service import get_pest_intel
from app.services.farmer.cost_service import get_cost_analysis
from app.services.farmer.market_service import get_market_intelligence

router = APIRouter()


@router.get("/recommendation/{unit_id}")
def recommendation_overview(unit_id: int, stage: str, crop: str = "generic"):

    weather = get_current_weather(unit_id)
    soil = get_soil_intelligence(unit_id, crop)
    health = get_crop_health_score(unit_id, stage, weather)
    pest = get_pest_intel(unit_id, stage, weather)
    cost = get_cost_analysis(unit_id, stage, actual_cost_spent=0)
    market = get_market_intelligence(unit_id, crop)

    # risk engine
    risk = compute_unified_risk(
        unit_id,
        weather=weather,
        pest_intel=pest,
        health=health,
        soil=soil,
        cost=cost,
        market=market
    )

    return get_recommendation_report(
        unit_id=unit_id,
        stage=stage,
        risk=risk,
        health=health,
        soil=soil,
        weather=weather,
        pest_intel=pest,
    )
