# backend/app/crud/farmer/stages.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List

from backend.app.models.farmer.production import UnitStage
from backend.app.schemas.farmer.production import StageCreate, StageUpdate


async def create_stage(db: AsyncSession, stage_in: StageCreate) -> UnitStage:
    stage = UnitStage(
        unit_id=stage_in.unit_id,
        title=stage_in.title,
        order=stage_in.order,
    )
    db.add(stage)
    await db.flush()
    await db.commit()
    await db.refresh(stage)
    return stage


async def get_stage(db: AsyncSession, stage_id: str) -> Optional[UnitStage]:
    stage = await db.get(UnitStage, stage_id)
    return stage


async def list_stages_by_unit(db: AsyncSession, unit_id: str) -> List[UnitStage]:
    rows = await db.scalars(select(UnitStage).where(UnitStage.unit_id == unit_id).order_by(UnitStage.order.asc()))
    return rows.all()


async def update_stage(db: AsyncSession, stage: UnitStage, stage_in: StageUpdate) -> UnitStage:
    for field, val in stage_in.dict(exclude_unset=True).items():
        setattr(stage, field, val)
    db.add(stage)
    await db.commit()
    await db.refresh(stage)
    return stage


async def delete_stage(db: AsyncSession, stage: UnitStage) -> None:
    await db.delete(stage)
    await db.commit()
