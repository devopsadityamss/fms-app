"""
API Routes — Budget Planner (Farmer POV)
----------------------------------------

Endpoints:
 - POST /farmer/budget/item
 - GET  /farmer/budget/item/{item_id}
 - GET  /farmer/budget/items
 - PUT  /farmer/budget/item/{item_id}
 - DELETE /farmer/budget/item/{item_id}
 - GET /farmer/budget/summary
"""

from fastapi import APIRouter, HTTPException, Query, Body
from typing import Optional, Dict, Any

from app.services.farmer import budget_planner_service as svc

router = APIRouter()


@router.post("/farmer/budget/item")
async def api_create_budget_item(payload: Dict[str, Any] = Body(...)):
    return svc.create_budget_item(payload)


@router.get("/farmer/budget/item/{item_id}")
def api_get_budget_item(item_id: str):
    rec = svc.get_budget_item(item_id)
    if not rec:
        raise HTTPException(status_code=404, detail="budget_item_not_found")
    return rec


@router.get("/farmer/budget/items")
def api_list_budget_items(
    item_type: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    unit_id: Optional[str] = Query(None)
):
    return svc.list_budget_items(item_type=item_type, category=category, unit_id=unit_id)


@router.put("/farmer/budget/item/{item_id}")
async def api_update_budget_item(item_id: str, payload: Dict[str, Any] = Body(...)):
    updated = svc.update_budget_item(item_id, payload)
    if not updated:
        raise HTTPException(status_code=404, detail="budget_item_not_found")
    return updated


@router.delete("/farmer/budget/item/{item_id}")
def api_delete_budget_item(item_id: str):
    ok = svc.delete_budget_item(item_id)
    if not ok:
        raise HTTPException(status_code=404, detail="budget_item_not_found")
    return {"success": True}


@router.get("/farmer/budget/summary")
def api_budget_summary(unit_id: Optional[str] = Query(None)):
    return svc.budget_summary(unit_id=unit_id)
