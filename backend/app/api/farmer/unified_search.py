# backend/app/api/farmer/unified_search.py

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List

from app.services.farmer.unified_search_service import unified_search

router = APIRouter()


@router.get("/search")
def api_search(
    q: str,
    types: Optional[str] = Query(None, description="Comma-separated types to restrict, e.g. unit,alert,task_template"),
    unit_id: Optional[str] = None,
    page: Optional[int] = 1,
    per_page: Optional[int] = 20
):
    if not q or q.strip() == "":
        raise HTTPException(status_code=400, detail="query parameter 'q' is required")
    types_list = [t.strip() for t in types.split(",")] if types else None
    res = unified_search(query=q, types=types_list, unit_id=unit_id, page=page or 1, per_page=per_page or 20)
    return res
