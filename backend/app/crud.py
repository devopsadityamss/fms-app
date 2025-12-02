# backend/app/crud.py
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from . import models, schemas
from uuid import UUID

async def get_profile(db: AsyncSession, profile_id: UUID):
    q = select(models.Profile).where(models.Profile.id == profile_id)
    res = await db.execute(q)
    return res.scalars().first()

async def list_profiles(db: AsyncSession, limit: int = 50):
    q = select(models.Profile).limit(limit)
    res = await db.execute(q)
    return res.scalars().all()

async def create_profile(db: AsyncSession, profile_in: schemas.ProfileCreate):
    obj = models.Profile(email=profile_in.email, full_name=profile_in.full_name, avatar_url=profile_in.avatar_url, role=profile_in.role, metadata={})
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj

# Projects
async def list_projects(db: AsyncSession, limit: int = 50):
    q = select(models.Project).limit(limit)
    res = await db.execute(q)
    return res.scalars().all()

async def get_project(db: AsyncSession, project_id: UUID):
    q = select(models.Project).where(models.Project.id == project_id)
    res = await db.execute(q)
    return res.scalars().first()

async def create_project(db: AsyncSession, project_in: schemas.ProjectCreate):
    obj = models.Project(name=project_in.name, description=project_in.description)
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj

# Tasks
async def list_tasks(db: AsyncSession, project_id=None, limit: int = 200):
    q = select(models.Task)
    if project_id:
        q = q.where(models.Task.project_id == project_id)
    q = q.limit(limit)
    res = await db.execute(q)
    return res.scalars().all()

async def get_task(db: AsyncSession, task_id: UUID):
    q = select(models.Task).where(models.Task.id == task_id)
    res = await db.execute(q)
    return res.scalars().first()

async def create_task(db: AsyncSession, task_in: schemas.TaskCreate):
    obj = models.Task(
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

async def update_task(db: AsyncSession, task_id: UUID, task_in: schemas.TaskUpdate):
    q = select(models.Task).where(models.Task.id == task_id)
    res = await db.execute(q)
    task = res.scalars().first()
    if not task:
        return None
    for field, value in task_in.dict(exclude_unset=True).items():
        setattr(task, field, value)
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task
