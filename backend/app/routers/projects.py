from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from ..core.database import get_db
from ..models import Project as ProjectModel
from ..schemas.project import Project, ProjectCreate
from sqlalchemy import select
from ..core.auth import require_user

router = APIRouter(prefix="/projects", tags=["projects"])

@router.get("/", response_model=List[Project])
async def list_projects(db: AsyncSession = Depends(get_db)):
    q = select(ProjectModel)
    res = await db.execute(q)
    return res.scalars().all()

@router.post(
    "/", 
    response_model=Project,
    dependencies=[Depends(require_user)]
)
async def create_project(project_in: ProjectCreate, db: AsyncSession = Depends(get_db)):
    obj = ProjectModel(name=project_in.name, description=project_in.description)
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj

@router.get("/{project_id}", response_model=Project)
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    q = select(ProjectModel).where(ProjectModel.id == project_id)
    res = await db.execute(q)
    p = res.scalars().first()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    return p

@router.delete(
    "/{project_id}",
    dependencies=[Depends(require_user)]
)
async def delete_project(project_id: str, db: AsyncSession = Depends(get_db)):
    q = select(ProjectModel).where(ProjectModel.id == project_id)
    res = await db.execute(q)
    p = res.scalars().first()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    await db.delete(p)
    await db.commit()
    return {"ok": True}
