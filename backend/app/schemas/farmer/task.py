# backend/app/schemas/farmer/task.py
from typing import Optional
from datetime import datetime
from pydantic import BaseModel

class TaskCreate(BaseModel):
    stage_id: str
    title: str
    order: int = 0
    completed: Optional[bool] = False
    priority: Optional[str] = None       # "low", "normal", "high"
    due_date: Optional[datetime] = None
    assigned_to: Optional[str] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    order: Optional[int] = None
    completed: Optional[bool] = None
    priority: Optional[str] = None
    due_date: Optional[datetime] = None
    assigned_to: Optional[str] = None

class TaskOut(BaseModel):
    id: str
    stage_id: str
    title: str
    order: int
    completed: bool
    priority: Optional[str]
    due_date: Optional[datetime]
    assigned_to: Optional[str]
    completed_at: Optional[datetime]

    class Config:
        orm_mode = True
