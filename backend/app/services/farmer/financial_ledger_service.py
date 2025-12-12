# backend/app/services/farmer/financial_ledger_service.py

from datetime import datetime, date
from threading import Lock
from typing import List, Dict, Any, Optional
import csv
import io
import math

# Ledger entry structure:
# {
#   "entry_id": str,
#   "unit_id": Optional[str],
#   "type": "expense" | "income",
#   "category": str,
#   "amount": float,
#   "date": "YYYY-MM-DD",
#   "description": str,
#   "tags": List[str],
#   "created_at": timestamp ISO
# }

_ledger_store: List[Dict[str, Any]] = []
_ledger_lock = Lock()


def _generate_entry_id() -> str:
    return f"ledger_{int(datetime.utcnow().timestamp() * 1000)}"


def _parse_date(d: str) -> date:
    try:
        return datetime.fromisoformat(d).date()
    except:
        return datetime.utcnow().date()


# -------------------------------------------------------------
# CRUD operations for entries
# -------------------------------------------------------------
def add_ledger_entry(
    entry_type: str,
    category: str,
    amount: float,
    date_iso: Optional[str] = None,
    unit_id: Optional[str] = None,
    description: str = "",
    tags: Optional[List[str]] = None
) -> Dict[str, Any]:

    entry = {
        "entry_id": _generate_entry_id(),
        "unit_id": unit_id,
        "type": entry_type,  # "expense" or "income"
        "category": category.lower(),
        "amount": float(amount),
        "date": date_iso or datetime.utcnow().date().isoformat(),
        "description": description,
        "tags": tags or [],
        "created_at": datetime.utcnow().isoformat()
    }

    with _ledger_lock:
        _ledger_store.append(entry)

    return entry


def list_entries(unit_id: Optional[str] = None, category: Optional[str] = None) -> List[Dict[str, Any]]:
    with _ledger_lock:
        items = list(_ledger_store)

    if unit_id:
        items = [e for e in items if e.get("unit_id") == unit_id]

    if category:
        items = [e for e in items if e.get("category") == category.lower()]

    return items


def delete_entry(entry_id: str) -> bool:
    with _ledger_lock:
        for idx, e in enumerate(_ledger_store):
            if e["entry_id"] == entry_id:
                _ledger_store.pop(idx)
                return True
    return False


# -------------------------------------------------------------
# Cashflow Analytics
# -------------------------------------------------------------
def compute_cashflow_summary(
    unit_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Dict[str, Any]:

    sd = _parse_date(start_date) if start_date else None
    ed = _parse_date(end_date) if end_date else None

    entries = list_entries(unit_id=unit_id)

    filtered = []
    for e in entries:
        d = _parse_date(e["date"])
        if sd and d < sd:
            continue
        if ed and d > ed:
            continue
        filtered.append(e)

    total_in = sum(e["amount"] for e in filtered if e["type"] == "income")
    total_out = sum(e["amount"] for e in filtered if e["type"] == "expense")

    net = total_in - total_out

    # category-wise spending
    categories: Dict[str, float] = {}
    for e in filtered:
        if e["type"] == "expense":
            categories[e["category"]] = categories.get(e["category"], 0) + e["amount"]

    # monthly breakdown
    monthly: Dict[str, float] = {}
    for e in filtered:
        m = e["date"][:7]  # "YYYY-MM"
        if e["type"] == "expense":
            monthly[m] = monthly.get(m, 0) + e["amount"]

    return {
        "total_income": round(total_in, 2),
        "total_expense": round(total_out, 2),
        "net_cashflow": round(net, 2),
        "category_expense": categories,
        "monthly_expense": monthly,
        "records": len(filtered),
        "start_date": start_date,
        "end_date": end_date,
        "generated_at": datetime.utcnow().isoformat()
    }


# -------------------------------------------------------------
# Ledger insights
# -------------------------------------------------------------
def get_top_expense_categories(unit_id: Optional[str] = None, top_n: int = 5) -> Dict[str, Any]:
    entries = list_entries(unit_id=unit_id)
    categories: Dict[str, float] = {}
    for e in entries:
        if e["type"] == "expense":
            categories[e["category"]] = categories.get(e["category"], 0) + e["amount"]

    ranked = sorted(categories.items(), key=lambda x: x[1], reverse=True)
    return {
        "top_categories": ranked[:top_n],
        "unit_id": unit_id,
        "generated_at": datetime.utcnow().isoformat(),
    }


def get_cashflow_forecast(unit_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Simplistic forecast: Use last 3 months average expense → next month projection.
    """
    entries = list_entries(unit_id=unit_id)

    monthly: Dict[str, float] = {}
    for e in entries:
        if e["type"] == "expense":
            m = e["date"][:7]  # YYYY-MM
            monthly[m] = monthly.get(m, 0) + e["amount"]

    # find last 3
    months_sorted = sorted(monthly.keys(), reverse=True)
    last3 = months_sorted[:3]
    if last3:
        avg = sum(monthly[m] for m in last3) / len(last3)
    else:
        avg = 0

    return {
        "forecast_next_month_expense": round(avg, 2),
        "basis_months": last3,
        "unit_id": unit_id,
        "generated_at": datetime.utcnow().isoformat()
    }


# -------------------------------------------------------------
# Export to CSV
# -------------------------------------------------------------
def export_ledger_csv(unit_id: Optional[str] = None) -> str:
    entries = list_entries(unit_id=unit_id)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["entry_id", "unit_id", "type", "category", "amount", "date", "description", "tags"])

    for e in entries:
        writer.writerow([
            e["entry_id"],
            e.get("unit_id"),
            e["type"],
            e["category"],
            e["amount"],
            e["date"],
            e["description"],
            ",".join(e["tags"]),
        ])

    return output.getvalue()
