from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

class TimelineItemCreate(BaseModel):
    task_id: UUID
    title: str
    description: Optional[str] = None

class TimelineItem(BaseModel):
    id: UUID
    task_id: UUID
    title: str
    description: Optional[str]
    created_at: Optional[datetime]

    class Config:
        orm_mode = True
