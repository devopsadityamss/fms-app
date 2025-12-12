# backend/app/api/farmer/market.py

from fastapi import APIRouter
from app.services.farmer.market_service import get_market_intelligence

router = APIRouter()

@router.get("/market/{unit_id}")
def market_overview(unit_id: int, crop: str = "generic"):
    return get_market_intelligence(unit_id, crop)
