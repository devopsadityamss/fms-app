# backend/app/services/farmer/task_service.py

from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from backend.app.crud.farmer.tasks import (
    create_task as crud_create_task,
    get_task,
    update_task as crud_update_task,
    delete_task as crud_delete_task,
    list_tasks_by_stage,
)
from backend.app.crud.farmer.stages import get_stage
from backend.app.services.farmer.stage_service import (
    recompute_stage_progress,
)
from backend.app.services.farmer.unit_service import (
    recompute_unit_progress,
)

from backend.app.schemas.farmer.task import TaskCreate, TaskUpdate


# ----------------------------------------------------------
# CREATE TASK + business logic
# ----------------------------------------------------------

async def create_task(payload: TaskCreate, db: AsyncSession):
    # validate stage
    stage = await get_stage(db, payload.stage_id)
    if not stage:
        raise ValueError("Stage not found")

    # Create task via CRUD
    task = await crud_create_task(
        db=db,
        stage_id=payload.stage_id,
        title=payload.title,
        order=payload.order,
        completed=payload.completed,
        priority=payload.priority,
        due_date=payload.due_date,
        assigned_to=payload.assigned_to,
    )

    # Recompute only because NEW task affects progress
    await recompute_stage_progress(stage.id, db)
    await recompute_unit_progress(stage.unit_id, db)

    return task


# ----------------------------------------------------------
# UPDATE TASK + selective business logic
# ----------------------------------------------------------

async def update_task(task_id: str, payload: TaskUpdate, db: AsyncSession):
    task = await get_task(db, task_id)
    if not task:
        return None

    # Determine if progress-related field changed
    progress_related = (
        (payload.completed is not None) or
        (payload.order is not None)  # affects stage-level ordering
    )

    # Update via CRUD
    updated_task = await crud_update_task(db, task_id, payload)

    if progress_related:
        # Recompute progress
        await recompute_stage_progress(task.stage_id, db)

        # Get stage to extract unit_id
        stage = await get_stage(db, task.stage_id)
        await recompute_unit_progress(stage.unit_id, db)

    return updated_task


# ----------------------------------------------------------
# DELETE TASK + business logic
# ----------------------------------------------------------

async def delete_task(task_id: str, db: AsyncSession):
    task = await get_task(db, task_id)
    if not task:
        return None

    stage_id = task.stage_id

    await crud_delete_task(db, task)

    # Recalculate progress since removing a task reduces totals
    await recompute_stage_progress(stage_id, db)

    stage = await get_stage(db, stage_id)
    await recompute_unit_progress(stage.unit_id, db)

    return True
