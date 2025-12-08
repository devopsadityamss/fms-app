# backend/app/schemas/farmer/stage.py
from typing import Optional, List
from pydantic import BaseModel
from .task import TaskOut

class StageCreate(BaseModel):
    unit_id: str
    title: str
    order: int = 0

class StageUpdate(BaseModel):
    title: Optional[str] = None
    order: Optional[int] = None
    status: Optional[str] = None
    progress: Optional[int] = None

class StageOut(BaseModel):
    id: str
    unit_id: str
    title: str
    order: int
    status: Optional[str]
    progress: Optional[int]

    class Config:
        orm_mode = True

class StageWithTasksOut(StageOut):
    tasks: List[TaskOut] = []
