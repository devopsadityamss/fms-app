# backend/app/api/farmer/tasks.py

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

from backend.app.schemas.farmer.task import TaskCreate, TaskUpdate, TaskOut
from backend.app.crud.farmer import tasks as crud_tasks
from backend.app.services.farmer import task_service


router = APIRouter(prefix="/tasks", tags=["farmer-tasks"])


@router.post("/stage/{stage_id}", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
async def create_task(stage_id: str, payload: TaskCreate, db: AsyncSession = Depends(get_db)):
    # Ensure payload.stage_id matches stage_id path param (defensive)
    if getattr(payload, "stage_id", None) and payload.stage_id != stage_id:
        raise HTTPException(status_code=400, detail="stage_id mismatch between path and payload")
    # enforce stage id
    payload.stage_id = stage_id
    task = await task_service.create_task(payload, db)
    return task


@router.get("/stage/{stage_id}", response_model=List[TaskOut])
async def list_tasks_for_stage(stage_id: str, db: AsyncSession = Depends(get_db)):
    tasks = await crud_tasks.list_tasks_by_stage(db, stage_id)
    return tasks


@router.patch("/{task_id}", response_model=TaskOut)
async def update_task(task_id: str, payload: TaskUpdate, db: AsyncSession = Depends(get_db)):
    updated = await task_service.update_task(task_id, payload, db)
    if not updated:
        raise HTTPException(status_code=404, detail="Task not found")
    return updated


@router.delete("/{task_id}", status_code=status.HTTP_200_OK)
async def delete_task(task_id: str, db: AsyncSession = Depends(get_db)):
    result = await task_service.delete_task(task_id, db)
    if not result:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"ok": True, "deleted": task_id}



# ============================================================
# ⭐ NEW ENDPOINT — MARK TASK COMPLETE
# ============================================================

@router.post("/{task_id}/complete")
async def complete_task(task_id: str, db: AsyncSession = Depends(get_db)):
    """
    Marks task as completed and creates an operation log.
    Works even though service layer is synchronous.
    """

    # run the sync service inside AsyncSession
    def _complete(sync_session):
        return task_service.mark_task_complete(sync_session, task_id, None)

    task, op_log = await db.run_sync(_complete)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return {
        "task_id": task_id,
        "completed": True,
        "operation_log_id": str(op_log.id) if op_log else None
    }
