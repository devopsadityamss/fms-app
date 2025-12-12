# backend/app/services/farmer/insurance_service.py

"""
Farm Insurance & Claims Management (in-memory)

- Policies: create, get, list, renew, cancel
- Claims: submit, assess, update status (assessor_review, approved, denied, paid)
- Premium calc: simple heuristic using area, crop, sum_insured, and risk factor
- Payout ledger: records of payouts
- Expiry reminders helper
- All data stored in-memory for prototyping
"""

from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, Any, List, Optional
import uuid
import math

_lock = Lock()

# stores
_policies: Dict[str, Dict[str, Any]] = {}       # policy_id -> record
_policies_by_farmer: Dict[str, List[str]] = {}  # farmer_id -> [policy_ids]

_claims: Dict[str, Dict[str, Any]] = {}         # claim_id -> record
_claims_by_policy: Dict[str, List[str]] = {}    # policy_id -> [claim_ids]

_payouts: List[Dict[str, Any]] = []             # list of payout records

# simple crop risk factors
CROP_RISK_FACTORS = {
    "paddy": 1.2,
    "wheat": 1.0,
    "maize": 1.05,
    "cotton": 1.15,
    "generic": 1.0
}

def _now_iso():
    return datetime.utcnow().isoformat()

def _new_id(prefix: str):
    return f"{prefix}_{uuid.uuid4()}"

# -----------------------
# Premium calculation
# -----------------------
def calculate_premium(
    area_acres: float,
    crop: str,
    sum_insured: float,
    base_rate_per_acre: float = 100.0
) -> Dict[str, Any]:
    """
    Simple premium:
      premium = base_rate_per_acre * area * crop_risk * load_factor
    Ensures premium doesn't exceed a % of sum_insured (sanity).
    """
    crop_factor = CROP_RISK_FACTORS.get(crop.lower(), CROP_RISK_FACTORS["generic"])
    load = 1.0
    premium = base_rate_per_acre * float(area_acres) * float(crop_factor) * load
    # ensure premium not > 10% of sum_insured
    max_allowed = 0.10 * float(sum_insured)
    premium = min(premium, max_allowed)
    premium = round(premium, 2)
    return {"area_acres": area_acres, "crop": crop, "sum_insured": sum_insured, "premium": premium, "base_rate_per_acre": base_rate_per_acre}

# -----------------------
# Policy operations
# -----------------------
def create_policy(
    farmer_id: str,
    unit_id: Optional[str],
    provider: str,
    crop: str,
    area_acres: float,
    sum_insured: float,
    start_date_iso: Optional[str] = None,
    tenure_days: int = 365,
    deductible_pct: float = 5.0,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    pid = _new_id("policy")
    start = datetime.fromisoformat(start_date_iso) if start_date_iso else datetime.utcnow()
    expires = (start + timedelta(days=tenure_days)).isoformat()
    premium_rec = calculate_premium(area_acres, crop, sum_insured)
    rec = {
        "policy_id": pid,
        "farmer_id": farmer_id,
        "unit_id": unit_id,
        "provider": provider,
        "crop": crop.lower(),
        "area_acres": float(area_acres),
        "sum_insured": float(sum_insured),
        "premium": premium_rec["premium"],
        "start_date": (start).isoformat(),
        "expires_at": expires,
        "deductible_pct": float(deductible_pct),
        "status": "active",  # active | expired | cancelled
        "metadata": metadata or {},
        "created_at": _now_iso()
    }
    with _lock:
        _policies[pid] = rec
        _policies_by_farmer.setdefault(farmer_id, []).append(pid)
    return rec

def get_policy(policy_id: str) -> Dict[str, Any]:
    return _policies.get(policy_id, {})

def list_policies(farmer_id: Optional[str] = None, active_only: bool = True) -> List[Dict[str, Any]]:
    with _lock:
        if farmer_id:
            ids = _policies_by_farmer.get(farmer_id, [])[:]
            items = [ _policies.get(i) for i in ids if _policies.get(i) ]
        else:
            items = list(_policies.values())
    if active_only:
        items = [p for p in items if p.get("status") == "active"]
    return items

def cancel_policy(policy_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
    with _lock:
        p = _policies.get(policy_id)
        if not p:
            return {"error": "policy_not_found"}
        p["status"] = "cancelled"
        p["cancelled_at"] = _now_iso()
        if reason:
            p.setdefault("metadata", {})["cancellation_reason"] = reason
        _policies[policy_id] = p
    return p

def renew_policy(policy_id: str, tenure_days: int = 365) -> Dict[str, Any]:
    with _lock:
        p = _policies.get(policy_id)
        if not p:
            return {"error": "policy_not_found"}
        cur_exp = datetime.fromisoformat(p.get("expires_at"))
        new_exp = (cur_exp + timedelta(days=tenure_days)).isoformat()
        p["expires_at"] = new_exp
        p["updated_at"] = _now_iso()
        _policies[policy_id] = p
    return p

def policies_expiring_within(days: int = 30) -> List[Dict[str, Any]]:
    cutoff = datetime.utcnow() + timedelta(days=days)
    res = []
    with _lock:
        for p in list(_policies.values()):
            try:
                exp = datetime.fromisoformat(p.get("expires_at"))
                if datetime.utcnow() <= exp <= cutoff and p.get("status") == "active":
                    res.append(p)
            except Exception:
                pass
    return res

# -----------------------
# Claims lifecycle
# -----------------------
def submit_claim(
    policy_id: str,
    reporter_id: str,
    event_date_iso: Optional[str],
    event_type: str,   # drought, flood, pest, fire, theft, other
    estimated_loss_amount: float,
    evidence: Optional[List[Dict[str, Any]]] = None,
    notes: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    if policy_id not in _policies:
        return {"error": "policy_not_found"}
    cid = _new_id("claim")
    rec = {
        "claim_id": cid,
        "policy_id": policy_id,
        "reporter_id": reporter_id,
        "event_date": event_date_iso or _now_iso(),
        "event_type": event_type,
        "estimated_loss_amount": float(estimated_loss_amount),
        "evidence": evidence or [],
        "notes": notes or "",
        "status": "filed",  # filed -> assessor_review -> approved | denied -> paid
        "assessed_amount": None,
        "payout_amount": None,
        "created_at": _now_iso()
    }
    with _lock:
        _claims[cid] = rec
        _claims_by_policy.setdefault(policy_id, []).append(cid)
    return rec

def get_claim(claim_id: str) -> Dict[str, Any]:
    return _claims.get(claim_id, {})

def list_claims(policy_id: Optional[str] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
    with _lock:
        items = list(_claims.values())
    if policy_id:
        ids = _claims_by_policy.get(policy_id, [])[:]
        items = [ _claims[i] for i in ids if _claims.get(i) ]
    if status:
        items = [c for c in items if c.get("status") == status]
    return items

def assess_claim(claim_id: str, assessor_id: str, assessed_loss_amount: Optional[float] = None, assessor_notes: Optional[str] = None) -> Dict[str, Any]:
    """
    Basic assessment heuristic:
      - If assessed_loss_amount provided, use it.
      - Else, use 0.6 * estimated_loss_amount for partial assessment by default.
      - Apply deductible % from policy: payout = assessed * (1 - deductible_pct/100), capped at sum_insured.
    """
    with _lock:
        c = _claims.get(claim_id)
        if not c:
            return {"error": "claim_not_found"}
        policy = _policies.get(c.get("policy_id"))
        if not policy:
            return {"error": "policy_missing"}
        est = float(c.get("estimated_loss_amount", 0.0))
        assessed = float(assessed_loss_amount) if assessed_loss_amount is not None else round(est * 0.6, 2)
        deductible = float(policy.get("deductible_pct", 0.0))
        payout_before_cap = max(0.0, assessed * (1.0 - deductible / 100.0))
        payout = min(payout_before_cap, float(policy.get("sum_insured", 0.0)))
        c["status"] = "assessor_review"
        c["assessed_by"] = assessor_id
        c["assessed_amount"] = round(assessed, 2)
        c["payout_amount"] = round(payout, 2)
        c["assessor_notes"] = assessor_notes or ""
        c["assessed_at"] = _now_iso()
        _claims[claim_id] = c
    return c

def finalize_claim(claim_id: str, action: str, actor_id: str, notes: Optional[str] = None) -> Dict[str, Any]:
    """
    action: 'approve' or 'deny' or 'mark_paid'
    """
    with _lock:
        c = _claims.get(claim_id)
        if not c:
            return {"error": "claim_not_found"}
        if action == "approve":
            c["status"] = "approved"
            c["approved_by"] = actor_id
            c["approved_at"] = _now_iso()
        elif action == "deny":
            c["status"] = "denied"
            c["denied_by"] = actor_id
            c["denied_at"] = _now_iso()
            c["denial_notes"] = notes or ""
        elif action == "mark_paid":
            # only allow if approved and payout_amount present
            if c.get("status") != "approved":
                return {"error": "claim_not_approved"}
            payout = float(c.get("payout_amount", 0.0)) if c.get("payout_amount") else 0.0
            c["status"] = "paid"
            c["paid_by"] = actor_id
            c["paid_at"] = _now_iso()
            # record payout ledger
            payout_rec = {
                "payout_id": _new_id("payout"),
                "claim_id": claim_id,
                "policy_id": c.get("policy_id"),
                "amount": round(payout, 2),
                "paid_at": _now_iso(),
                "processed_by": actor_id
            }
            _payouts.append(payout_rec)
            c.setdefault("payout_record", payout_rec)
        else:
            return {"error": "invalid_action"}
        _claims[claim_id] = c
    return c

def list_payouts(limit: int = 100) -> List[Dict[str, Any]]:
    return _payouts[-limit:]

# -----------------------
# Simple helpers / reports
# -----------------------
def policy_claims_summary(policy_id: str) -> Dict[str, Any]:
    claims = list_claims(policy_id=policy_id)
    total_claims = len(claims)
    total_estimated = sum(c.get("estimated_loss_amount", 0) for c in claims)
    total_assessed = sum((c.get("assessed_amount") or 0) for c in claims)
    total_payouts = sum((c.get("payout_amount") or 0) for c in claims)
    return {
        "policy_id": policy_id,
        "total_claims": total_claims,
        "total_estimated_loss": round(total_estimated, 2),
        "total_assessed": round(total_assessed, 2),
        "total_payouts": round(total_payouts, 2),
        "claims": claims
    }

def open_claims_for_farmer(farmer_id: str) -> List[Dict[str, Any]]:
    pids = _policies_by_farmer.get(farmer_id, [])
    open_claims = []
    for pid in pids:
        for cid in _claims_by_policy.get(pid, []):
            c = _claims.get(cid)
            if c and c.get("status") not in ("paid", "denied"):
                open_claims.append(c)
    return open_claims
