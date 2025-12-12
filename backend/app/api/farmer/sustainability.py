# backend/app/api/farmer/sustainability.py

from fastapi import APIRouter
from app.services.farmer.sustainability_service import get_sustainability_summary

router = APIRouter()

@router.get("/sustainability/{unit_id}")
def sustainability_overview(unit_id: int):
    return get_sustainability_summary(unit_id)
