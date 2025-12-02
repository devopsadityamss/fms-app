# app/models.py

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID, ENUM
from .db import Base
import datetime

# Correct ENUM to match database values
task_status_enum = ENUM(
    'pending', 'in_progress', 'completed',
    name='task_status',
    create_type=False
)

class Profile(Base):
    __tablename__ = "profiles"

    id = Column(UUID(as_uuid=True), primary_key=True)
    auth_id = Column(UUID(as_uuid=True), unique=True)
    email = Column(Text, nullable=False)
    full_name = Column(Text)
    role = Column(Text, default="user")
    meta = Column(JSON, default={})               # <--- FIXED
    created_at = Column(DateTime)
    updated_at = Column(DateTime)


class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True)
    name = Column(Text, nullable=False)
    description = Column(Text)
    owner_id = Column(UUID(as_uuid=True))
    is_archived = Column(Boolean, default=False)
    meta = Column(JSON, default={})
    created_at = Column(DateTime)
    updated_at = Column(DateTime)



class Task(Base):
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True)
    project_id = Column(UUID(as_uuid=True))
    title = Column(Text, nullable=False)
    description = Column(Text)
    status = Column(task_status_enum, nullable=False, default='pending')
    priority = Column(Integer, default=2)         # 1=low, 2=medium, 3=high
    assignee_id = Column(UUID(as_uuid=True))
    reporter_id = Column(UUID(as_uuid=True))
    due_date = Column(DateTime)
    meta = Column(JSON, default={})               # <--- FIXED
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
