# backend/app/api/marketplace/payment.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.services.marketplace.payment_service import (
    ensure_wallet,
    get_wallet_balance,
    credit_wallet,
    debit_wallet,
    create_payment_intent,
    capture_payment_intent,
    hold_in_escrow,
    release_escrow_to_provider,
    refund_escrow_to_payer,
    create_provider_payout,
    get_escrow,
    list_escrows,
    list_ledger,
    list_wallets
)

router = APIRouter()


# -------- Payloads
class WalletTopupPayload(BaseModel):
    user_id: str
    amount: float
    meta: Optional[Dict[str, Any]] = None


class PaymentIntentPayload(BaseModel):
    user_id: str
    amount: float
    currency: Optional[str] = "INR"
    payment_method: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class CapturePayload(BaseModel):
    simulate_success: Optional[bool] = True


class HoldEscrowPayload(BaseModel):
    booking_id: str
    payer_user_id: str
    amount: float
    currency: Optional[str] = "INR"


class ReleasePayload(BaseModel):
    booking_id: str
    provider_user_id: str
    platform_fee_pct: Optional[float] = None


class RefundPayload(BaseModel):
    booking_id: str
    reason: Optional[str] = None


class PayoutPayload(BaseModel):
    provider_user_id: str
    amount: float
    payout_method: Optional[Dict[str, Any]] = None


# -------- Endpoints
@router.post("/market/payments/wallet/ensure")
def api_ensure_wallet(user_id: str):
    return ensure_wallet(user_id)


@router.get("/market/payments/wallet/{user_id}")
def api_get_wallet(user_id: str):
    return get_wallet_balance(user_id)


@router.post("/market/payments/wallet/topup")
def api_topup(req: WalletTopupPayload):
    # In production, topup happens after payment gateway capture; here we simulate credit.
    res = credit_wallet(req.user_id, req.amount, meta=req.meta or {})
    return res


@router.post("/market/payments/intent")
def api_create_intent(req: PaymentIntentPayload):
    intent = create_payment_intent(req.user_id, req.amount, currency=req.currency or "INR", payment_method=req.payment_method, metadata=req.metadata)
    return intent


@router.post("/market/payments/intent/{intent_id}/capture")
def api_capture_intent(intent_id: str, payload: CapturePayload):
    res = capture_payment_intent(intent_id, simulate_success=bool(payload.simulate_success))
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res


@router.post("/market/payments/escrow/hold")
def api_hold_escrow(req: HoldEscrowPayload):
    res = hold_in_escrow(req.booking_id, req.payer_user_id, req.amount, currency=req.currency or "INR")
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res


@router.post("/market/payments/escrow/release")
def api_release_escrow(req: ReleasePayload):
    res = release_escrow_to_provider(req.booking_id, req.provider_user_id, platform_fee_pct=req.platform_fee_pct)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res


@router.post("/market/payments/escrow/refund")
def api_refund_escrow(req: RefundPayload):
    res = refund_escrow_to_payer(req.booking_id, reason=req.reason)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res


@router.post("/market/payments/provider/payout")
def api_provider_payout(req: PayoutPayload):
    res = create_provider_payout(req.provider_user_id, req.amount, payout_method=req.payout_method)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res


@router.get("/market/payments/escrow/{booking_id}")
def api_get_escrow(booking_id: str):
    return get_escrow(booking_id)


@router.get("/market/payments/escrows")
def api_list_escrows(status: Optional[str] = None):
    return {"escrows": list_escrows(status=status)}


@router.get("/market/payments/ledger")
def api_list_ledger(limit: Optional[int] = 200):
    return {"ledger": list_ledger(limit=limit or 200)}


@router.get("/market/payments/wallets")
def api_list_wallets():
    return {"wallets": list_wallets()}
