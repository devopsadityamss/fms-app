# backend/app/services/farmer/stage_service.py

from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.crud.farmer.stages import (
    create_stage as crud_create_stage,
    get_stage,
    list_stages_by_unit,
    update_stage as crud_update_stage,
    delete_stage as crud_delete_stage,
)
from backend.app.services.farmer.unit_service import (
    recompute_unit_progress,
)

from backend.app.schemas.farmer.stage import StageCreate, StageUpdate


# ----------------------------------------------------------
# CREATE STAGE
# ----------------------------------------------------------

async def create_stage(payload: StageCreate, db: AsyncSession):
    stage = await crud_create_stage(db, payload)
    await recompute_unit_progress(payload.unit_id, db)
    return stage


# ----------------------------------------------------------
# UPDATE STAGE
# ----------------------------------------------------------

async def update_stage(stage_id: str, payload: StageUpdate, db: AsyncSession):
    stage = await get_stage(db, stage_id)
    if not stage:
        return None

    updated = await crud_update_stage(db, stage, payload)

    # Stage metadata affects unit progress sometimes
    await recompute_unit_progress(stage.unit_id, db)
    return updated


# ----------------------------------------------------------
# DELETE STAGE
# ----------------------------------------------------------

async def delete_stage(stage_id: str, db: AsyncSession):
    stage = await get_stage(db, stage_id)
    if not stage:
        return None

    unit_id = stage.unit_id
    await crud_delete_stage(db, stage)

    await recompute_unit_progress(unit_id, db)
    return True


# ----------------------------------------------------------
# PROGRESS RECALC
# ----------------------------------------------------------

async def recompute_stage_progress(stage_id: str, db: AsyncSession):
    stage = await get_stage(db, stage_id)
    if not stage:
        return None

    tasks = stage.tasks

    if not tasks:
        stage.progress = 0
        stage.status = "pending"
    else:
        completed = sum(1 for t in tasks if t.completed)
        total = len(tasks)
        stage.progress = int((completed / total) * 100)

        if stage.progress == 100:
            stage.status = "completed"
        elif completed > 0:
            stage.status = "active"
        else:
            stage.status = "pending"

    db.add(stage)
    await db.commit()
    return stage
