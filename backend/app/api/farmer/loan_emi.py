"""
API Routes — Loan EMI Calculator (Farmer POV)

Endpoints:
 - POST /farmer/finance/emi
 - GET  /farmer/finance/emi/{calc_id}
 - GET  /farmer/finance/emi
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from app.services.farmer import loan_emi_service as svc

router = APIRouter()


@router.post("/farmer/finance/emi")
async def api_calculate_emi(
    principal: float = Query(...),
    annual_rate: float = Query(...),
    tenure_months: int = Query(...),
    notes: Optional[str] = Query(None),
    unit_id: Optional[str] = Query(None)
):
    """
    Returns EMI, interest, and total payable.
    """
    result = svc.calculate_emi(
        principal=principal,
        annual_rate=annual_rate,
        tenure_months=tenure_months,
        notes=notes,
        unit_id=unit_id
    )
    return result


@router.get("/farmer/finance/emi/{calc_id}")
def api_get_emi(calc_id: str):
    rec = svc.get_calculation(calc_id)
    if not rec:
        raise HTTPException(status_code=404, detail="calculation_not_found")
    return rec


@router.get("/farmer/finance/emi")
def api_list_emi(unit_id: Optional[str] = Query(None)):
    return svc.list_calculations(unit_id=unit_id)
