# backend/app/models.py
from sqlalchemy import Column, Text, Integer, TIMESTAMP, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from .database import Base
import enum
import sqlalchemy as sa

# Must match DB enum values
class TaskStatusEnum(str, enum.Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(UUID(as_uuid=True), primary_key=True)

    # REMOVED: metadata / profile_metadata (not in DB, not needed)

    created_at = Column(TIMESTAMP(timezone=True))
    updated_at = Column(TIMESTAMP(timezone=True))
    avatar_url = Column(Text)

    email = Column(Text, unique=True)
    full_name = Column(Text)
    role = Column(Text)


class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    name = Column(Text, nullable=False)
    description = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class Task(Base):
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))

    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"))

    title = Column(Text, nullable=False)
    description = Column(Text)

    status = Column(
        SAEnum(TaskStatusEnum, name="task_status", native_enum=False),
        server_default="pending"
    )

    priority = Column(Integer, default=1)

    assignee_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"))
    reporter_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"))

    due_date = Column(TIMESTAMP(timezone=True))

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
