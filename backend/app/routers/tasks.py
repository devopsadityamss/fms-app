from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from ..core.database import get_db
from ..models import Task as TaskModel
from ..schemas.task import Task, TaskCreate, TaskUpdate
from sqlalchemy import select
from ..core.auth import require_user

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.get("/", response_model=List[Task])
async def list_tasks(
    project_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    q = select(TaskModel)
    if project_id:
        q = q.where(TaskModel.project_id == project_id)
    if status:
        q = q.where(TaskModel.status == status)
    q = q.order_by(TaskModel.created_at.desc())
    res = await db.execute(q)
    return res.scalars().all()

@router.post(
    "/", 
    response_model=Task,
    dependencies=[Depends(require_user)]
)
async def create_task(task_in: TaskCreate, db: AsyncSession = Depends(get_db)):
    obj = TaskModel(
        project_id=task_in.project_id,
        title=task_in.title,
        description=task_in.description,
        priority=task_in.priority,
        assignee_id=task_in.assignee_id,
        reporter_id=task_in.reporter_id,
        due_date=task_in.due_date
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj

@router.get("/{task_id}", response_model=Task)
async def get_task(task_id: str, db: AsyncSession = Depends(get_db)):
    q = select(TaskModel).where(TaskModel.id == task_id)
    res = await db.execute(q)
    t = res.scalars().first()
    if not t:
        raise HTTPException(status_code=404, detail="Task not found")
    return t

@router.put(
    "/{task_id}",
    response_model=Task,
    dependencies=[Depends(require_user)]
)
async def update_task(task_id: str, task_in: TaskUpdate, db: AsyncSession = Depends(get_db)):
    q = select(TaskModel).where(TaskModel.id == task_id)
    res = await db.execute(q)
    task = res.scalars().first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    for field, value in task_in.dict(exclude_unset=True).items():
        setattr(task, field, value)
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task

@router.delete(
    "/{task_id}",
    dependencies=[Depends(require_user)]
)
async def delete_task(task_id: str, db: AsyncSession = Depends(get_db)):
    q = select(TaskModel).where(TaskModel.id == task_id)
    res = await db.execute(q)
    t = res.scalars().first()
    if not t:
        raise HTTPException(status_code=404, detail="Task not found")
    await db.delete(t)
    await db.commit()
    return {"ok": True}
