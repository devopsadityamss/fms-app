from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from typing import Optional

from app.core.database import get_db
from app.models.production import ProductionUnit, UnitOption, UnitStage, UnitTask
from app.schemas.production import ProductionUnitCreate, TaskUpdate
from app.crud import production as crud_production

router = APIRouter(prefix="/farmer/production-unit", tags=["Production"])


# ---------------------------------------------------------------------
# CREATE PRODUCTION UNIT
# - kept compatible with your original behavior (accepts a dict)
# - delegates to CRUD layer (create_production_unit)
# ---------------------------------------------------------------------
@router.post("/create")
async def create_production_unit(data: dict, db: AsyncSession = Depends(get_db)):
    """
    Accepts a JSON dict payload (backwards compatible). Expected keys:
      - user_id (required)
      - name, practice_type, category, meta
      - stages: [{ title, order, tasks: [{title, order, ...}] }, ...]
      - options: [{ option_name, meta }, ...]
    """

    user_id = data.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")

    try:
        UUID(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user_id format")

    # Normalize dict → ProductionUnitCreate schema (safe)
    payload = ProductionUnitCreate(
        name=data.get("name", "Untitled Unit"),
        practice_type=data.get("practice_type", ""),
        category=data.get("category"),
        meta=data.get("metadata") or data.get("meta"),
        stages=[
            {
                "title": s.get("title"),
                "order": s.get("order", 0),
                "tasks": [
                    {
                        "title": t.get("title"),
                        "order": t.get("order", 0),
                        "completed": t.get("completed", False),
                        "priority": t.get("priority"),
                        "due_date": t.get("due_date"),
                        "assigned_to": t.get("assigned_to"),
                    }
                    for t in (s.get("tasks") or [])
                ],
            }
            for s in (data.get("stages") or [])
        ],
        options=[
            {"option_name": o} if isinstance(o, str) else {"option_name": o.get("option_name"), "meta": o.get("meta")}
            for o in (data.get("items") or data.get("options") or [])
        ],
    )

    # ProductionUnitCreate type expects objects; convert dicts into proper Pydantic by re-parsing
    # Use Pydantic's model parsing (this will validate shapes)
    try:
        pu_payload = ProductionUnitCreate.parse_obj(payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid payload: {e}")

    unit = await crud_production.create_production_unit(user_id, pu_payload, db)
    return {"status": "ok", "id": unit.id}


# ---------------------------------------------------------------------
# GET FULL PRODUCTION UNIT (unchanged semantics)
# ---------------------------------------------------------------------
@router.get("/{unit_id}")
async def get_production_unit(unit_id: str, db: AsyncSession = Depends(get_db)):
    try:
        UUID(unit_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid unit id")

    unit = await crud_production.get_production_unit(unit_id, db)
    if not unit:
        raise HTTPException(status_code=404, detail="Production unit not found")

    # Return raw ORM object — FastAPI + Pydantic (with orm_mode) will serialize
    return unit


# ---------------------------------------------------------------------
# LIST UNITS FOR DASHBOARD
# (keeps the same output shape as your previous implementation)
# ---------------------------------------------------------------------
@router.get("/list/{user_id}")
async def list_production_units(user_id: str, db: AsyncSession = Depends(get_db)):
    """Returns production units formatted for dashboard cards."""
    try:
        UUID(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user_id format")

    units = await crud_production.list_units_for_dashboard(user_id, db)
    return {"units": units}


# ---------------------------------------------------------------------
# DASHBOARD SUMMARY
# ---------------------------------------------------------------------
@router.get("/summary/{user_id}")
async def get_dashboard_summary(user_id: str, db: AsyncSession = Depends(get_db)):
    """Returns KPI metrics for dashboard summary."""
    try:
        UUID(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user_id")

    summary = await crud_production.dashboard_summary(user_id, db)
    return summary


# ---------------------------------------------------------------------
# UPDATE A TASK (small helper endpoint)
# - payload follows app.schemas.production.TaskUpdate
# ---------------------------------------------------------------------
@router.put("/task/{task_id}")
async def update_task_endpoint(task_id: str, payload: TaskUpdate, db: AsyncSession = Depends(get_db)):
    try:
        UUID(task_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid task_id format")

    task = await crud_production.update_task(task_id, payload, db)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # after updating a task you might want to recalc & return unit progress — keep response minimal for now
    return {"status": "updated", "task_id": task.id}


# ---------------------------------------------------------------------
# (Optional) Lightweight health-check / simple list helper for debugging
# ---------------------------------------------------------------------
@router.get("/_debug/all/{user_id}")
async def debug_list_raw(user_id: str, db: AsyncSession = Depends(get_db)):
    """Developer helper: returns raw production units + counts (not for prod)."""
    try:
        UUID(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user_id format")

    rows = await db.scalars(select(ProductionUnit).where(ProductionUnit.user_id == user_id))
    rows = rows.all()
    out = []
    for u in rows:
        stages = await db.scalars(select(UnitStage).where(UnitStage.unit_id == u.id))
        stages = stages.all()
        tasks = []
        for s in stages:
            ts = await db.scalars(select(UnitTask).where(UnitTask.stage_id == s.id))
            tasks.extend(ts.all())
        opts = await db.scalars(select(UnitOption).where(UnitOption.unit_id == u.id))
        out.append({
            "id": u.id,
            "name": u.name,
            "stages": len(stages),
            "tasks": len(tasks),
            "options": [o.option_name for o in opts.all()]
        })
    return {"units": out}
