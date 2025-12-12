# backend/app/api/farmer/dashboard.py

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from app.services.farmer.dashboard_intel_service import get_dashboard_for_unit
from fastapi import Depends   # ← ADDED
from sqlalchemy.ext.asyncio import AsyncSession   # ← ADDED
from app.core.database import get_db   # ← ADDED
from backend.app.crud.farmer import units as crud_units   # ← ADDED

router = APIRouter()

@router.get("/dashboard/{unit_id}")
def api_get_dashboard(unit_id: str):
    res = get_dashboard_for_unit(unit_id)
    if res.get("status") == "unit_not_found":
        raise HTTPException(status_code=404, detail="unit_not_found")
    return res


@router.get("/summary/{user_id}")
async def get_dashboard_summary(user_id: str, db: AsyncSession = Depends(get_db)):
    summary = await crud_units.dashboard_summary(user_id, db)
    return summary