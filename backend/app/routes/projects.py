# backend/app/routes/projects.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from .. import schemas, crud
from ..database import get_db

router = APIRouter(prefix="/projects", tags=["projects"])

@router.get("/", response_model=List[schemas.Project])
async def read_projects(limit: int = 50, db: AsyncSession = Depends(get_db)):
    return await crud.list_projects(db, limit=limit)

@router.get("/{project_id}", response_model=schemas.Project)
async def read_project(project_id: str, db: AsyncSession = Depends(get_db)):
    p = await crud.get_project(db, project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    return p

@router.post("/", response_model=schemas.Project)
async def create_project(project_in: schemas.ProjectCreate, db: AsyncSession = Depends(get_db)):
    return await crud.create_project(db, project_in)
