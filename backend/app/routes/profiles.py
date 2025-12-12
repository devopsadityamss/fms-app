# backend/app/routes/profiles.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from .. import schemas, crud
from ..database import get_db

router = APIRouter(prefix="/profiles", tags=["profiles"])

@router.get("/", response_model=List[schemas.Profile])
async def read_profiles(limit: int = 50, db: AsyncSession = Depends(get_db)):
    return await crud.list_profiles(db, limit=limit)

@router.get("/{profile_id}", response_model=schemas.Profile)
async def read_profile(profile_id: str, db: AsyncSession = Depends(get_db)):
    p = await crud.get_profile(db, profile_id)
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")
    return p

@router.post("/", response_model=schemas.Profile)
async def create_profile(profile_in: schemas.ProfileCreate, db: AsyncSession = Depends(get_db)):
    return await crud.create_profile(db, profile_in)
