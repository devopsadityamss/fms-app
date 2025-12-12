# backend/app/api/farmer/intelligence.py

from fastapi import APIRouter
from app.services.farmer.intelligence_engine_service import get_full_intelligence

router = APIRouter()

@router.get("/intelligence/{unit_id}")
def intelligence_overview(unit_id: int, stage: str, crop: str = "generic"):
    # current_stock left optional for now
    return get_full_intelligence(unit_id=unit_id, stage=stage, current_stock={}, crop=crop)
