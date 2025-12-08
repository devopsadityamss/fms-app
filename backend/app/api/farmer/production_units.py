# backend/app/api/farmer/production_units.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

from backend.app.schemas.farmer.production import (
    ProductionUnitCreate,
    ProductionUnit as ProductionUnitOut,
    UnitUpdate as ProductionUnitUpdate,
)
from backend.app.crud.farmer import units as crud_units
from backend.app.services.farmer import unit_service

router = APIRouter(prefix="/units", tags=["farmer-units"])


@router.post("/", response_model=ProductionUnitOut, status_code=status.HTTP_201_CREATED)
async def create_unit(payload: ProductionUnitCreate, db: AsyncSession = Depends(get_db)):
    unit = await crud_units.create_production_unit(payload_user_id(payload), payload, db) if False else None
    # The above line is a noop kept to avoid linters complaining about payload_user_id helper not present.
    # Use the explicit flow below.

    # NOTE: ProductionUnitCreate does not include user_id in schema; expect user_id from payload meta or auth.
    # Try to read from payload.meta.user_id if present; otherwise call crud with a placeholder.
    # Preferably, your frontend supplies user_id in request context. Here we use payload.meta['user_id'] if exists.
    user_id = None
    try:
        # payload.meta may be a JSON string — try to pull user_id if provided in meta dict
        meta = getattr(payload, "meta", None)
        if isinstance(meta, dict) and meta.get("user_id"):
            user_id = meta.get("user_id")
    except Exception:
        user_id = None

    # If no user_id found, raise — your system expects user_id in create flows
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id must be provided in payload.meta or set by auth layer")

    unit = await crud_units.create_production_unit(user_id, payload, db)

    # recompute progress (safe no-op if no tasks)
    await unit_service.recompute_unit_progress(unit.id, db)

    return unit


@router.get("/", response_model=List[ProductionUnitOut])
async def list_units(user_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    # if no user_id provided, return all units (admin use); otherwise filter
    if user_id:
        units = await crud_units.list_units_for_dashboard(user_id, db)
        # list_units_for_dashboard returns lightweight dicts — convert/return raw
        # But the route signature expects ProductionUnitOut (full object) — to keep consistent, load full units when user_id provided
        results = []
        for u in units:
            full = await crud_units.get_production_unit(u["id"], db)
            if full:
                results.append(full)
        return results
    # fallback: list all units (admin)
    # Here we fetch all production units (no filter)
    # crud_units does not have list_all; reuse list_units_for_dashboard with a placeholder approach:
    # fetch all by selecting from DB directly (fallback to original crud function)
    raise HTTPException(status_code=400, detail="user_id is required to list units")


@router.get("/{unit_id}", response_model=ProductionUnitOut)
async def get_unit(unit_id: str, db: AsyncSession = Depends(get_db)):
    unit = await crud_units.get_production_unit(unit_id, db)
    if not unit:
        raise HTTPException(status_code=404, detail="Production unit not found")
    return unit


@router.patch("/{unit_id}", response_model=ProductionUnitOut)
async def update_unit(unit_id: str, payload: ProductionUnitUpdate, db: AsyncSession = Depends(get_db)):
    unit = await crud_units.get_production_unit(unit_id, db)
    if not unit:
        raise HTTPException(status_code=404, detail="Production unit not found")
    # update fields (we expect UnitUpdate to be defined inside production schema as UnitUpdate or UnitUpdate-like)
    # If your schema uses a different name, adapt accordingly.
    updated = await crud_units.update_unit(db, unit, payload)
    # recompute progress if necessary
    await unit_service.recompute_unit_progress(unit_id, db)
    return updated


@router.delete("/{unit_id}", status_code=status.HTTP_200_OK)
async def delete_unit(unit_id: str, db: AsyncSession = Depends(get_db)):
    unit = await crud_units.get_production_unit(unit_id, db)
    if not unit:
        raise HTTPException(status_code=404, detail="Production unit not found")
    await crud_units.delete_unit(db, unit)
    return {"ok": True, "deleted": unit_id}
