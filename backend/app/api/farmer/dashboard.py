# backend/app/api/farmer/dashboard.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from backend.app.crud.farmer import units as crud_units

router = APIRouter(prefix="/dashboard", tags=["farmer-dashboard"])


@router.get("/summary/{user_id}")
async def get_dashboard_summary(user_id: str, db: AsyncSession = Depends(get_db)):
    summary = await crud_units.dashboard_summary(user_id, db)
    return summary
