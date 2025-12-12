# backend/app/schemas/farmer/production.py

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel


# ============================================================
# BASE SCHEMAS
# ============================================================

class UnitTaskBase(BaseModel):
    title: str
    order: int
    completed: Optional[bool] = False
    priority: Optional[str] = None
    due_date: Optional[datetime] = None
    assigned_to: Optional[str] = None


class UnitTaskCreate(UnitTaskBase):
    pass


class UnitTask(UnitTaskBase):
    id: str
    completed_at: Optional[datetime] = None

    class Config:
        orm_mode = True


# ------------------------------------------------------------

class UnitStageBase(BaseModel):
    title: str
    order: int


class UnitStageCreate(UnitStageBase):
    tasks: Optional[List[UnitTaskCreate]] = []


class UnitStage(UnitStageBase):
    id: str
    status: Optional[str] = None
    progress: Optional[int] = None
    tasks: List[UnitTask] = []

    class Config:
        orm_mode = True


# ------------------------------------------------------------

class UnitOptionBase(BaseModel):
    option_name: str
    meta: Optional[str] = None


class UnitOption(UnitOptionBase):
    id: str

    class Config:
        orm_mode = True


# ============================================================
# PRODUCTION UNIT SCHEMAS
# ============================================================

class ProductionUnitBase(BaseModel):
    name: str
    practice_type: str
    category: Optional[str] = None
    meta: Optional[str] = None


class ProductionUnitCreate(ProductionUnitBase):
    stages: Optional[List[UnitStageCreate]] = []
    options: Optional[List[UnitOption]] = []


class ProductionUnit(ProductionUnitBase):
    id: str
    user_id: str
    created_at: datetime
    status: Optional[str] = None
    progress: Optional[int] = None
    health_status: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    stages: List[UnitStage] = []
    options: List[UnitOption] = []

    class Config:
        orm_mode = True


# ============================================================
# DASHBOARD RESPONSE SCHEMAS
# ============================================================

class DashboardUnitCard(BaseModel):
    id: str
    name: str
    practice_type: str
    progress: int
    next_task: Optional[str]
    health_status: str


class DashboardSummary(BaseModel):
    total_units: int
    active_units: int
    upcoming_tasks: int
    overdue_tasks: int
    total_expenses: float
    profit_index: float


# ============================================================
# TASK UPDATE PAYLOAD
# ============================================================

class TaskUpdate(BaseModel):
    completed: Optional[bool] = None
    priority: Optional[str] = None
    due_date: Optional[datetime] = None
