# backend/app/api/farmer/financial_ledger.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.services.farmer.financial_ledger_service import (
    add_ledger_entry,
    list_entries,
    delete_entry,
    compute_cashflow_summary,
    get_top_expense_categories,
    get_cashflow_forecast,
    export_ledger_csv
)

router = APIRouter()


class LedgerEntryRequest(BaseModel):
    type: str
    category: str
    amount: float
    date: Optional[str] = None
    unit_id: Optional[str] = None
    description: Optional[str] = ""
    tags: Optional[List[str]] = []


@router.post("/ledger/add")
def api_add_entry(req: LedgerEntryRequest):
    if req.type not in ["income", "expense"]:
        raise HTTPException(status_code=400, detail="type must be income or expense")
    entry = add_ledger_entry(
        req.type,
        req.category,
        req.amount,
        req.date,
        req.unit_id,
        req.description,
        req.tags
    )
    return entry


@router.get("/ledger/list")
def api_list_entries(unit_id: Optional[str] = None, category: Optional[str] = None):
    return list_entries(unit_id=unit_id, category=category)


@router.delete("/ledger/{entry_id}")
def api_delete_entry(entry_id: str):
    ok = delete_entry(entry_id)
    if not ok:
        raise HTTPException(status_code=404, detail="entry_not_found")
    return {"deleted": True}


class CashflowSummaryRequest(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    unit_id: Optional[str] = None


@router.post("/ledger/cashflow/summary")
def api_cashflow_summary(req: CashflowSummaryRequest):
    return compute_cashflow_summary(
        unit_id=req.unit_id,
        start_date=req.start_date,
        end_date=req.end_date
    )


@router.get("/ledger/insights/top-categories")
def api_top_categories(unit_id: Optional[str] = None, top_n: int = 5):
    return get_top_expense_categories(unit_id=unit_id, top_n=top_n)


@router.get("/ledger/forecast")
def api_forecast(unit_id: Optional[str] = None):
    return get_cashflow_forecast(unit_id=unit_id)


@router.get("/ledger/export/csv")
def api_export_csv(unit_id: Optional[str] = None):
    csv_str = export_ledger_csv(unit_id)
    return {"csv": csv_str}
