# backend/app/services/marketplace/payment_service.py

from datetime import datetime
from threading import Lock
from typing import Dict, Any, List, Optional
import uuid

"""
Marketplace Payments & Escrow (in-memory)

Concepts:
 - wallets: per-user cached balance (simulate top-up via payment gateway)
 - payment_intents: created when farmer initiates payment (stub for gateway)
 - escrow_accounts: holds funds for a booking until provider marks complete
 - ledger: immutable list of transactions for audit (in-memory)
 - payouts: transfer from provider escrow to provider wallet (simulate)
 - fees: platform fee percentage applied on releases (configurable)
 
NOTE:
- This is a simulator / stub. Replace payment_intent functions with real gateway SDK calls.
- Persist data to DB later for durability.
"""

_lock = Lock()

# user_id -> { "user_id", "balance" }
_wallets: Dict[str, Dict[str, Any]] = {}

# booking_id -> escrow record { booking_id, amount, currency, status: held|released|refunded, created_at, held_at, released_at }
_escrow_store: Dict[str, Dict[str, Any]] = {}

# payment intent store: intent_id -> {intent_id, user_id, amount, currency, status: created|captured|failed, metadata}
_payment_intents: Dict[str, Dict[str, Any]] = {}

# ledger: list of txns { txn_id, type, amount, from, to, booking_id, intent_id, fee, created_at, meta }
_ledger: List[Dict[str, Any]] = []

# platform config
_PLATFORM_FEE_PCT = 5.0  # percent fee on release by default


def _now_iso() -> str:
    return datetime.utcnow().isoformat()


def _record_txn(txn: Dict[str, Any]) -> None:
    with _lock:
        _ledger.append(txn)


# -----------------------
# Wallets
# -----------------------
def ensure_wallet(user_id: str) -> Dict[str, Any]:
    with _lock:
        w = _wallets.get(user_id)
        if not w:
            w = {"user_id": user_id, "balance": 0.0, "currency": "INR", "created_at": _now_iso()}
            _wallets[user_id] = w
    return w


def get_wallet_balance(user_id: str) -> Dict[str, Any]:
    w = ensure_wallet(user_id)
    return {"user_id": user_id, "balance": round(float(w["balance"]), 2), "currency": w.get("currency", "INR")}


def credit_wallet(user_id: str, amount: float, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Credit user's wallet (top-up). In production this occurs after gateway capture.
    """
    with _lock:
        w = ensure_wallet(user_id)
        w["balance"] = float(w.get("balance", 0.0)) + float(amount)
        tx = {
            "txn_id": f"txn_{uuid.uuid4()}",
            "type": "wallet_credit",
            "amount": float(amount),
            "from": meta.get("from") if meta else None,
            "to": user_id,
            "booking_id": meta.get("booking_id") if meta else None,
            "intent_id": meta.get("intent_id") if meta else None,
            "fee": 0.0,
            "created_at": _now_iso(),
            "meta": meta or {}
        }
        _record_txn(tx)
    return {"status": "credited", "wallet": get_wallet_balance(user_id), "txn": tx}


def debit_wallet(user_id: str, amount: float, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Debit user's wallet. Fails if insufficient balance.
    """
    with _lock:
        w = ensure_wallet(user_id)
        if float(w.get("balance", 0.0)) < float(amount):
            return {"error": "insufficient_funds", "balance": w.get("balance", 0.0)}
        w["balance"] = float(w.get("balance", 0.0)) - float(amount)
        tx = {
            "txn_id": f"txn_{uuid.uuid4()}",
            "type": "wallet_debit",
            "amount": float(amount),
            "from": user_id,
            "to": meta.get("to") if meta else None,
            "booking_id": meta.get("booking_id") if meta else None,
            "intent_id": meta.get("intent_id") if meta else None,
            "fee": 0.0,
            "created_at": _now_iso(),
            "meta": meta or {}
        }
        _record_txn(tx)
    return {"status": "debited", "wallet": get_wallet_balance(user_id), "txn": tx}


# -----------------------
# Payment intents (gateway stub)
# -----------------------
def create_payment_intent(user_id: str, amount: float, currency: str = "INR", payment_method: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Creates a payment intent stub. In production integrate with Stripe/PayU/CCAvenue/Instamojo/PG.
    Returns an intent_id which the frontend can use to complete payment.
    """
    intent_id = f"pi_{uuid.uuid4()}"
    intent = {
        "intent_id": intent_id,
        "user_id": user_id,
        "amount": round(float(amount), 2),
        "currency": currency,
        "payment_method": payment_method,
        "status": "created",
        "created_at": _now_iso(),
        "metadata": metadata or {}
    }
    with _lock:
        _payment_intents[intent_id] = intent
    return intent


def capture_payment_intent(intent_id: str, simulate_success: bool = True) -> Dict[str, Any]:
    """
    Simulate capturing a payment intent (gateway webhook would do this in reality).
    On success: mark intent captured and credit user's wallet.
    """
    with _lock:
        intent = _payment_intents.get(intent_id)
        if not intent:
            return {"error": "intent_not_found"}
        if intent["status"] in ["captured", "failed"]:
            return {"error": "invalid_intent_state", "state": intent["status"]}

        if simulate_success:
            intent["status"] = "captured"
            intent["captured_at"] = _now_iso()
            # credit wallet of user
            meta = {"intent_id": intent_id, "from": "gateway", "booking_id": intent.get("metadata", {}).get("booking_id")}
            credit_res = credit_wallet(intent["user_id"], float(intent["amount"]), meta=meta)
            return {"status": "captured", "intent": intent, "credit": credit_res}
        else:
            intent["status"] = "failed"
            intent["failed_at"] = _now_iso()
            return {"status": "failed", "intent": intent}


# -----------------------
# Escrow (per booking)
# -----------------------
def hold_in_escrow(booking_id: str, payer_user_id: str, amount: float, currency: str = "INR") -> Dict[str, Any]:
    """
    Move funds from payer wallet into escrow for booking.
    Fails if insufficient funds. Creates escrow record keyed by booking_id.
    """
    with _lock:
        if booking_id in _escrow_store and _escrow_store[booking_id]["status"] == "held":
            return {"error": "escrow_already_exists"}
        # debit payer wallet
        debit_res = debit_wallet(payer_user_id, amount, meta={"to": "escrow", "booking_id": booking_id})
        if "error" in debit_res:
            return {"error": "insufficient_funds", "details": debit_res}
        esc = {
            "escrow_id": f"esc_{uuid.uuid4()}",
            "booking_id": booking_id,
            "amount": round(float(amount), 2),
            "currency": currency,
            "payer": payer_user_id,
            "status": "held",
            "held_at": _now_iso(),
            "released_at": None,
            "released_to": None,
            "metadata": {}
        }
        _escrow_store[booking_id] = esc
        # record ledger
        _record_txn({
            "txn_id": f"txn_{uuid.uuid4()}",
            "type": "escrow_hold",
            "amount": float(amount),
            "from": payer_user_id,
            "to": f"escrow::{booking_id}",
            "booking_id": booking_id,
            "intent_id": None,
            "fee": 0.0,
            "created_at": _now_iso(),
            "meta": {}
        })
    return {"status": "held", "escrow": esc, "debit": debit_res}


def release_escrow_to_provider(booking_id: str, provider_user_id: str, platform_fee_pct: Optional[float] = None) -> Dict[str, Any]:
    """
    Release escrow for booking to provider wallet after deducting platform fee.
    """
    with _lock:
        esc = _escrow_store.get(booking_id)
        if not esc or esc.get("status") != "held":
            return {"error": "escrow_not_found_or_not_held"}
        amt = float(esc["amount"])
        fee_pct = float(platform_fee_pct) if platform_fee_pct is not None else _PLATFORM_FEE_PCT
        fee = round(amt * (fee_pct / 100.0), 2)
        payout = round(amt - fee, 2)

        # credit provider wallet
        credit_res = credit_wallet(provider_user_id, payout, meta={"from": f"escrow::{booking_id}", "booking_id": booking_id})
        # mark escrow released
        esc["status"] = "released"
        esc["released_at"] = _now_iso()
        esc["released_to"] = provider_user_id
        esc["fee_charged"] = fee
        _escrow_store[booking_id] = esc

        # ledger entries
        _record_txn({
            "txn_id": f"txn_{uuid.uuid4()}",
            "type": "escrow_release",
            "amount": payout,
            "from": f"escrow::{booking_id}",
            "to": provider_user_id,
            "booking_id": booking_id,
            "intent_id": None,
            "fee": fee,
            "created_at": _now_iso(),
            "meta": {"platform_fee_pct": fee_pct}
        })
        # platform fee txn (record only; platform account not modeled as wallet)
        _record_txn({
            "txn_id": f"txn_{uuid.uuid4()}",
            "type": "platform_fee",
            "amount": fee,
            "from": f"escrow::{booking_id}",
            "to": "platform",
            "booking_id": booking_id,
            "intent_id": None,
            "fee": 0.0,
            "created_at": _now_iso(),
            "meta": {"platform_fee_pct": fee_pct}
        })

    return {"status": "released", "escrow": esc, "credit": credit_res, "fee": fee}


def refund_escrow_to_payer(booking_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
    """
    Refund escrowed amount back to payer wallet (e.g., booking cancelled).
    """
    with _lock:
        esc = _escrow_store.get(booking_id)
        if not esc or esc.get("status") != "held":
            return {"error": "escrow_not_found_or_not_held"}
        amt = float(esc["amount"])
        payer = esc["payer"]
        # credit payer back
        credit_res = credit_wallet(payer, amt, meta={"from": f"escrow::{booking_id}", "booking_id": booking_id, "reason": reason})
        esc["status"] = "refunded"
        esc["released_at"] = _now_iso()
        esc["released_to"] = payer
        _escrow_store[booking_id] = esc

        _record_txn({
            "txn_id": f"txn_{uuid.uuid4()}",
            "type": "escrow_refund",
            "amount": amt,
            "from": f"escrow::{booking_id}",
            "to": payer,
            "booking_id": booking_id,
            "intent_id": None,
            "fee": 0.0,
            "created_at": _now_iso(),
            "meta": {"reason": reason}
        })
    return {"status": "refunded", "escrow": esc, "credit": credit_res}


# -----------------------
# Provider payout (withdraw from wallet to external payout — stub)
# -----------------------
def create_provider_payout(provider_user_id: str, amount: float, payout_method: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Simulate a payout: debits provider wallet and creates a payout ledger entry.
    Integration with bank / payment processor required for real payouts.
    """
    with _lock:
        w = ensure_wallet(provider_user_id)
        if float(w.get("balance", 0.0)) < float(amount):
            return {"error": "insufficient_funds", "balance": w.get("balance", 0.0)}
        # debit wallet
        debit_res = debit_wallet(provider_user_id, amount, meta={"to": "payout", "payout_method": payout_method})
        # record payout txn
        _record_txn({
            "txn_id": f"txn_{uuid.uuid4()}",
            "type": "provider_payout",
            "amount": float(amount),
            "from": provider_user_id,
            "to": "external_bank",
            "booking_id": None,
            "intent_id": None,
            "fee": 0.0,
            "created_at": _now_iso(),
            "meta": {"payout_method": payout_method}
        })
    return {"status": "initiated", "payout": {"provider": provider_user_id, "amount": amount, "method": payout_method}, "debit": debit_res}


# -----------------------
# Query / Audit
# -----------------------
def get_escrow(booking_id: str) -> Dict[str, Any]:
    return _escrow_store.get(booking_id, {})


def list_escrows(status: Optional[str] = None) -> List[Dict[str, Any]]:
    with _lock:
        items = list(_escrow_store.values())
    if status:
        items = [i for i in items if i.get("status") == status]
    return items


def list_ledger(limit: int = 200) -> List[Dict[str, Any]]:
    with _lock:
        return list(_ledger[-limit:])


def list_wallets() -> List[Dict[str, Any]]:
    with _lock:
        return list(_wallets.values())
