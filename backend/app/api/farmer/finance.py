# backend/app/api/farmer/finance.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.services.farmer.finance_service import (
    # wallets
    wallet_balance,
    topup_wallet,
    withdraw_wallet,

    # ledger
    add_ledger_entry,
    query_ledger,
    get_entry,
    update_entry,
    delete_entry,
    export_ledger_csv,
    monthly_summary,
    cashflow_summary,
    top_categories,
    bulk_import_entries,

    # subsidies
    create_subsidy_rule,
    list_subsidy_rules,
    apply_subsidy_rule,

    # invoices/payments
    create_invoice,
    get_invoice,
    list_invoices,
    record_invoice_payment,

    # payouts
    record_payout,
    list_payouts,

    # summary
    finance_summary
)

router = APIRouter()


# -------------------------------------------------------------------
# Pydantic Models
# -------------------------------------------------------------------

class TopupPayload(BaseModel):
    farmer_id: str
    amount: float
    source: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class WithdrawPayload(BaseModel):
    farmer_id: str
    amount: float
    destination: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class LedgerPayload(BaseModel):
    farmer_id: str
    unit_id: Optional[str] = None
    entry_type: str
    category: str
    amount: float
    currency: Optional[str] = "INR"
    date_iso: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None

class BulkImportPayload(BaseModel):
    rows: List[Dict[str, Any]]
    default_farmer_id: Optional[str] = None

class SubsidyRulePayload(BaseModel):
    name: str
    rule_type: str   # percent|fixed
    value: float
    eligible_categories: Optional[List[str]] = None
    active: Optional[bool] = True

class ApplySubsidyPayload(BaseModel):
    rule_id: str
    farmer_id: str
    expense_entry_id: str

class InvoiceItem(BaseModel):
    description: str
    qty: Optional[float] = 1
    unit_price: Optional[float] = 0.0
    total_amount: Optional[float] = None
    unit: Optional[str] = "kg"

class InvoicePayload(BaseModel):
    farmer_id: str
    to_id: str
    items: List[InvoiceItem]
    currency: Optional[str] = "INR"
    due_date_iso: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class InvoicePaymentPayload(BaseModel):
    invoice_id: str
    paid_by: str
    amount: float
    payment_method: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class PayoutPayload(BaseModel):
    source: str
    farmer_id: str
    amount: float
    reference: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


# -------------------------------------------------------------------
# Wallet Routes
# -------------------------------------------------------------------

@router.get("/farmer/finance/wallet/{farmer_id}")
def api_wallet_balance(farmer_id: str):
    return wallet_balance(farmer_id)


@router.post("/farmer/finance/wallet/topup")
def api_wallet_topup(req: TopupPayload):
    res = topup_wallet(req.farmer_id, req.amount, source=req.source, metadata=req.metadata)
    if "error" in res:
        raise HTTPException(400, res["error"])
    return res


@router.post("/farmer/finance/wallet/withdraw")
def api_wallet_withdraw(req: WithdrawPayload):
    res = withdraw_wallet(req.farmer_id, req.amount, destination=req.destination, metadata=req.metadata)
    if "error" in res:
        raise HTTPException(400, res["error"])
    return res


# -------------------------------------------------------------------
# Ledger Routes
# -------------------------------------------------------------------

@router.post("/farmer/finance/ledger/add")
def api_add_ledger(req: LedgerPayload):
    return add_ledger_entry(
        farmer_id=req.farmer_id,
        unit_id=req.unit_id,
        entry_type=req.entry_type,
        category=req.category,
        amount=req.amount,
        currency=req.currency,
        date_iso=req.date_iso,
        description=req.description,
        tags=req.tags,
        metadata=req.metadata
    )


@router.get("/farmer/finance/ledger/query")
def api_query_ledger(
    farmer_id: Optional[str] = None,
    unit_id: Optional[str] = None,
    from_date_iso: Optional[str] = None,
    to_date_iso: Optional[str] = None,
    types: Optional[str] = None,
    categories: Optional[str] = None,
    tags: Optional[str] = None,
    limit: int = 200,
    offset: int = 0
):
    types_list = types.split(",") if types else None
    cat_list = categories.split(",") if categories else None
    tag_list = tags.split(",") if tags else None

    return query_ledger(
        farmer_id=farmer_id,
        unit_id=unit_id,
        from_date_iso=from_date_iso,
        to_date_iso=to_date_iso,
        types=types_list,
        categories=cat_list,
        tags=tag_list,
        limit=limit,
        offset=offset
    )


@router.get("/farmer/finance/ledger/entry/{entry_id}")
def api_get_entry(entry_id: str):
    res = get_entry(entry_id)
    if not res:
        raise HTTPException(404, "entry_not_found")
    return res


@router.post("/farmer/finance/ledger/update/{entry_id}")
def api_update_entry(entry_id: str, updates: Dict[str, Any]):
    res = update_entry(entry_id, updates)
    if "error" in res:
        raise HTTPException(404, res["error"])
    return res


@router.delete("/farmer/finance/ledger/delete/{entry_id}")
def api_delete_entry(entry_id: str):
    res = delete_entry(entry_id)
    if "error" in res:
        raise HTTPException(404, res["error"])
    return res


@router.get("/farmer/finance/ledger/export_csv/{farmer_id}")
def api_export_csv(farmer_id: str, from_date_iso: Optional[str] = None, to_date_iso: Optional[str] = None):
    return {"csv": export_ledger_csv(farmer_id, from_date_iso, to_date_iso)}


# -------------------------------------------------------------------
# Monthly, Cashflow, Top Categories
# -------------------------------------------------------------------

@router.get("/farmer/finance/monthly/{farmer_id}")
def api_monthly(farmer_id: str, year: Optional[int] = None):
    return monthly_summary(farmer_id, year)


@router.get("/farmer/finance/cashflow/{farmer_id}")
def api_cashflow(farmer_id: str, from_date_iso: Optional[str] = None, to_date_iso: Optional[str] = None):
    return cashflow_summary(farmer_id, from_date_iso, to_date_iso)


@router.get("/farmer/finance/top_categories/{farmer_id}")
def api_top_categories(farmer_id: str, top_n: int = 10):
    return top_categories(farmer_id, top_n=top_n)


# -------------------------------------------------------------------
# Subsidy Routes
# -------------------------------------------------------------------

@router.post("/farmer/finance/subsidy_rule")
def api_create_subsidy_rule(req: SubsidyRulePayload):
    res = create_subsidy_rule(req.name, req.rule_type, req.value, req.eligible_categories, req.active)
    if "error" in res:
        raise HTTPException(400, res["error"])
    return res


@router.get("/farmer/finance/subsidy_rules")
def api_list_rules(active_only: bool = True):
    return {"rules": list_subsidy_rules(active_only=active_only)}


@router.post("/farmer/finance/apply_subsidy")
def api_apply_subsidy(req: ApplySubsidyPayload):
    res = apply_subsidy_rule(req.rule_id, req.farmer_id, req.expense_entry_id)
    if "error" in res:
        raise HTTPException(400, res["error"])
    return res


# -------------------------------------------------------------------
# Bulk Import
# -------------------------------------------------------------------

@router.post("/farmer/finance/bulk_import")
def api_bulk_import(req: BulkImportPayload):
    return bulk_import_entries(req.rows, req.default_farmer_id)


# -------------------------------------------------------------------
# Invoice Routes
# -------------------------------------------------------------------

@router.post("/farmer/finance/invoice")
def api_create_invoice(req: InvoicePayload):
    items = [it.dict() for it in req.items]
    return create_invoice(req.farmer_id, req.to_id, items, req.currency, req.due_date_iso, req.metadata)


@router.get("/farmer/finance/invoice/{invoice_id}")
def api_get_invoice(invoice_id: str):
    inv = get_invoice(invoice_id)
    if not inv:
        raise HTTPException(404, "invoice_not_found")
    return inv


@router.get("/farmer/finance/invoices")
def api_list_all_invoices(farmer_id: Optional[str] = None, status: Optional[str] = None):
    return {"invoices": list_invoices(farmer_id, status)}


@router.post("/farmer/finance/invoice/payment")
def api_invoice_payment(req: InvoicePaymentPayload):
    res = record_invoice_payment(req.invoice_id, req.paid_by, req.amount, req.payment_method, req.metadata)
    if "error" in res:
        raise HTTPException(400, res["error"])
    return res


# -------------------------------------------------------------------
# Payout Routes
# -------------------------------------------------------------------

@router.post("/farmer/finance/payout")
def api_payout(req: PayoutPayload):
    return record_payout(req.source, req.farmer_id, req.amount, req.reference, req.metadata)


@router.get("/farmer/finance/payouts")
def api_list_payouts(limit: int = 200):
    return {"payouts": list_payouts(limit)}


# -------------------------------------------------------------------
# Finance Summary Route
# -------------------------------------------------------------------

@router.get("/farmer/finance/summary/{farmer_id}")
def api_finance_summary(farmer_id: str):
    return finance_summary(farmer_id)
