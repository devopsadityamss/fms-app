"""
Finance Ledger Service (Receivable & Payable Tracking)
------------------------------------------------------

This module tracks:
 - receivables (incoming money)
 - payables (outgoing money)

Each entry includes:
 - type: receivable | payable
 - amount
 - due_date
 - status: pending | paid | overdue
 - counterparty (buyer/supplier/etc.)
 - notes
 - optional unit_id to tie to a farm production unit

Everything is in-memory for now. Replace with DB integration later.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, date
import uuid


# ---------------------------------------------------------------------
# In-memory ledger store
# key = entry_id
# value = dict with ledger entry
# ---------------------------------------------------------------------
_ledger_store: Dict[str, Dict[str, Any]] = {}


def _new_id() -> str:
    return str(uuid.uuid4())


def _now() -> str:
    return datetime.utcnow().isoformat()


# ---------------------------------------------------------------------
# Helper: detect overdue status
# ---------------------------------------------------------------------
def _update_status(entry: Dict[str, Any]) -> None:
    if entry["status"] == "paid":
        return

    due = entry.get("due_date")
    if not due:
        return

    try:
        due_date = date.fromisoformat(due)
        if due_date < date.today():
            entry["status"] = "overdue"
        else:
            entry["status"] = "pending"
    except:
        # invalid date format, leave status unchanged
        pass


# ---------------------------------------------------------------------
# CRUD operations
# ---------------------------------------------------------------------
def create_entry(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Expected payload fields:
    - entry_type: receivable | payable
    - amount: float
    - due_date: yyyy-mm-dd (optional)
    - counterparty: str
    - notes: str
    - unit_id: str (optional)
    """
    entry_id = _new_id()
    entry = {
        "id": entry_id,
        "entry_type": payload.get("entry_type", "receivable"),
        "amount": float(payload.get("amount", 0)),
        "due_date": payload.get("due_date"),  # ISO date string
        "counterparty": payload.get("counterparty"),
        "unit_id": payload.get("unit_id"),
        "notes": payload.get("notes"),
        "status": "pending",
        "created_at": _now(),
        "updated_at": _now(),
    }

    _update_status(entry)
    _ledger_store[entry_id] = entry
    return entry


def get_entry(entry_id: str) -> Optional[Dict[str, Any]]:
    return _ledger_store.get(entry_id)


def update_entry(entry_id: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    entry = _ledger_store.get(entry_id)
    if not entry:
        return None

    for key in ("entry_type", "amount", "due_date", "counterparty", "notes", "unit_id", "status"):
        if key in payload:
            entry[key] = payload[key]

    entry["updated_at"] = _now()
    _update_status(entry)
    _ledger_store[entry_id] = entry
    return entry


def delete_entry(entry_id: str) -> bool:
    if entry_id in _ledger_store:
        del _ledger_store[entry_id]
        return True
    return False


# ---------------------------------------------------------------------
# Listing / Filtering
# ---------------------------------------------------------------------
def list_entries(
    entry_type: Optional[str] = None,
    unit_id: Optional[str] = None,
    status: Optional[str] = None
) -> Dict[str, Any]:

    items = list(_ledger_store.values())

    # auto-update statuses
    for i in items:
        _update_status(i)

    if entry_type:
        items = [i for i in items if i.get("entry_type") == entry_type]

    if unit_id:
        items = [i for i in items if i.get("unit_id") == unit_id]

    if status:
        items = [i for i in items if i.get("status") == status]

    return {"count": len(items), "items": items}


# ---------------------------------------------------------------------
# Summary Calculations
# ---------------------------------------------------------------------
def ledger_summary(unit_id: Optional[str] = None) -> Dict[str, Any]:
    items = list(_ledger_store.values())

    # Filter by unit if needed
    if unit_id:
        items = [i for i in items if i.get("unit_id") == unit_id]

    total_receivable = sum(i["amount"] for i in items if i["entry_type"] == "receivable")
    total_payable = sum(i["amount"] for i in items if i["entry_type"] == "payable")

    overdue = [i for i in items if i["status"] == "overdue"]

    return {
        "total_receivable": round(total_receivable, 2),
        "total_payable": round(total_payable, 2),
        "net_balance": round(total_receivable - total_payable, 2),
        "overdue_count": len(overdue),
        "overdue_items": overdue,
    }


# ---------------------------------------------------------------------
# For testing
# ---------------------------------------------------------------------
def _clear_store():
    _ledger_store.clear()
