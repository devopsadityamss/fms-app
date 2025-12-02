from sqlalchemy import Column, Text, Integer, TIMESTAMP, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from ..core.database import Base
import sqlalchemy as sa
import enum

class TaskStatusEnum(str, enum.Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"

class Task(Base):
    __tablename__ = "tasks"
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"))
    title = Column(Text, nullable=False)
    description = Column(Text)
    status = Column(SAEnum(TaskStatusEnum, name="task_status", native_enum=False), server_default="pending")
    priority = Column(Integer, default=1)
    assignee_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"))
    reporter_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"))
    due_date = Column(TIMESTAMP(timezone=True))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
