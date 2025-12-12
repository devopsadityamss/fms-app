"""
Supplier Payment Scheduler Service (stub-ready)
----------------------------------------------

Allows farmers to manage supplier-side payments:

Payment record:
 - supplier_name
 - supplier_id (optional)
 - amount
 - due_date
 - category: fertilizer | seeds | tools | machinery | services | misc
 - status: pending | paid | overdue
 - notes
 - created_at, updated_at

Everything is in-memory now; upgrade to DB later.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, date
import uuid


_payment_store: Dict[str, Dict[str, Any]] = {}


def _new_id() -> str:
    return str(uuid.uuid4())


def _now() -> str:
    return datetime.utcnow().isoformat()


# -------------------------
# Helper: detect overdue status
# -------------------------
def _refresh_status(rec: Dict[str, Any]):
    if rec.get("status") == "paid":
        return

    due = rec.get("due_date")
    if not due:
        return

    try:
        d = date.fromisoformat(due)
        if d < date.today():
            rec["status"] = "overdue"
        else:
            rec["status"] = "pending"
    except:
        pass


# -------------------------
# CREATE
# -------------------------
def create_payment(payload: Dict[str, Any]) -> Dict[str, Any]:
    pay_id = _new_id()

    record = {
        "id": pay_id,
        "supplier_id": payload.get("supplier_id"),
        "supplier_name": payload.get("supplier_name"),
        "amount": float(payload.get("amount", 0)),
        "due_date": payload.get("due_date"),  # ISO date
        "category": payload.get("category", "misc"),
        "status": payload.get("status", "pending"),
        "notes": payload.get("notes"),
        "created_at": _now(),
        "updated_at": _now(),
    }

    _refresh_status(record)
    _payment_store[pay_id] = record
    return record


# -------------------------
# GET
# -------------------------
def get_payment(pay_id: str) -> Optional[Dict[str, Any]]:
    return _payment_store.get(pay_id)


# -------------------------
# UPDATE
# -------------------------
def update_payment(pay_id: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    rec = _payment_store.get(pay_id)
    if not rec:
        return None

    for k in ("supplier_id", "supplier_name", "amount", "due_date", "category", "status", "notes"):
        if k in payload:
            rec[k] = payload[k]

    rec["updated_at"] = _now()
    _refresh_status(rec)
    _payment_store[pay_id] = rec
    return rec


# -------------------------
# DELETE
# -------------------------
def delete_payment(pay_id: str) -> bool:
    if pay_id in _payment_store:
        del _payment_store[pay_id]
        return True
    return False


# -------------------------
# LIST / FILTER
# -------------------------
def list_payments(
    supplier_id: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None
) -> Dict[str, Any]:

    items = list(_payment_store.values())

    # refresh statuses
    for rec in items:
        _refresh_status(rec)

    if supplier_id:
        items = [i for i in items if i.get("supplier_id") == supplier_id]

    if category:
        items = [i for i in items if i.get("category") == category]

    if status:
        items = [i for i in items if i.get("status") == status]

    return {"count": len(items), "items": items}


# -------------------------
# SUMMARY
# -------------------------
def payment_summary() -> Dict[str, Any]:
    items = list(_payment_store.values())
    for i in items:
        _refresh_status(i)

    total_pending = sum(i["amount"] for i in items if i["status"] == "pending")
    total_overdue = sum(i["amount"] for i in items if i["status"] == "overdue")
    total_paid = sum(i["amount"] for i in items if i["status"] == "paid")

    return {
        "pending_amount": round(total_pending, 2),
        "overdue_amount": round(total_overdue, 2),
        "paid_amount": round(total_paid, 2),
        "total_payments": len(items)
    }


def _clear_store():
    _payment_store.clear()
