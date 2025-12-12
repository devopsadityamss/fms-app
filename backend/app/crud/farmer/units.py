# backend/app/crud/farmer/units.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List, Tuple
from uuid import UUID
import datetime

from backend.app.models.farmer.production import ProductionUnit, UnitStage, UnitTask, UnitOption
from backend.app.schemas.farmer.production import ProductionUnitCreate

# NOTE: functions preserve original semantics from production.py


async def compute_unit_progress(unit_id: str, db: AsyncSession) -> Tuple[int, Optional[str], str]:
    """
    Computes:
    - overall progress %
    - next task name
    - health status
    (Preserves previous logic)
    """
    stages = await db.scalars(select(UnitStage).where(UnitStage.unit_id == unit_id))
    stages = stages.all()

    tasks = []
    for s in stages:
        t = await db.scalars(select(UnitTask).where(UnitTask.stage_id == s.id))
        tasks.extend(t.all())

    if not tasks:
        return 0, None, "warning"

    completed = sum(1 for t in tasks if getattr(t, "completed", False))
    total = len(tasks)

    progress = int((completed / total) * 100) if total > 0 else 0

    pending = sorted(
        [t for t in tasks if not getattr(t, "completed", False)],
        key=lambda x: (x.stage_id, getattr(x, "order", 0)),
    )

    next_task = pending[0].title if pending else None

    if progress < 30:
        health = "warning"
    elif progress < 70:
        health = "good"
    else:
        health = "excellent"

    return progress, next_task, health


async def create_production_unit(user_id: str, payload: ProductionUnitCreate, db: AsyncSession):
    """
    Create a ProductionUnit with options, stages and tasks (same behavior as old function).
    """
    unit = ProductionUnit(
        user_id=user_id,
        name=payload.name,
        practice_type=payload.practice_type,
        category=payload.category,
        meta=payload.meta,
        created_at=datetime.datetime.utcnow(),
    )

    db.add(unit)
    await db.flush()  # ensure unit.id populated

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
                completed=getattr(t, "completed", False),
                priority=getattr(t, "priority", None),
                due_date=getattr(t, "due_date", None),
                assigned_to=getattr(t, "assigned_to", None),
            )
            db.add(task)

    await db.commit()
    return unit


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
            upcoming_tasks += len([t for t in tasks if not getattr(t, "completed", False)][:7])

    return {
        "total_units": total_units,
        "active_units": active_units,
        "upcoming_tasks": upcoming_tasks,
        "overdue_tasks": 0.0,     # reserved
        "total_expenses": 0.0,    # reserved
        "profit_index": 0.0,      # reserved
    }
