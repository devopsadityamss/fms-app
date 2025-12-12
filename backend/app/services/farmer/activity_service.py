# backend/app/services/farmer/activity_service.py

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from uuid import UUID

from app.models.farmer.activity import (
    OperationLog,
    OperationMaterialUsage,
    OperationLabourUsage,
    OperationExpense,
    OperationMedia,
)

from app.schemas.farmer.activity import (
    OperationLogCreate,
    OperationLogUpdate,
    MaterialUsageCreate,
    LabourUsageCreate,
    ExpenseCreate,
    MediaCreate,
)


# ------------------------------------------------------------
# Operation Log
# ------------------------------------------------------------

def create_operation_log(db: Session, data: OperationLogCreate, user_id: UUID | None = None) -> OperationLog:
    """Create an operation log entry."""
    log = OperationLog(
        production_unit_id=data.production_unit_id,
        stage_id=data.stage_id,
        task_template_id=data.task_template_id,
        performed_on=data.performed_on,
        status=data.status,
        notes=data.notes,
        reported_by_id=data.reported_by_id or user_id,
        quantity=data.quantity,
        unit=data.unit,
        extra=data.extra,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def update_operation_log(db: Session, log_id: UUID, data: OperationLogUpdate) -> OperationLog | None:
    """Update fields on an operation log."""
    log = db.query(OperationLog).filter(OperationLog.id == log_id).first()
    if not log:
        return None

    update_data = data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(log, field, value)

    db.commit()
    db.refresh(log)
    return log


def get_operation_log(db: Session, log_id: UUID) -> OperationLog | None:
    """Fetch a single log with all relations."""
    return (
        db.query(OperationLog)
        .options(
            joinedload(OperationLog.materials),
            joinedload(OperationLog.labour),
            joinedload(OperationLog.media),
            joinedload(OperationLog.expenses),
        )
        .filter(OperationLog.id == log_id, OperationLog.is_deleted == False)
        .first()
    )


def list_logs_for_unit(db: Session, production_unit_id: UUID, skip=0, limit=100):
    """Return a paginated list of logs for a production unit."""
    query = (
        db.query(OperationLog)
        .filter(
            OperationLog.production_unit_id == production_unit_id,
            OperationLog.is_deleted == False
        )
        .order_by(OperationLog.performed_on.desc())
    )

    total = query.count()
    items = query.offset(skip).limit(limit).all()

    return {"items": items, "total": total}


# ------------------------------------------------------------
# Material Usage
# ------------------------------------------------------------

def add_material_usage(db: Session, data: MaterialUsageCreate) -> OperationMaterialUsage:
    usage = OperationMaterialUsage(
        operation_log_id=data.operation_log_id,
        material_name=data.material_name,
        material_id=data.material_id,
        quantity=data.quantity,
        unit=data.unit,
        cost=data.cost,
        extra=data.extra,
    )
    db.add(usage)
    db.commit()
    db.refresh(usage)
    return usage


# ------------------------------------------------------------
# Labour Usage
# ------------------------------------------------------------

def add_labour_usage(db: Session, data: LabourUsageCreate) -> OperationLabourUsage:
    usage = OperationLabourUsage(
        operation_log_id=data.operation_log_id,
        worker_name=data.worker_name,
        worker_id=data.worker_id,
        hours=data.hours,
        labour_cost=data.labour_cost,
        role=data.role,
        extra=data.extra,
    )
    db.add(usage)
    db.commit()
    db.refresh(usage)
    return usage


# ------------------------------------------------------------
# Expenses
# ------------------------------------------------------------

def add_expense(db: Session, data: ExpenseCreate, user_id: UUID | None = None) -> OperationExpense:
    exp = OperationExpense(
        operation_log_id=data.operation_log_id,
        production_unit_id=data.production_unit_id,
        amount=data.amount,
        currency=data.currency,
        category=data.category,
        notes=data.notes,
        incurred_on=data.incurred_on,
        created_by_id=data.created_by_id or user_id,
        extra=data.extra,
    )
    db.add(exp)
    db.commit()
    db.refresh(exp)
    return exp


# ------------------------------------------------------------
# Media
# ------------------------------------------------------------

def add_media(db: Session, data: MediaCreate) -> OperationMedia:
    media = OperationMedia(
        operation_log_id=data.operation_log_id,
        file_name=data.file_name,
        file_url=data.file_url,
        mime_type=data.mime_type,
        size_bytes=data.size_bytes,
        caption=data.caption,
    )
    db.add(media)
    db.commit()
    db.refresh(media)
    return media
