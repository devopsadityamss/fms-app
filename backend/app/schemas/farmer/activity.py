from uuid import UUID
from typing import Optional, List, Any
from datetime import date, datetime
from pydantic import BaseModel, Field


# ---------------------------------------------------------------
# Shared Base Models
# ---------------------------------------------------------------

class OperationLogBase(BaseModel):
    production_unit_id: UUID
    stage_id: Optional[UUID] = None
    task_template_id: Optional[UUID] = None
    performed_on: date = Field(default_factory=date.today)
    status: Optional[str] = "completed"
    notes: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    extra: Optional[Any] = None


class MaterialUsageBase(BaseModel):
    material_name: str
    material_id: Optional[UUID] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    cost: Optional[float] = None
    extra: Optional[Any] = None


class LabourUsageBase(BaseModel):
    worker_name: Optional[str] = None
    worker_id: Optional[UUID] = None
    hours: Optional[float] = None
    labour_cost: Optional[float] = None
    role: Optional[str] = None
    extra: Optional[Any] = None


class ExpenseBase(BaseModel):
    production_unit_id: Optional[UUID] = None
    amount: float
    currency: Optional[str] = "INR"
    category: Optional[str] = None
    notes: Optional[str] = None
    incurred_on: date = Field(default_factory=date.today)
    extra: Optional[Any] = None


class MediaBase(BaseModel):
    file_name: str
    file_url: Optional[str] = None
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    caption: Optional[str] = None


# ---------------------------------------------------------------
# Create Models
# ---------------------------------------------------------------

class OperationLogCreate(OperationLogBase):
    reported_by_id: Optional[UUID] = None


class MaterialUsageCreate(MaterialUsageBase):
    operation_log_id: UUID


class LabourUsageCreate(LabourUsageBase):
    operation_log_id: UUID


class ExpenseCreate(ExpenseBase):
    operation_log_id: Optional[UUID] = None
    created_by_id: Optional[UUID] = None


class MediaCreate(MediaBase):
    operation_log_id: UUID


# ---------------------------------------------------------------
# Update Models
# ---------------------------------------------------------------

class OperationLogUpdate(BaseModel):
    notes: Optional[str] = None
    status: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    extra: Optional[Any] = None


# ---------------------------------------------------------------
# Response Models
# ---------------------------------------------------------------

class MediaOut(MediaBase):
    id: UUID
    created_at: datetime

    class Config:
        orm_mode = True


class MaterialUsageOut(MaterialUsageBase):
    id: UUID
    created_at: datetime

    class Config:
        orm_mode = True


class LabourUsageOut(LabourUsageBase):
    id: UUID
    created_at: datetime

    class Config:
        orm_mode = True


class ExpenseOut(ExpenseBase):
    id: UUID
    operation_log_id: Optional[UUID]
    created_by_id: Optional[UUID]
    created_at: datetime

    class Config:
        orm_mode = True


class OperationLogOut(OperationLogBase):
    id: UUID
    reported_by_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime

    # child relationships
    materials: List[MaterialUsageOut] = []
    labour: List[LabourUsageOut] = []
    media: List[MediaOut] = []
    expenses: List[ExpenseOut] = []

    class Config:
        orm_mode = True


# ---------------------------------------------------------------
# Helper / List Views
# ---------------------------------------------------------------

class OperationLogList(BaseModel):
    items: List[OperationLogOut]
    total: int

    class Config:
        orm_mode = True
