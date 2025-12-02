from sqlalchemy import Column, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from ..core.database import Base
import sqlalchemy as sa

class Profile(Base):
    __tablename__ = "profiles"
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    metadata = Column(JSONB)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    avatar_url = Column(Text)
    email = Column(Text, unique=True)
    full_name = Column(Text)
    role = Column(Text)
