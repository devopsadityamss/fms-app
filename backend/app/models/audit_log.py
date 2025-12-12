# backend/app/models/audit_log.py

from sqlalchemy import Column, String, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base
import uuid

from app.core.database import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    entity_type = Column(String, nullable=False)     # "task" or "project"
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    action = Column(String, nullable=False)          # created, updated, deleted
    detail = Column(String, nullable=True)
    created_at = Column(TIMESTAMP, server_default=text("NOW()"))
