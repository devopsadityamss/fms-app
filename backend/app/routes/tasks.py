# backend/app/routes/tasks.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID
from .. import schemas, crud
from ..database import get_db

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.get("/", response_model=List[schemas.Task])
async def list_tasks(project_id: UUID = None, limit: int = 200, db: AsyncSession = Depends(get_db)):
    return await crud.list_tasks(db, project_id=project_id, limit=limit)

@router.get("/{task_id}", response_model=schemas.Task)
async def get_task(task_id: UUID, db: AsyncSession = Depends(get_db)):
    t = await crud.get_task(db, task_id)
    if not t:
        raise HTTPException(status_code=404, detail="Task not found")
    return t

@router.post("/", response_model=schemas.Task)
async def create_task(task_in: schemas.TaskCreate, db: AsyncSession = Depends(get_db)):
    return await crud.create_task(db, task_in)

@router.put("/{task_id}", response_model=schemas.Task)
async def update_task(task_id: UUID, task_in: schemas.TaskUpdate, db: AsyncSession = Depends(get_db)):
    updated = await crud.update_task(db, task_id, task_in)
    if not updated:
        raise HTTPException(status_code=404, detail="Task not found")
    return updated
