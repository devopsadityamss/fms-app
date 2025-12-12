"""
Loan EMI Calculator Service (stub-ready)
----------------------------------------

Responsibilities:
 - Calculate EMI based on principal, annual interest rate, and tenure months
 - Provide total interest and total payable
 - Store each calculation request in-memory
 - Optional notes and metadata

This module uses the standard EMI formula:
    EMI = P * r * (1+r)^n / ((1+r)^n - 1)

Everything here is easy to replace later with a more advanced finance engine.
"""

from typing import Dict, Any, Optional
from datetime import datetime
import uuid
import math


# ---------------------------------------------------------------------
# In-memory store
# ---------------------------------------------------------------------
_emi_store: Dict[str, Dict[str, Any]] = {}


def _now() -> str:
    return datetime.utcnow().isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------
# EMI calculation helpers
# ---------------------------------------------------------------------
def _calculate_emi(principal: float, annual_rate: float, months: int) -> Dict[str, float]:
    """
    Calculates EMI and totals based on:
     principal (P)
     annual_rate in percent
     months (n)
    """
    if months <= 0:
        raise ValueError("months must be > 0")

    monthly_rate = annual_rate / (12 * 100)  # convert to monthly decimal

    if monthly_rate == 0:
        # no interest loan
        emi = principal / months
    else:
        emi = principal * monthly_rate * (1 + monthly_rate) ** months / ((1 + monthly_rate) ** months - 1)

    total_payable = emi * months
    total_interest = total_payable - principal

    return {
        "emi": round(emi, 2),
        "total_interest": round(total_interest, 2),
        "total_payable": round(total_payable, 2),
    }


# ---------------------------------------------------------------------
# MAIN ENTRY
# ---------------------------------------------------------------------
def calculate_emi(
    principal: float,
    annual_rate: float,
    tenure_months: int,
    notes: Optional[str] = None,
    unit_id: Optional[str] = None
) -> Dict[str, Any]:

    calculation_id = _new_id()

    try:
        result = _calculate_emi(principal, annual_rate, tenure_months)
    except Exception as e:
        return {"error": "calculation_failed", "details": str(e)}

    record = {
        "id": calculation_id,
        "principal": principal,
        "annual_rate": annual_rate,
        "tenure_months": tenure_months,
        "generated_at": _now(),
        "results": result,
        "unit_id": unit_id,
        "notes": notes
    }

    _emi_store[calculation_id] = record
    return record


def get_calculation(calculation_id: str) -> Optional[Dict[str, Any]]:
    return _emi_store.get(calculation_id)


def list_calculations(unit_id: Optional[str] = None) -> Dict[str, Any]:
    items = list(_emi_store.values())
    if unit_id:
        items = [i for i in items if i.get("unit_id") == unit_id]
    return {"count": len(items), "items": items}


def _clear_store():
    _emi_store.clear()
