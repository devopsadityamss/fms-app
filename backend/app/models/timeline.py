from sqlalchemy import Column, Text, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from ..core.database import Base
import sqlalchemy as sa

class TimelineItem(Base):
    __tablename__ = "timeline"
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"))
    title = Column(Text)
    description = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
