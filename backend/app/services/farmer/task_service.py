# backend/app/services/farmer/task_service.py

from datetime import datetime, date
from sqlalchemy.orm import Session, joinedload
from uuid import UUID

from app.models.production import UnitTask, UnitStage, ProductionUnit
from app.models.farmer.activity import OperationLog


# ====================================================================
# MAIN: MARK TASK COMPLETE
# ====================================================================

def mark_task_complete(db: Session, task_id: UUID, user_id: UUID | None = None):
    """
    Marks a UnitTask as completed and generates an OperationLog entry.
    Handles:
      - stage progress update
      - auto stage progression
      - auto unit completion
    Returns (task, log) on success.
    """

    # Load task with stage and unit
    task = (
        db.query(UnitTask)
        .options(
            joinedload(UnitTask.stage).joinedload(UnitStage.unit)
        )
        .filter(UnitTask.id == task_id)
        .first()
    )

    if not task:
        return None, None

    # Already completed?
    if task.completed:
        return task, None

    # Mark completion
    task.completed = True
    task.completed_at = datetime.utcnow()

    stage = task.stage
    unit = stage.unit if stage else None

    # Create operation log entry
    op_log = OperationLog(
        production_unit_id=unit.id if unit else None,
        stage_id=stage.id if stage else None,
        task_template_id=task.id,
        performed_on=date.today(),
        status="completed",
        notes=f"Task '{task.title}' marked complete.",
        reported_by_id=user_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(op_log)
    db.add(task)

    # Update stage + auto stage progression
    update_stage_progress(db, stage)

    # Update unit progress + auto-complete if all stages done
    update_unit_progress(db, unit)

    db.commit()
    db.refresh(task)
    db.refresh(op_log)

    return task, op_log


# ====================================================================
# STAGE PROGRESS + AUTO PROGRESSION
# ====================================================================

def update_stage_progress(db: Session, stage: UnitStage):
    """
    Updates stage progress and automatically activates the next stage
    when all stage tasks are completed.
    """
    if not stage:
        return

    tasks = stage.tasks or []
    total = len(tasks)

    if total == 0:
        stage.progress = 0
        stage.status = "pending"
        db.add(stage)
        return

    completed = sum(1 for t in tasks if t.completed)

    # Calculate % progress
    stage.progress = int((completed / total) * 100)

    # Determine stage status
    if completed == total:
        stage.status = "completed"
        db.add(stage)

        # auto-progress only when fully completed
        activate_next_stage(db, stage)

    elif completed > 0:
        stage.status = "active"
    else:
        stage.status = "pending"

    db.add(stage)


def activate_next_stage(db: Session, current_stage: UnitStage):
    """
    Activate next stage when current stage completes.
    """
    unit = current_stage.unit
    if not unit:
        return

    # Ensure stages sorted by order
    stages = sorted(unit.stages, key=lambda s: s.order)

    # Find index of current stage
    try:
        idx = next(i for i, s in enumerate(stages) if s.id == current_stage.id)
    except StopIteration:
        return

    # Last stage? No next stage exists
    if idx >= len(stages) - 1:
        return

    next_stage = stages[idx + 1]

    # Only activate if not already active/completed
    if next_stage.status == "pending":
        next_stage.status = "active"
        next_stage.progress = 0
        db.add(next_stage)


# ====================================================================
# UNIT PROGRESS + AUTO COMPLETION
# ====================================================================

def update_unit_progress(db: Session, unit: ProductionUnit):
    """
    Updates unit progress from all tasks in all stages.
    Also auto-completes unit if all stages are completed.
    """
    if not unit:
        return

    all_tasks = []
    for stage in unit.stages:
        all_tasks.extend(stage.tasks)

    if not all_tasks:
        unit.progress = 0
    else:
        completed = sum(1 for t in all_tasks if t.completed)
        unit.progress = int((completed / len(all_tasks)) * 100)

    db.add(unit)

    # Check for auto-completion
    check_unit_completion(db, unit)


def check_unit_completion(db: Session, unit: ProductionUnit):
    """
    Auto-completes the entire production unit when:
      - all stages are completed
      - all tasks are completed
    """
    if not unit or not unit.stages:
        return

    # If any stage is not completed → do nothing
    for stage in unit.stages:
        if stage.status != "completed":
            return

    # If reached here → all stages completed
    unit.status = "completed"
    unit.progress = 100

    # Only set end_date if not already set
    if not unit.end_date:
        unit.end_date = datetime.utcnow()

    db.add(unit)
