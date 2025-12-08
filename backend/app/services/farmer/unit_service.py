# backend/app/services/farmer/unit_service.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.models.farmer.production import ProductionUnit, UnitStage

from backend.app.crud.farmer.units import compute_unit_progress


# ----------------------------------------------------------
# RECOMPUTE UNIT PROGRESS
# ----------------------------------------------------------

async def recompute_unit_progress(unit_id: str, db: AsyncSession):
    unit = await db.get(ProductionUnit, unit_id)
    if not unit:
        return None

    progress, next_task, health = await compute_unit_progress(unit_id, db)

    unit.progress = progress
    unit.health_status = health

    # set end_date if fully complete
    if progress == 100 and not unit.end_date:
        from datetime import datetime
        unit.end_date = datetime.utcnow()

    # auto-update status
    if progress == 100:
        unit.status = "completed"
    elif progress > 0:
        unit.status = "active"
    else:
        unit.status = "pending"

    db.add(unit)
    await db.commit()
    return unit
