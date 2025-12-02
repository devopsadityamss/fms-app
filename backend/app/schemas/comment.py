from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

class CommentCreate(BaseModel):
    task_id: UUID
    author_id: Optional[UUID] = None
    text: str

class Comment(BaseModel):
    id: UUID
    task_id: UUID
    author_id: Optional[UUID]
    text: str
    created_at: Optional[datetime]

    class Config:
        orm_mode = True
