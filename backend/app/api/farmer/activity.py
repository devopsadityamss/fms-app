from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.db.session import get_db
from app.services.farmer import activity_service

from app.schemas.farmer.activity import (
    OperationLogCreate,
    OperationLogUpdate,
    OperationLogOut,
    OperationLogList,
    MaterialUsageCreate,
    MaterialUsageOut,
    LabourUsageCreate,
    LabourUsageOut,
    ExpenseCreate,
    ExpenseOut,
    MediaCreate,
    MediaOut,
)

# If you have a real dependency, import it:
# from app.api.deps import get_current_user

router = APIRouter(prefix="/activity", tags=["Farmer Activity"])


# -------------------------------------------------------------
# Operation Log
# -------------------------------------------------------------

@router.post("/log", response_model=OperationLogOut)
def create_operation_log(
    data: OperationLogCreate,
    db: Session = Depends(get_db),
    # current_user=Depends(get_current_user)   # enable if needed
):
    # user_id = current_user.id if current_user else None
    created_log = activity_service.create_operation_log(db, data)
    return created_log


@router.patch("/log/{log_id}", response_model=OperationLogOut)
def update_operation_log(
    log_id: UUID,
    data: OperationLogUpdate,
    db: Session = Depends(get_db),
):
    updated = activity_service.update_operation_log(db, log_id, data)
    if not updated:
        raise HTTPException(status_code=404, detail="Operation log not found")
    return updated


@router.get("/log/{log_id}", response_model=OperationLogOut)
def get_operation_log(
    log_id: UUID,
    db: Session = Depends(get_db),
):
    log = activity_service.get_operation_log(db, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    return log


@router.get("/{unit_id}/logs", response_model=OperationLogList)
def list_unit_logs(
    unit_id: UUID,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    result = activity_service.list_logs_for_unit(db, unit_id, skip=skip, limit=limit)
    return result


# -------------------------------------------------------------
# Material Usage
# -------------------------------------------------------------

@router.post("/material", response_model=MaterialUsageOut)
def add_material_usage(
    data: MaterialUsageCreate,
    db: Session = Depends(get_db),
):
    return activity_service.add_material_usage(db, data)


# -------------------------------------------------------------
# Labour Usage
# -------------------------------------------------------------

@router.post("/labour", response_model=LabourUsageOut)
def add_labour_usage(
    data: LabourUsageCreate,
    db: Session = Depends(get_db),
):
    return activity_service.add_labour_usage(db, data)


# -------------------------------------------------------------
# Expense
# -------------------------------------------------------------

@router.post("/expense", response_model=ExpenseOut)
def add_expense(
    data: ExpenseCreate,
    db: Session = Depends(get_db),
    # current_user=Depends(get_current_user)
):
    # user_id = current_user.id if current_user else None
    return activity_service.add_expense(db, data)


# -------------------------------------------------------------
# Media Upload (metadata only)
# -------------------------------------------------------------

@router.post("/media", response_model=MediaOut)
def add_media(
    data: MediaCreate,
    db: Session = Depends(get_db),
):
    return activity_service.add_media(db, data)
