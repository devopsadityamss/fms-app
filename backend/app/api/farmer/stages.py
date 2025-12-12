# backend/app/api/farmer/stages.py

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

from backend.app.schemas.farmer.stage import StageCreate, StageUpdate, StageWithTasksOut, StageOut
from backend.app.crud.farmer import stages as crud_stages
from backend.app.services.farmer import stage_service

router = APIRouter(prefix="/stages", tags=["farmer-stages"])


@router.post("/", response_model=StageOut, status_code=status.HTTP_201_CREATED)
async def create_stage(payload: StageCreate, db: AsyncSession = Depends(get_db)):
    # validate unit exists via CRUD (get_production_unit)
    from backend.app.crud.farmer import units as crud_units
    unit = await crud_units.get_production_unit(payload.unit_id, db)
    if not unit:
        raise HTTPException(status_code=404, detail="Production unit not found")
    stage = await stage_service.create_stage(payload, db)
    return stage


@router.get("/unit/{unit_id}", response_model=List[StageWithTasksOut])
async def list_stages(unit_id: str, db: AsyncSession = Depends(get_db)):
    stages = await crud_stages.list_stages_by_unit(db, unit_id)
    # ensure tasks are loaded (eager)
    out = []
    for s in stages:
        # `s.tasks` should already be accessible via relationship if CRUD populated; otherwise fetch tasks
        tasks = getattr(s, "tasks", None)
        if tasks is None:
            from backend.app.crud.farmer import tasks as crud_tasks
            tasks = await crud_tasks.list_tasks_by_stage(db, s.id)
        s.tasks = tasks
        out.append(s)
    return out


@router.get("/{stage_id}", response_model=StageWithTasksOut)
async def get_stage(stage_id: str, db: AsyncSession = Depends(get_db)):
    stage = await crud_stages.get_stage(db, stage_id)
    if not stage:
        raise HTTPException(status_code=404, detail="Stage not found")
    # ensure tasks loaded
    from backend.app.crud.farmer import tasks as crud_tasks
    stage.tasks = await crud_tasks.list_tasks_by_stage(db, stage.id)
    return stage


@router.patch("/{stage_id}", response_model=StageOut)
async def update_stage(stage_id: str, payload: StageUpdate, db: AsyncSession = Depends(get_db)):
    stage = await crud_stages.get_stage(db, stage_id)
    if not stage:
        raise HTTPException(status_code=404, detail="Stage not found")
    updated = await stage_service.update_stage(stage_id, payload, db)
    return updated


@router.delete("/{stage_id}", status_code=status.HTTP_200_OK)
async def delete_stage(stage_id: str, db: AsyncSession = Depends(get_db)):
    stage = await crud_stages.get_stage(db, stage_id)
    if not stage:
        raise HTTPException(status_code=404, detail="Stage not found")
    await stage_service.delete_stage(stage_id, db)
    return {"ok": True, "deleted": stage_id}
