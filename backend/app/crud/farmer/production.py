from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from backend.app.models.farmer.production import (
    ProductionUnit,
    UnitStage,
    UnitTask,
    UnitOption,
)

from backend.app.schemas.farmer.production import (
    ProductionUnitCreate,
    TaskUpdate,
)

import datetime


# ============================================================
# HELPERS
# ============================================================

async def compute_unit_progress(unit_id: str, db: AsyncSession) -> tuple[int, str, str]:
    """
    Computes:
    - overall progress %
    - next task name
    - health status
    """
    stages = await db.scalars(select(UnitStage).where(UnitStage.unit_id == unit_id))
    stages = stages.all()

    tasks = []
    for s in stages:
        t = await db.scalars(select(UnitTask).where(UnitTask.stage_id == s.id))
        tasks.extend(t.all())

    if not tasks:
        return 0, None, "warning"

    completed = sum(1 for t in tasks if t.completed)
    total = len(tasks)

    progress = int((completed / total) * 100)

    pending = sorted(
        [t for t in tasks if not t.completed],
        key=lambda x: (x.stage_id, x.order),
    )

    next_task = pending[0].title if pending else None

    if progress < 30:
        health = "warning"
    elif progress < 70:
        health = "good"
    else:
        health = "excellent"

    return progress, next_task, health


# ============================================================
# CREATE PRODUCTION UNIT
# ============================================================

async def create_production_unit(user_id: str, payload: ProductionUnitCreate, db: AsyncSession):
    unit = ProductionUnit(
        user_id=user_id,
        name=payload.name,
        practice_type=payload.practice_type,
        category=payload.category,
        meta=payload.meta,
        created_at=datetime.datetime.utcnow(),
    )

    db.add(unit)
    await db.flush()  # ensures `unit.id` is generated

    # Create options
    for opt in payload.options or []:
        new_opt = UnitOption(
            unit_id=unit.id,
            option_name=opt.option_name,
            meta=opt.meta,
        )
        db.add(new_opt)

    # Create stages + tasks
    for st in payload.stages or []:
        stage = UnitStage(
            unit_id=unit.id,
            title=st.title,
            order=st.order,
        )
        db.add(stage)
        await db.flush()

        for t in st.tasks or []:
            task = UnitTask(
                stage_id=stage.id,
                title=t.title,
                order=t.order,
                completed=t.completed,
                priority=t.priority,
                due_date=t.due_date,
                assigned_to=t.assigned_to,
            )
            db.add(task)

    await db.commit()
    return unit


# ============================================================
# GET FULL UNIT DETAILS
# ============================================================

async def get_production_unit(unit_id: str, db: AsyncSession):
    unit = await db.get(ProductionUnit, unit_id)
    if not unit:
        return None

    # eager load children
    stages = await db.scalars(select(UnitStage).where(UnitStage.unit_id == unit.id))
    unit.stages = stages.all()

    for st in unit.stages:
        tasks = await db.scalars(select(UnitTask).where(UnitTask.stage_id == st.id))
        st.tasks = tasks.all()

    options = await db.scalars(select(UnitOption).where(UnitOption.unit_id == unit.id))
    unit.options = options.all()

    return unit


# ============================================================
# LIST UNITS FOR DASHBOARD
# ============================================================

async def list_units_for_dashboard(user_id: str, db: AsyncSession):
    units = await db.scalars(select(ProductionUnit).where(ProductionUnit.user_id == user_id))
    units = units.all()

    results = []

    for u in units:
        progress, next_task, health = await compute_unit_progress(u.id, db)

        results.append({
            "id": u.id,
            "name": u.name,
            "practice_type": u.practice_type,
            "progress": progress,
            "next_task": next_task,
            "health_status": health,
        })

    return results


# ============================================================
# DASHBOARD SUMMARY
# ============================================================

async def dashboard_summary(user_id: str, db: AsyncSession):
    units = await db.scalars(select(ProductionUnit).where(ProductionUnit.user_id == user_id))
    units = units.all()

    total_units = len(units)

    # simple placeholder values (can refine later)
    active_units = total_units
    total_tasks = 0
    upcoming_tasks = 0

    for u in units:
        st = await db.scalars(select(UnitStage).where(UnitStage.unit_id == u.id))
        for stage in st.all():
            ts = await db.scalars(select(UnitTask).where(UnitTask.stage_id == stage.id))
            tasks = ts.all()
            total_tasks += len(tasks)

            upcoming_tasks += len([t for t in tasks if not t.completed][:7])

    return {
        "total_units": total_units,
        "active_units": active_units,
        "upcoming_tasks": upcoming_tasks,
        "overdue_tasks": 0,     # will be implemented later
        "total_expenses": 0.0,  # future feature
        "profit_index": 0.0,    # placeholder
    }


# ============================================================
# UPDATE A TASK
# ============================================================

async def update_task(task_id: str, payload: TaskUpdate, db: AsyncSession):
    task = await db.get(UnitTask, task_id)
    if not task:
        return None

    if payload.completed is not None:
        task.completed = payload.completed
        if payload.completed:
            task.completed_at = datetime.datetime.utcnow()

    if payload.priority is not None:
        task.priority = payload.priority

    if payload.due_date is not None:
        task.due_date = payload.due_date

    await db.commit()
    await db.refresh(task)
    return task
