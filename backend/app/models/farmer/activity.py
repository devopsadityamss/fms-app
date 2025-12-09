# backend/app/models/farmer/activity.py
import uuid
from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text, Boolean, Float
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base_class import Base  # adjust import path if your Base is elsewhere


class OperationLog(Base):
    __tablename__ = "operation_log"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # 🔥 FIXED foreign key table names
    production_unit_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("production_units.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stage_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("unit_stages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    task_template_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("unit_tasks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    performed_on = Column(Date, nullable=False, default=datetime.utcnow)
    status = Column(String(32), nullable=False, default="completed")
    notes = Column(Text, nullable=True)

    reported_by_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    quantity = Column(Float, nullable=True)
    unit = Column(String(32), nullable=True)

    extra = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)

    # 🔥 FIXED back_populates to match actual models
    production_unit = relationship("ProductionUnit", back_populates="operation_logs")
    stage = relationship("UnitStage", back_populates="operation_logs")
    task_template = relationship("UnitTask", back_populates="operation_logs")
    reported_by = relationship("User", foreign_keys=[reported_by_id])


class OperationMaterialUsage(Base):
    __tablename__ = "operation_material_usage"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    operation_log_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("operation_log.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    material_name = Column(String(255), nullable=False)
    material_id = Column(PG_UUID(as_uuid=True), nullable=True)
    quantity = Column(Float, nullable=True)
    unit = Column(String(32), nullable=True)
    cost = Column(Float, nullable=True)
    extra = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    operation_log = relationship("OperationLog", back_populates="materials")


class OperationLabourUsage(Base):
    __tablename__ = "operation_labour_usage"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    operation_log_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("operation_log.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    worker_name = Column(String(255), nullable=True)
    worker_id = Column(PG_UUID(as_uuid=True), nullable=True)
    hours = Column(Float, nullable=True)
    labour_cost = Column(Float, nullable=True)
    role = Column(String(128), nullable=True)
    extra = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    operation_log = relationship("OperationLog", back_populates="labour")


class OperationExpense(Base):
    __tablename__ = "operation_expense"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    operation_log_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("operation_log.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    production_unit_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("production_units.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    amount = Column(Float, nullable=False, default=0.0)
    currency = Column(String(8), nullable=True, default="INR")
    category = Column(String(128), nullable=True)
    notes = Column(Text, nullable=True)
    incurred_on = Column(Date, nullable=False, default=datetime.utcnow)
    created_by_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    extra = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    operation_log = relationship("OperationLog", back_populates="expenses")
    production_unit = relationship("ProductionUnit")


class OperationMedia(Base):
    __tablename__ = "operation_media"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    operation_log_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("operation_log.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_name = Column(String(255), nullable=False)
    file_url = Column(Text, nullable=True)
    mime_type = Column(String(128), nullable=True)
    size_bytes = Column(Integer, nullable=True)
    caption = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    operation_log = relationship("OperationLog", back_populates="media")
