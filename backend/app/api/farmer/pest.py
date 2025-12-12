# backend/app/api/farmer/pest.py

from fastapi import APIRouter
from app.services.farmer.pest_service import get_pest_intel
from app.services.farmer.weather_service import get_current_weather

router = APIRouter()

@router.get("/pest/{unit_id}")
def pest_overview(unit_id: int, stage: str):
    weather = get_current_weather(unit_id)
    return get_pest_intel(unit_id, stage, weather)
