# backend/app/crud/farmer/tasks.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List

from backend.app.models.farmer.production import UnitTask
from backend.app.schemas.farmer.production import TaskUpdate
import datetime

# CREATE task helper (not present separately in old file) — we derive from create_production_unit logic
async def create_task(db: AsyncSession, stage_id: str, title: str, order: int = 0,
                      completed: bool = False, priority: Optional[int] = None,
                      due_date = None, assigned_to: Optional[str] = None) -> UnitTask:
    task = UnitTask(
        stage_id=stage_id,
        title=title,
        order=order,
        completed=completed,
        priority=priority,
        due_date=due_date,
        assigned_to=assigned_to,
    )
    db.add(task)
    await db.flush()
    await db.commit()
    await db.refresh(task)
    return task


async def get_task(db: AsyncSession, task_id: str) -> Optional[UnitTask]:
    return await db.get(UnitTask, task_id)


async def list_tasks_by_stage(db: AsyncSession, stage_id: str) -> List[UnitTask]:
    rows = await db.scalars(select(UnitTask).where(UnitTask.stage_id == stage_id))
    return rows.all()


async def list_tasks_by_unit(db: AsyncSession, unit_id: str) -> List[UnitTask]:
    rows = await db.scalars(select(UnitTask).where(UnitTask.unit_id == unit_id))
    return rows.all()


async def update_task(db: AsyncSession, task_id: str, payload: TaskUpdate):
    # existing production.update_task uses task object + payload; keep compatibility
    task = await db.get(UnitTask, task_id)
    if not task:
        return None

    if getattr(payload, "completed", None) is not None:
        task.completed = payload.completed
        if payload.completed:
            task.completed_at = datetime.datetime.utcnow()

    if getattr(payload, "priority", None) is not None:
        task.priority = payload.priority

    if getattr(payload, "due_date", None) is not None:
        task.due_date = payload.due_date

    await db.commit()
    await db.refresh(task)
    return task


async def delete_task(db: AsyncSession, task: UnitTask) -> None:
    await db.delete(task)
    await db.commit()
