# backend/app/api/farmer/offline_sync.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.services.farmer.offline_sync_service import (
    register_device,
    get_device,
    list_devices,
    push_operations,
    pull_server_changes,
    list_device_queue,
    resolve_conflict,
    purge_device_queue
)

router = APIRouter()

# Payload schemas
class RegisterPayload(BaseModel):
    device_id: Optional[str] = None
    farmer_id: Optional[str] = None


class OperationPayload(BaseModel):
    op_id: Optional[str] = None
    entity: str
    entity_id: Optional[str] = None
    action: str  # create | update | delete
    payload: Optional[Dict[str, Any]] = None
    client_ts: Optional[str] = None


class PushPayload(BaseModel):
    device_id: str
    ops: List[OperationPayload]


class ResolvePayload(BaseModel):
    action: str  # accept_server | accept_client | merge
    merged_payload: Optional[Dict[str, Any]] = None


@router.post("/sync/register")
def api_register(req: RegisterPayload):
    rec = register_device(req.device_id, farmer_id=req.farmer_id)
    return rec


@router.get("/sync/device/{device_id}")
def api_get_device(device_id: str):
    rec = get_device(device_id)
    if not rec:
        raise HTTPException(status_code=404, detail="device_not_found")
    return rec


@router.get("/sync/devices")
def api_list_devices():
    return list_devices()


@router.post("/sync/push")
def api_push(payload: PushPayload):
    if not payload.device_id:
        raise HTTPException(status_code=400, detail="device_id required")
    ops = [o.dict() for o in payload.ops]
    res = push_operations(payload.device_id, ops)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res


@router.get("/sync/pull/{device_id}")
def api_pull(device_id: str, since_iso: Optional[str] = None, limit: Optional[int] = 100):
    res = pull_server_changes(device_id, since_iso=since_iso, limit=limit or 100)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res


@router.get("/sync/queue/{device_id}")
def api_list_queue(device_id: str):
    res = list_device_queue(device_id)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res


@router.post("/sync/resolve/{device_id}/{op_id}")
def api_resolve(device_id: str, op_id: str, payload: ResolvePayload):
    res = resolve_conflict(device_id, op_id, payload.dict())
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res


@router.post("/sync/purge/{device_id}")
def api_purge(device_id: str):
    res = purge_device_queue(device_id)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res
