# backend/app/schemas.py
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from uuid import UUID
import enum

class TaskStatusEnum(str, enum.Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"

class ProfileBase(BaseModel):
    avatar_url: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[str] = None

class ProfileCreate(ProfileBase):
    email: EmailStr

class ProfileUpdate(ProfileBase):
    email: Optional[EmailStr] = None

class Profile(ProfileBase):
    id: UUID
    email: EmailStr
    metadata: Optional[dict] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True

class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None

class ProjectCreate(ProjectBase):
    pass

class Project(ProjectBase):
    id: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True

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
