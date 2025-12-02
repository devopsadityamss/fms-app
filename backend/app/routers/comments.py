from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from ..core.database import get_db
from ..models import Comment as CommentModel
from ..schemas.comment import Comment, CommentCreate
from sqlalchemy import select
from ..core.auth import require_user

router = APIRouter(prefix="/comments", tags=["comments"])

@router.get("/task/{task_id}", response_model=List[Comment])
async def get_comments(task_id: str, db: AsyncSession = Depends(get_db)):
    q = select(CommentModel).where(CommentModel.task_id == task_id).order_by(CommentModel.created_at.desc())
    res = await db.execute(q)
    return res.scalars().all()

@router.post(
    "/", 
    response_model=Comment,
    dependencies=[Depends(require_user)]
)
async def create_comment(comment_in: CommentCreate, db: AsyncSession = Depends(get_db)):
    obj = CommentModel(
        task_id=comment_in.task_id,
        author_id=comment_in.author_id,
        text=comment_in.text
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj
