"""
Contract Farming Planner Service (stub-ready)
---------------------------------------------

Tracks farmer–buyer contract agreements.

Contract Includes:
 - buyer_id
 - unit_id (optional)
 - contract_price_per_kg
 - expected_quantity_kg
 - start_date, end_date
 - milestones (payment schedule, delivery schedule)
 - quality_requirements (stub)
 - status: active | completed | cancelled
 - risk_score (stub)
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid


_contract_store: Dict[str, Dict[str, Any]] = {}


def _now() -> str:
    return datetime.utcnow().isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


# -------------------------------------------------------
# Stubbed Risk Model
# -------------------------------------------------------
def _compute_risk_stub(price: float, expected_qty: float, duration_days: int) -> float:
    """
    Simple heuristic:
     - longer contracts = higher risk
     - larger quantities = higher risk
     - very high contract price = low risk (buyer committed strongly)
    """
    base = 0.5

    if duration_days > 120:
        base += 0.15
    if expected_qty > 5000:
        base += 0.1
    if price > 40:
        base -= 0.1

    return round(max(0.1, min(0.95, base)), 3)


# -------------------------------------------------------
# CREATE
# -------------------------------------------------------
def create_contract(payload: Dict[str, Any]) -> Dict[str, Any]:
    contract_id = _new_id()

    start = payload.get("start_date")
    end = payload.get("end_date")

    # compute duration
    try:
        d_start = datetime.fromisoformat(start)
        d_end = datetime.fromisoformat(end)
        duration_days = (d_end - d_start).days
    except Exception:
        duration_days = 90  # fallback

    price = float(payload.get("contract_price_per_kg", 0))
    qty = float(payload.get("expected_quantity_kg", 0))

    risk = _compute_risk_stub(price, qty, duration_days)

    record = {
        "id": contract_id,
        "buyer_id": payload.get("buyer_id"),
        "unit_id": payload.get("unit_id"),
        "contract_price_per_kg": price,
        "expected_quantity_kg": qty,
        "start_date": start,
        "end_date": end,
        "milestones": payload.get("milestones", []),  # list of dicts
        "quality_requirements": payload.get("quality_requirements", {}),
        "status": payload.get("status", "active"),
        "risk_score": risk,
        "notes": payload.get("notes"),
        "created_at": _now(),
        "updated_at": _now(),
    }

    _contract_store[contract_id] = record
    return record


# -------------------------------------------------------
# GET
# -------------------------------------------------------
def get_contract(contract_id: str) -> Optional[Dict[str, Any]]:
    return _contract_store.get(contract_id)


# -------------------------------------------------------
# UPDATE
# -------------------------------------------------------
def update_contract(contract_id: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    rec = _contract_store.get(contract_id)
    if not rec:
        return None

    for key in (
        "buyer_id",
        "unit_id",
        "contract_price_per_kg",
        "expected_quantity_kg",
        "start_date",
        "end_date",
        "milestones",
        "quality_requirements",
        "notes",
        "status",
    ):
        if key in payload:
            rec[key] = payload[key]

    # recompute risk on major fields
    try:
        d_start = datetime.fromisoformat(rec.get("start_date"))
        d_end = datetime.fromisoformat(rec.get("end_date"))
        duration_days = (d_end - d_start).days
    except:
        duration_days = 90

    rec["risk_score"] = _compute_risk_stub(
        float(rec.get("contract_price_per_kg", 0)),
        float(rec.get("expected_quantity_kg", 0)),
        duration_days,
    )

    rec["updated_at"] = _now()
    return rec


# -------------------------------------------------------
# DELETE
# -------------------------------------------------------
def delete_contract(contract_id: str) -> bool:
    if contract_id in _contract_store:
        del _contract_store[contract_id]
        return True
    return False


# -------------------------------------------------------
# LIST + Filters
# -------------------------------------------------------
def list_contracts(
    buyer_id: Optional[str] = None,
    unit_id: Optional[str] = None,
    status: Optional[str] = None,
) -> Dict[str, Any]:

    items = list(_contract_store.values())

    if buyer_id:
        items = [i for i in items if i.get("buyer_id") == buyer_id]

    if unit_id:
        items = [i for i in items if i.get("unit_id") == unit_id]

    if status:
        items = [i for i in items if i.get("status") == status]

    return {"count": len(items), "items": items}


# -------------------------------------------------------
# Summary
# -------------------------------------------------------
def contract_summary(contract_id: str) -> Optional[Dict[str, Any]]:
    rec = _contract_store.get(contract_id)
    if not rec:
        return None

    summary = {
        "id": rec["id"],
        "buyer_id": rec["buyer_id"],
        "unit_id": rec["unit_id"],
        "duration": f"{rec['start_date']} → {rec['end_date']}",
        "expected_revenue": round(rec["contract_price_per_kg"] * rec["expected_quantity_kg"], 2),
        "risk_score": rec["risk_score"],
        "milestone_count": len(rec.get("milestones", [])),
        "status": rec["status"],
    }
    return summary


def _clear_store():
    _contract_store.clear()
