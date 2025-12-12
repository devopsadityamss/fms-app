"""
FastAPI routes for Operation Listing (Farmer POV)

Routes:
 - POST /farmer/operations            -> create operation
 - GET  /farmer/operations           -> list operations (with filters)
 - GET  /farmer/operations/{op_id}   -> get operation
 - PUT  /farmer/operations/{op_id}   -> update operation
 - DELETE /farmer/operations/{op_id} -> delete operation
 - POST /farmer/operations/{op_id}/complete -> mark completed (domain action)
"""

from fastapi import APIRouter, HTTPException, Query, Body
from typing import Optional, List, Dict, Any

from app.services.farmer import operation_listing_service as svc

router = APIRouter()

# --- request / response simple pydantic-optional shapes ---
# (we keep function signatures simple and accept raw dicts; adapt to Pydantic models later)

@router.post("/farmer/operations")
async def api_create_operation(payload: Dict[str, Any] = Body(...)):
    rec = svc.create_operation(payload)
    return rec

@router.get("/farmer/operations")
def api_list_operations(
    unit_id: Optional[str] = Query(None),
    operation_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sort_desc: bool = Query(True)
):
    return svc.list_operations(unit_id=unit_id, operation_type=operation_type, status=status, limit=limit, offset=offset, sort_desc=sort_desc)

@router.get("/farmer/operations/{op_id}")
def api_get_operation(op_id: str):
    rec = svc.get_operation(op_id)
    if not rec:
        raise HTTPException(status_code=404, detail="operation_not_found")
    return rec

@router.put("/farmer/operations/{op_id}")
def api_update_operation(op_id: str, payload: Dict[str, Any] = Body(...)):
    rec = svc.update_operation(op_id, payload)
    if not rec:
        raise HTTPException(status_code=404, detail="operation_not_found")
    return rec

@router.delete("/farmer/operations/{op_id}")
def api_delete_operation(op_id: str):
    ok = svc.delete_operation(op_id)
    if not ok:
        raise HTTPException(status_code=404, detail="operation_not_found")
    return {"success": True}

@router.post("/farmer/operations/{op_id}/complete")
def api_complete_operation(op_id: str, completion_notes: Optional[str] = Body(None)):
    rec = svc.mark_operation_completed(op_id, completion_notes=completion_notes)
    if not rec:
        raise HTTPException(status_code=404, detail="operation_not_found")
    return rec

# convenience endpoint: summary for a unit
@router.get("/farmer/operations/summary/{unit_id}")
def api_operations_summary(unit_id: str):
    return svc.operations_summary_by_unit(unit_id)
