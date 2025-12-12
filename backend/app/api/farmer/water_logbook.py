"""
API Routes — Water Logbook (Farmer POV)
---------------------------------------

Endpoints:
 - POST /farmer/water/log
 - GET  /farmer/water/log/{log_id}
 - GET  /farmer/water/log
 - PUT  /farmer/water/log/{log_id}
 - DELETE /farmer/water/log/{log_id}
 - GET  /farmer/water/summary
"""

from fastapi import APIRouter, HTTPException, Query, Body
from typing import Optional, Dict, Any

from app.services.farmer import water_logbook_service as svc

router = APIRouter()


@router.post("/farmer/water/log")
async def api_create_water_log(payload: Dict[str, Any] = Body(...)):
    return svc.create_water_log(payload)


@router.get("/farmer/water/log/{log_id}")
def api_get_water_log(log_id: str):
    rec = svc.get_water_log(log_id)
    if not rec:
        raise HTTPException(status_code=404, detail="water_log_not_found")
    return rec


@router.get("/farmer/water/log")
def api_list_water_logs(
    unit_id: Optional[str] = Query(None),
    method: Optional[str] = Query(None),
    water_source: Optional[str] = Query(None)
):
    return svc.list_water_logs(unit_id=unit_id, method=method, water_source=water_source)


@router.put("/farmer/water/log/{log_id}")
async def api_update_water_log(log_id: str, payload: Dict[str, Any] = Body(...)):
    rec = svc.update_water_log(log_id, payload)
    if not rec:
        raise HTTPException(status_code=404, detail="water_log_not_found")
    return rec


@router.delete("/farmer/water/log/{log_id}")
def api_delete_water_log(log_id: str):
    ok = svc.delete_water_log(log_id)
    if not ok:
        raise HTTPException(status_code=404, detail="water_log_not_found")
    return {"success": True}


@router.get("/farmer/water/summary")
def api_water_summary(unit_id: Optional[str] = Query(None)):
    return svc.total_water_usage(unit_id=unit_id)
