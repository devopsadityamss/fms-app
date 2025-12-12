"""
API Routes — Labor Compliance Checker
-------------------------------------

Endpoints:
 - POST /farmer/labor/compliance/worker
 - POST /farmer/labor/compliance/farm
"""

from fastapi import APIRouter, HTTPException, Body
from typing import Dict, Any, Optional, List

from app.services.farmer import labor_compliance_service as svc

router = APIRouter()


# -------------------------------------------------------------
# INDIVIDUAL WORKER COMPLIANCE
# -------------------------------------------------------------
@router.post("/farmer/labor/compliance/worker")
async def api_worker_compliance(payload: Dict[str, Any] = Body(...)):
    required = ["worker_id", "month", "year"]
    for r in required:
        if r not in payload:
            raise HTTPException(status_code=400, detail=f"{r} is required")

    return svc.evaluate_worker_compliance(
        worker_id=payload["worker_id"],
        month=int(payload["month"]),
        year=int(payload["year"]),
        worker_meta=payload.get("worker_meta")
    )


# -------------------------------------------------------------
# FARM-WIDE COMPLIANCE
# -------------------------------------------------------------
@router.post("/farmer/labor/compliance/farm")
async def api_farm_compliance(payload: Dict[str, Any] = Body(...)):
    required = ["worker_ids", "month", "year"]
    for r in required:
        if r not in payload:
            raise HTTPException(status_code=400, detail=f"{r} is required")

    return svc.farm_compliance_summary(
        worker_ids=payload["worker_ids"],
        month=int(payload["month"]),
        year=int(payload["year"])
    )
