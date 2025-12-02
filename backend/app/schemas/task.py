from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime
import enum

class TaskStatusEnum(str, enum.Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    priority: Optional[int] = 1
    due_date: Optional[datetime] = None

class TaskCreate(TaskBase):
    project_id: UUID
    assignee_id: Optional[UUID] = None
    reporter_id: Optional[UUID] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatusEnum] = None
    priority: Optional[int] = None
    assignee_id: Optional[UUID] = None
    reporter_id: Optional[UUID] = None
    due_date: Optional[datetime] = None
    project_id: Optional[UUID] = None

class Task(TaskBase):
    id: UUID
    project_id: UUID
    status: TaskStatusEnum
    assignee_id: Optional[UUID]
    reporter_id: Optional[UUID]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True
