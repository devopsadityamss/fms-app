from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

class AttachmentCreate(BaseModel):
    task_id: UUID
    path: str
    name: Optional[str] = None

class Attachment(BaseModel):
    id: UUID
    task_id: UUID
    path: str
    name: Optional[str]
    created_at: Optional[datetime]

    class Config:
        orm_mode = True
