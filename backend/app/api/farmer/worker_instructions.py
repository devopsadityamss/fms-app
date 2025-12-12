"""
API Routes — Worker Instructions Broadcast (Farmer POV)
-------------------------------------------------------

Endpoints:
 - POST /farmer/worker/instructions      -> create broadcast
 - GET  /farmer/worker/instructions      -> list instructions
 - GET  /farmer/worker/instructions/{id} -> get one
 - DELETE /farmer/worker/instructions/{id}
 - POST /farmer/worker/instructions/{id}/deliver -> manually mark delivered (stub)
"""

from fastapi import APIRouter, HTTPException, Query, Body
from typing import Optional, List, Dict, Any

from app.services.farmer import worker_instructions_service as svc

router = APIRouter()


@router.post("/farmer/worker/instructions")
async def api_create_instruction(
    title: str = Query(...),
    message: str = Query(...),
    target_all: bool = Query(False),
    worker_ids: Optional[str] = Query(None),  # comma-separated
    unit_id: Optional[str] = Query(None),
    expires_at: Optional[str] = Query(None),
    notes: Optional[str] = Query(None)
):
    worker_list = worker_ids.split(",") if worker_ids else None

    record = svc.create_instruction(
        title=title,
        message=message,
        target_all=target_all,
        worker_ids=worker_list,
        unit_id=unit_id,
        expires_at=expires_at,
        notes=notes,
    )
    return record


@router.get("/farmer/worker/instructions/{instr_id}")
def api_get_instruction(instr_id: str):
    rec = svc.get_instruction(instr_id)
    if not rec:
        raise HTTPException(status_code=404, detail="instruction_not_found")
    return rec


@router.get("/farmer/worker/instructions")
def api_list_instructions(
    mode: Optional[str] = Query(None),
    worker_id: Optional[str] = Query(None),
    unit_id: Optional[str] = Query(None)
):
    return svc.list_instructions(mode=mode, worker_id=worker_id, unit_id=unit_id)


@router.delete("/farmer/worker/instructions/{instr_id}")
def api_delete_instruction(instr_id: str):
    ok = svc.delete_instruction(instr_id)
    if not ok:
        raise HTTPException(status_code=404, detail="instruction_not_found")
    return {"success": True}


@router.post("/farmer/worker/instructions/{instr_id}/deliver")
def api_mark_delivered(instr_id: str):
    rec = svc.mark_delivered(instr_id)
    if not rec:
        raise HTTPException(status_code=404, detail="instruction_not_found")
    return rec
