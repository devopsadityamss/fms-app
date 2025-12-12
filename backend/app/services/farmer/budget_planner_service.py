"""
Budget Planner Service (stub-ready)
-----------------------------------

Tracks:
 - projected expenses
 - projected incomes
 - category-based budgeting
 - per-unit or overall farmer budgeting

Provides:
 - CRUD for budget items
 - Summaries: total income, total expense, net projection

In-memory store for now. Replace with DB integration later.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid


# ---------------------------------------------------------
# In-memory stores
# ---------------------------------------------------------
_budget_store: Dict[str, Dict[str, Any]] = {}  # stores individual items


def _now() -> str:
    return datetime.utcnow().isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------
# CRUD Operations
# ---------------------------------------------------------
def create_budget_item(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Expected fields:
      - type: expense | income
      - amount: float
      - category: fertilizer | labor | irrigation | crop_sales | misc | ...
      - unit_id: optional
      - notes: optional
    """
    item_id = _new_id()

    item = {
        "id": item_id,
        "type": payload.get("type", "expense"),
        "amount": float(payload.get("amount", 0)),
        "category": payload.get("category", "misc"),
        "unit_id": payload.get("unit_id"),
        "notes": payload.get("notes"),
        "created_at": _now(),
        "updated_at": _now(),
    }

    _budget_store[item_id] = item
    return item


def get_budget_item(item_id: str) -> Optional[Dict[str, Any]]:
    return _budget_store.get(item_id)


def update_budget_item(item_id: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    item = _budget_store.get(item_id)
    if not item:
        return None

    for key in ("type", "amount", "category", "unit_id", "notes"):
        if key in payload:
            item[key] = payload[key]

    item["updated_at"] = _now()
    _budget_store[item_id] = item
    return item


def delete_budget_item(item_id: str) -> bool:
    if item_id in _budget_store:
        del _budget_store[item_id]
        return True
    return False


# ---------------------------------------------------------
# Listing & Filtering
# ---------------------------------------------------------
def list_budget_items(
    item_type: Optional[str] = None,
    category: Optional[str] = None,
    unit_id: Optional[str] = None
) -> Dict[str, Any]:

    items = list(_budget_store.values())

    if item_type:
        items = [i for i in items if i.get("type") == item_type]

    if category:
        items = [i for i in items if i.get("category") == category]

    if unit_id:
        items = [i for i in items if i.get("unit_id") == unit_id]

    return {"count": len(items), "items": items}


# ---------------------------------------------------------
# Budget Summary
# ---------------------------------------------------------
def budget_summary(unit_id: Optional[str] = None) -> Dict[str, Any]:
    items = list(_budget_store.values())

    if unit_id:
        items = [i for i in items if i.get("unit_id") == unit_id]

    total_expense = sum(i["amount"] for i in items if i["type"] == "expense")
    total_income = sum(i["amount"] for i in items if i["type"] == "income")

    return {
        "total_expense": round(total_expense, 2),
        "total_income": round(total_income, 2),
        "net_projection": round(total_income - total_expense, 2),
        "item_count": len(items),
    }


# ---------------------------------------------------------
# Reset for testing
# ---------------------------------------------------------
def _clear_store():
    _budget_store.clear()
