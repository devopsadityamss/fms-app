# backend/app/api/farmer/insurance.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from app.services.farmer.insurance_service import (
    calculate_premium,
    create_policy,
    get_policy,
    list_policies,
    cancel_policy,
    renew_policy,
    policies_expiring_within,
    submit_claim,
    get_claim,
    list_claims,
    assess_claim,
    finalize_claim,
    list_payouts,
    policy_claims_summary,
    open_claims_for_farmer
)

router = APIRouter()

# Payloads
class PremiumPayload(BaseModel):
    area_acres: float
    crop: str
    sum_insured: float
    base_rate_per_acre: Optional[float] = 100.0

class PolicyPayload(BaseModel):
    farmer_id: str
    unit_id: Optional[str] = None
    provider: str
    crop: str
    area_acres: float
    sum_insured: float
    start_date_iso: Optional[str] = None
    tenure_days: Optional[int] = 365
    deductible_pct: Optional[float] = 5.0
    metadata: Optional[Dict[str, Any]] = None

class ClaimPayload(BaseModel):
    policy_id: str
    reporter_id: str
    event_date_iso: Optional[str] = None
    event_type: str
    estimated_loss_amount: float
    evidence: Optional[List[Dict[str, Any]]] = None
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class AssessPayload(BaseModel):
    claim_id: str
    assessor_id: str
    assessed_loss_amount: Optional[float] = None
    assessor_notes: Optional[str] = None

class FinalizePayload(BaseModel):
    claim_id: str
    action: str   # approve | deny | mark_paid
    actor_id: str
    notes: Optional[str] = None

# Endpoints
@router.post("/farmer/insurance/calc_premium")
def api_calc_premium(req: PremiumPayload):
    return calculate_premium(req.area_acres, req.crop, req.sum_insured, base_rate_per_acre=req.base_rate_per_acre)

@router.post("/farmer/insurance/policy")
def api_create_policy(req: PolicyPayload):
    return create_policy(
        farmer_id=req.farmer_id,
        unit_id=req.unit_id,
        provider=req.provider,
        crop=req.crop,
        area_acres=req.area_acres,
        sum_insured=req.sum_insured,
        start_date_iso=req.start_date_iso,
        tenure_days=req.tenure_days or 365,
        deductible_pct=req.deductible_pct or 5.0,
        metadata=req.metadata
    )

@router.get("/farmer/insurance/policy/{policy_id}")
def api_get_policy(policy_id: str):
    res = get_policy(policy_id)
    if not res:
        raise HTTPException(status_code=404, detail="policy_not_found")
    return res

@router.get("/farmer/insurance/policies")
def api_list_policies(farmer_id: Optional[str] = None, active_only: Optional[bool] = True):
    return {"policies": list_policies(farmer_id=farmer_id, active_only=bool(active_only))}

@router.post("/farmer/insurance/policy/{policy_id}/cancel")
def api_cancel_policy(policy_id: str, reason: Optional[str] = None):
    res = cancel_policy(policy_id, reason=reason)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res

@router.post("/farmer/insurance/policy/{policy_id}/renew")
def api_renew_policy(policy_id: str, tenure_days: Optional[int] = 365):
    res = renew_policy(policy_id, tenure_days=tenure_days or 365)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res

@router.get("/farmer/insurance/policies/expiring")
def api_policies_expiring(days: Optional[int] = 30):
    return {"expiring": policies_expiring_within(days=days or 30)}

@router.post("/farmer/insurance/claim")
def api_submit_claim(req: ClaimPayload):
    res = submit_claim(
        policy_id=req.policy_id,
        reporter_id=req.reporter_id,
        event_date_iso=req.event_date_iso,
        event_type=req.event_type,
        estimated_loss_amount=req.estimated_loss_amount,
        evidence=req.evidence,
        notes=req.notes,
        metadata=req.metadata
    )
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res

@router.get("/farmer/insurance/claim/{claim_id}")
def api_get_claim(claim_id: str):
    res = get_claim(claim_id)
    if not res:
        raise HTTPException(status_code=404, detail="claim_not_found")
    return res

@router.get("/farmer/insurance/claims")
def api_list_claims(policy_id: Optional[str] = None, status: Optional[str] = None):
    return {"claims": list_claims(policy_id=policy_id, status=status)}

@router.post("/farmer/insurance/assess")
def api_assess_claim(req: AssessPayload):
    res = assess_claim(req.claim_id, req.assessor_id, assessed_loss_amount=req.assessed_loss_amount, assessor_notes=req.assessor_notes)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res

@router.post("/farmer/insurance/finalize")
def api_finalize_claim(req: FinalizePayload):
    res = finalize_claim(req.claim_id, req.action, req.actor_id, notes=req.notes)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res

@router.get("/farmer/insurance/payouts")
def api_list_payouts(limit: Optional[int] = 100):
    return {"payouts": list_payouts(limit=limit or 100)}

@router.get("/farmer/insurance/summary/{policy_id}")
def api_policy_summary(policy_id: str):
    res = policy_claims_summary(policy_id)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res

@router.get("/farmer/insurance/open_claims/{farmer_id}")
def api_open_claims(farmer_id: str):
    return {"open_claims": open_claims_for_farmer(farmer_id)}
