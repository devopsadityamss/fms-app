# backend/app/models/production.py

from sqlalchemy import (
    Column, String, Integer, ForeignKey, DateTime,
    Text, Boolean
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

from app.core.database import Base

def gen_uuid():
    return str(uuid.uuid4())


# ============================================================
# PRODUCTION UNIT (Expanded for dashboard & lifecycle tracking)
# ============================================================
class ProductionUnit(Base):
    __tablename__ = "production_units"

    id = Column(PG_UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(PG_UUID(as_uuid=False), nullable=False, index=True)
    name = Column(String, nullable=False)
    practice_type = Column(String, nullable=False)
    category = Column(String, nullable=True)

    meta = Column(Text, nullable=True)  # JSON string

    created_at = Column(DateTime, default=datetime.utcnow)

    # ⭐ NEW FIELDS (NON-BREAKING)
    status = Column(String, default="active")           # active, paused, archived
    progress = Column(Integer, default=0)               # 0–100%
    health_status = Column(String, default="unknown")   # good / warning / critical
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)

    stages = relationship("UnitStage", back_populates="unit", cascade="all, delete-orphan")
    options = relationship("UnitOption", back_populates="unit", cascade="all, delete-orphan")

    # ⭐ NEW — required for OperationLog relationship
    operation_logs = relationship(
        "OperationLog",
        back_populates="production_unit",
        cascade="all, delete-orphan"
    )


# ============================================================
# OPTIONS (unchanged)
# ============================================================
class UnitOption(Base):
    __tablename__ = "unit_options"

    id = Column(PG_UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    unit_id = Column(PG_UUID(as_uuid=False), ForeignKey("production_units.id"), nullable=False)
    option_name = Column(String, nullable=False)
    meta = Column(Text, nullable=True)

    unit = relationship("ProductionUnit", back_populates="options")


# ============================================================
# STAGES (Expanded with status + progress)
# ============================================================
class UnitStage(Base):
    __tablename__ = "unit_stages"

    id = Column(PG_UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    unit_id = Column(PG_UUID(as_uuid=False), ForeignKey("production_units.id"), nullable=False)
    title = Column(String, nullable=False)
    order = Column(Integer, nullable=False, default=0)

    # ⭐ NEW
    status = Column(String, default="pending")   # pending, active, completed
    progress = Column(Integer, default=0)        # % based on tasks

    unit = relationship("ProductionUnit", back_populates="stages")
    tasks = relationship("UnitTask", back_populates="stage", cascade="all, delete-orphan")

    # ⭐ NEW — needed because OperationLog has stage_id → UnitStage
    operation_logs = relationship(
        "OperationLog",
        back_populates="stage",
        cascade="all, delete-orphan"
    )


# ============================================================
# TASKS (Expanded with dates, assignee, priority)
# ============================================================
class UnitTask(Base):
    __tablename__ = "unit_tasks"

    id = Column(PG_UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    stage_id = Column(PG_UUID(as_uuid=False), ForeignKey("unit_stages.id"), nullable=False)
    title = Column(String, nullable=False)
    order = Column(Integer, nullable=False, default=0)
    completed = Column(Boolean, default=False)

    # ⭐ NEW FIELDS
    priority = Column(String, default="normal")            # low, normal, high
    due_date = Column(DateTime, nullable=True)
    assigned_to = Column(String, nullable=True)           # worker/supervisor id
    completed_at = Column(DateTime, nullable=True)

    stage = relationship("UnitStage", back_populates="tasks")

    # ⭐ NEW — needed because OperationLog has task_template_id → UnitTask
    operation_logs = relationship(
        "OperationLog",
        back_populates="task_template",
        cascade="all, delete-orphan"
    )
