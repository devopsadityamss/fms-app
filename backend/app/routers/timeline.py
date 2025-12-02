from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from ..core.database import get_db
from ..models.timeline import TimelineItem as TimelineModel
from ..schemas.timeline import TimelineItem, TimelineItemCreate
from sqlalchemy import select
from ..core.auth import require_user

router = APIRouter(prefix="/timeline", tags=["timeline"])

@router.get("/task/{task_id}", response_model=List[TimelineItem])
async def get_timeline(task_id: str, db: AsyncSession = Depends(get_db)):
    q = select(TimelineModel).where(TimelineModel.task_id == task_id).order_by(TimelineModel.created_at.desc())
    res = await db.execute(q)
    return res.scalars().all()

@router.post(
    "/", 
    response_model=TimelineItem,
    dependencies=[Depends(require_user)]
)
async def create_timeline(item_in: TimelineItemCreate, db: AsyncSession = Depends(get_db)):
    obj = TimelineModel(
        task_id=item_in.task_id,
        title=item_in.title,
        description=item_in.description
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj
