from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from ..core.database import get_db
from ..models import Attachment as AttachmentModel
from ..schemas.attachment import Attachment, AttachmentCreate
from sqlalchemy import select
from ..core.auth import require_user

router = APIRouter(prefix="/attachments", tags=["attachments"])

@router.get("/task/{task_id}", response_model=List[Attachment])
async def list_attachments(task_id: str, db: AsyncSession = Depends(get_db)):
    q = select(AttachmentModel).where(AttachmentModel.task_id == task_id).order_by(AttachmentModel.created_at.desc())
    res = await db.execute(q)
    return res.scalars().all()

@router.post(
    "/", 
    response_model=Attachment,
    dependencies=[Depends(require_user)]
)
async def create_attachment(att_in: AttachmentCreate, db: AsyncSession = Depends(get_db)):
    obj = AttachmentModel(
        task_id=att_in.task_id,
        path=att_in.path,
        name=att_in.name
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj
