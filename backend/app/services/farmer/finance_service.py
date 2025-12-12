# backend/app/services/farmer/finance_service.py

"""
Unified Finance Service (in-memory)

Combines:
 - original Ledger, Subsidy Management, Bulk Import, CSV export, Monthly summaries, Cashflow, Top categories
 - Wallets (topup/withdraw), Invoices, Invoice Payments, Payouts (insurance/marketplace), Payments ledger entries
 - All ledger activity is recorded via add_ledger_entry(...) so the ledger stays canonical.

NOTE:
 - Keep this as the single source of truth for all finance flows.
 - For persistence, replace the in-memory stores with DB models and keep the API unchanged.
"""

from datetime import datetime, date, timedelta
from threading import Lock
from typing import Dict, Any, List, Optional
import uuid
import csv
import io
import statistics

_lock = Lock()

# ------------------------------------------------------------------
# Canonical ledger (original)
# ------------------------------------------------------------------
_ledger: List[Dict[str, Any]] = []
_subsidy_rules: Dict[str, Dict[str, Any]] = {}  # rule_id -> { name, type: percent|fixed, value, eligible_categories, active, created_at }

# ------------------------------------------------------------------
# Wallets, Invoices, Payments, Payouts (new additions)
# ------------------------------------------------------------------
_wallets: Dict[str, Dict[str, Any]] = {}           # farmer_id -> {balance, currency, updated_at}
_invoices: Dict[str, Dict[str, Any]] = {}          # invoice_id -> invoice record
_invoices_by_farmer: Dict[str, List[str]] = {}     # farmer_id -> [invoice_ids]
_payments: Dict[str, Dict[str, Any]] = {}          # payment_id -> payment record
_payouts: List[Dict[str, Any]] = []                # payout records (insurance/marketplace)

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def _now_iso() -> str:
    return datetime.utcnow().isoformat()

def _newid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4()}"

# ------------------------------------------------------------------
# Ledger operations (your original implementation)
# ------------------------------------------------------------------
def _new_entry_id() -> str:
    return f"entry_{uuid.uuid4()}"

def add_ledger_entry(
    farmer_id: str,
    unit_id: Optional[str],
    entry_type: str,  # income | expense | subsidy | transfer
    category: str,
    amount: float,
    currency: str = "INR",
    date_iso: Optional[str] = None,
    description: Optional[str] = None,
    tags: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    if entry_type not in ("income", "expense", "subsidy", "transfer"):
        return {"error": "invalid_entry_type"}
    ent = {
        "entry_id": _new_entry_id(),
        "farmer_id": farmer_id,
        "unit_id": unit_id,
        "type": entry_type,
        "category": category,
        "amount": round(float(amount), 2),
        "currency": currency,
        "date_iso": date_iso or datetime.utcnow().date().isoformat(),
        "description": description or "",
        "tags": tags or [],
        "metadata": metadata or {},
        "created_at": _now_iso()
    }
    with _lock:
        _ledger.append(ent)
    return ent

def get_entry(entry_id: str) -> Dict[str, Any]:
    with _lock:
        for e in _ledger:
            if e["entry_id"] == entry_id:
                return e
    return {}

def update_entry(entry_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    with _lock:
        for i,e in enumerate(_ledger):
            if e["entry_id"] == entry_id:
                e.update(updates)
                e["updated_at"] = _now_iso()
                _ledger[i] = e
                return e
    return {"error": "not_found"}

def delete_entry(entry_id: str) -> Dict[str, Any]:
    with _lock:
        for i,e in enumerate(_ledger):
            if e["entry_id"] == entry_id:
                _ledger.pop(i)
                return {"status": "deleted", "entry_id": entry_id}
    return {"error": "not_found"}

# ------------------------------------------------------------------
# Querying (original)
# ------------------------------------------------------------------
def query_ledger(
    farmer_id: Optional[str] = None,
    unit_id: Optional[str] = None,
    from_date_iso: Optional[str] = None,
    to_date_iso: Optional[str] = None,
    types: Optional[List[str]] = None,
    categories: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    limit: int = 200,
    offset: int = 0
) -> Dict[str, Any]:
    with _lock:
        items = list(_ledger)

    def in_range(diso: str, start: Optional[str], end: Optional[str]) -> bool:
        try:
            d = datetime.fromisoformat(diso).date()
        except Exception:
            try:
                d = datetime.fromisoformat(diso + "T00:00:00").date()
            except Exception:
                return False
        if start:
            try:
                s = datetime.fromisoformat(start).date()
                if d < s: return False
            except:
                pass
        if end:
            try:
                t = datetime.fromisoformat(end).date()
                if d > t: return False
            except:
                pass
        return True

    filtered = []
    for e in items:
        if farmer_id and e.get("farmer_id") != farmer_id:
            continue
        if unit_id and e.get("unit_id") != unit_id:
            continue
        if types and e.get("type") not in types:
            continue
        if categories and e.get("category") not in categories:
            continue
        if tags:
            if not any(t in e.get("tags",[]) for t in tags):
                continue
        if not in_range(e.get("date_iso"), from_date_iso, to_date_iso):
            continue
        filtered.append(e)

    total = len(filtered)
    sliced = filtered[offset: offset + limit]
    return {"total": total, "count": len(sliced), "items": sliced}

# ------------------------------------------------------------------
# Monthly summary / P&L (original)
# ------------------------------------------------------------------
def monthly_summary(farmer_id: str, year: Optional[int] = None) -> Dict[str, Any]:
    with _lock:
        items = [e for e in _ledger if e.get("farmer_id") == farmer_id]
    by_month: Dict[str, Dict[str, float]] = {}
    for e in items:
        try:
            d = datetime.fromisoformat(e.get("date_iso")).date()
        except Exception:
            try:
                d = datetime.fromisoformat(e.get("date_iso") + "T00:00:00").date()
            except:
                continue
        if year and d.year != int(year):
            continue
        key = f"{d.year}-{d.month:02d}"
        m = by_month.setdefault(key, {"income": 0.0, "expense": 0.0, "subsidy": 0.0})
        if e.get("type") == "income":
            m["income"] += e.get("amount",0)
        elif e.get("type") == "expense":
            m["expense"] += e.get("amount",0)
        elif e.get("type") == "subsidy":
            m["subsidy"] += e.get("amount",0)
    out = []
    for k, v in sorted(by_month.items()):
        profit = round(v["income"] + v["subsidy"] - v["expense"], 2)
        out.append({"month": k, "income": round(v["income"],2), "expense": round(v["expense"],2), "subsidy": round(v["subsidy"],2), "profit": profit})
    return {"farmer_id": farmer_id, "months": out}

# ------------------------------------------------------------------
# Cashflow summary (original)
# ------------------------------------------------------------------
def cashflow_summary(farmer_id: str, from_date_iso: Optional[str] = None, to_date_iso: Optional[str] = None) -> Dict[str, Any]:
    q = query_ledger(farmer_id=farmer_id, from_date_iso=from_date_iso, to_date_iso=to_date_iso, limit=10000)
    items = q.get("items", [])
    balance = 0.0
    timeline = []
    for e in sorted(items, key=lambda x: x.get("date_iso")):
        amt = float(e.get("amount",0))
        if e.get("type") == "income" or e.get("type") == "subsidy":
            balance += amt
        else:
            balance -= amt
        timeline.append({"date": e.get("date_iso"), "entry_id": e.get("entry_id"), "type": e.get("type"), "amount": amt, "balance": round(balance,2)})
    return {"farmer_id": farmer_id, "ending_balance": round(balance,2), "timeline": timeline}

# ------------------------------------------------------------------
# Subsidy rules & application (original)
# ------------------------------------------------------------------
def create_subsidy_rule(name: str, rule_type: str, value: float, eligible_categories: Optional[List[str]] = None, active: bool = True) -> Dict[str, Any]:
    if rule_type not in ("percent", "fixed"):
        return {"error": "invalid_rule_type"}
    rid = f"sub_{uuid.uuid4()}"
    rec = {"rule_id": rid, "name": name, "type": rule_type, "value": float(value), "eligible_categories": eligible_categories or [], "active": bool(active), "created_at": _now_iso()}
    with _lock:
        _subsidy_rules[rid] = rec
    return rec

def list_subsidy_rules(active_only: bool = True) -> List[Dict[str, Any]]:
    with _lock:
        rules = list(_subsidy_rules.values())
    if active_only:
        rules = [r for r in rules if r.get("active")]
    return rules

def apply_subsidy_rule(rule_id: str, farmer_id: str, expense_entry_id: str) -> Dict[str, Any]:
    with _lock:
        rule = _subsidy_rules.get(rule_id)
        if not rule:
            return {"error": "rule_not_found"}
    expense = get_entry(expense_entry_id)
    if not expense or expense.get("type") != "expense":
        return {"error": "expense_not_found"}
    eligible = True
    elig_cats = rule.get("eligible_categories") or []
    if elig_cats and expense.get("category") not in elig_cats:
        eligible = False
    if not eligible:
        return {"error": "not_eligible"}

    amt = float(expense.get("amount",0))
    if rule.get("type") == "percent":
        subsidy_amt = round(amt * (rule.get("value",0) / 100.0), 2)
    else:
        subsidy_amt = round(rule.get("value",0), 2)

    # create subsidy ledger entry using canonical ledger
    sub_entry = add_ledger_entry(
        farmer_id=expense.get("farmer_id"),
        unit_id=expense.get("unit_id"),
        entry_type="subsidy",
        category=f"subsidy::{rule.get('name')}",
        amount=subsidy_amt,
        currency=expense.get("currency","INR"),
        date_iso=_now_iso(),
        description=f"Subsidy applied for expense {expense_entry_id} via rule {rule_id}",
        tags=["subsidy", rule.get("name")],
        metadata={"applied_to": expense_entry_id, "rule_id": rule_id}
    )
    return {"status": "applied", "subsidy_entry": sub_entry}

# ------------------------------------------------------------------
# Bulk import (original)
# ------------------------------------------------------------------
def bulk_import_entries(rows: List[Dict[str, Any]], default_farmer_id: Optional[str] = None) -> Dict[str, Any]:
    ingested = []
    errors = []
    for idx, r in enumerate(rows):
        try:
            farmer_id = r.get("farmer_id") or default_farmer_id
            if not farmer_id:
                raise ValueError("missing farmer_id")
            ent = add_ledger_entry(
                farmer_id=farmer_id,
                unit_id=r.get("unit_id"),
                entry_type=r.get("type"),
                category=r.get("category") or "import",
                amount=float(r.get("amount",0)),
                currency=r.get("currency","INR"),
                date_iso=r.get("date_iso"),
                description=r.get("description"),
                tags=r.get("tags", []),
                metadata=r.get("metadata", {})
            )
            ingested.append(ent)
        except Exception as e:
            errors.append({"row": idx, "error": str(e)})
    return {"ingested_count": len(ingested), "ingested": ingested, "errors": errors}

# ------------------------------------------------------------------
# Quick analytics (original)
# ------------------------------------------------------------------
def top_categories(farmer_id: str, top_n: int = 10) -> Dict[str, Any]:
    q = query_ledger(farmer_id=farmer_id, limit=10000)
    items = q.get("items", [])
    cat_map: Dict[str, float] = {}
    for e in items:
        cat = e.get("category") or "uncategorized"
        amt = float(e.get("amount",0))
        # keep sign logic consistent: expense reduces, income adds; but we aggregate absolute amounts per category
        cat_map[cat] = cat_map.get(cat, 0.0) + amt
    sorted_cats = sorted(cat_map.items(), key=lambda x: x[1], reverse=True)[:top_n]
    return {"top_categories": [{"category": k, "amount": round(v,2)} for k,v in sorted_cats]}

# ------------------------------------------------------------------
# Export (original)
# ------------------------------------------------------------------
def export_ledger_csv(farmer_id: str, from_date_iso: Optional[str] = None, to_date_iso: Optional[str] = None) -> str:
    q = query_ledger(farmer_id=farmer_id, from_date_iso=from_date_iso, to_date_iso=to_date_iso, limit=10000)
    items = q.get("items", [])
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["entry_id","date_iso","type","category","amount","currency","unit_id","description","tags"])
    for e in items:
        writer.writerow([e.get("entry_id"), e.get("date_iso"), e.get("type"), e.get("category"), e.get("amount"), e.get("currency"), e.get("unit_id"), e.get("description",""), ";".join(e.get("tags",[]))])
    return output.getvalue()

# ------------------------------------------------------------------
# Wallet operations (new) - integrated with ledger
# ------------------------------------------------------------------
def ensure_wallet(farmer_id: str, currency: str = "INR") -> Dict[str, Any]:
    with _lock:
        w = _wallets.get(farmer_id)
        if not w:
            w = {"farmer_id": farmer_id, "balance": 0.0, "currency": currency, "updated_at": _now_iso()}
            _wallets[farmer_id] = w
    return w

def wallet_balance(farmer_id: str) -> Dict[str, Any]:
    w = ensure_wallet(farmer_id)
    return {"farmer_id": farmer_id, "balance": round(float(w["balance"]), 2), "currency": w["currency"]}

def topup_wallet(farmer_id: str, amount: float, source: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if amount <= 0:
        return {"error": "invalid_amount"}
    with _lock:
        w = ensure_wallet(farmer_id)
        w["balance"] = float(w["balance"]) + float(amount)
        w["updated_at"] = _now_iso()
        # record canonical ledger income entry
        entry = add_ledger_entry(
            farmer_id=farmer_id,
            unit_id=None,
            entry_type="income",
            category="topup",
            amount=round(float(amount),2),
            currency=w.get("currency","INR"),
            date_iso=_now_iso(),
            description=f"Wallet topup from {source}",
            tags=["topup"],
            metadata=metadata or {}
        )
    return {"wallet": w, "ledger_entry": entry}

def withdraw_wallet(farmer_id: str, amount: float, destination: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if amount <= 0:
        return {"error": "invalid_amount"}
    with _lock:
        w = ensure_wallet(farmer_id)
        if float(w["balance"]) < float(amount):
            return {"error": "insufficient_funds"}
        w["balance"] = float(w["balance"]) - float(amount)
        w["updated_at"] = _now_iso()
        entry = add_ledger_entry(
            farmer_id=farmer_id,
            unit_id=None,
            entry_type="expense",
            category="withdrawal",
            amount=round(float(amount),2),
            currency=w.get("currency","INR"),
            date_iso=_now_iso(),
            description=f"Wallet withdrawal to {destination}",
            tags=["withdrawal"],
            metadata=metadata or {}
        )
    return {"wallet": w, "ledger_entry": entry}

# ------------------------------------------------------------------
# Invoice operations (new) - integrated with ledger
# ------------------------------------------------------------------
def create_invoice(farmer_id: str, to_id: str, items: List[Dict[str, Any]], currency: str = "INR", due_date_iso: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    inv_id = _newid("inv")
    total = 0.0
    normalized_items = []
    for it in items:
        it_copy = dict(it)
        if it_copy.get("total_amount") is None:
            qty = float(it_copy.get("qty",1))
            price = float(it_copy.get("unit_price", it_copy.get("unit_price_per_kg_or_unit",0)))
            it_copy["total_amount"] = round(qty * price, 2)
        normalized_items.append(it_copy)
        total += float(it_copy.get("total_amount",0))
    rec = {
        "invoice_id": inv_id,
        "farmer_id": farmer_id,
        "to_id": to_id,
        "items": normalized_items,
        "currency": currency,
        "total_amount": round(total,2),
        "outstanding_amount": round(total,2),
        "status": "issued",  # issued | partially_paid | paid | cancelled
        "created_at": _now_iso(),
        "due_date": due_date_iso,
        "metadata": metadata or {}
    }
    with _lock:
        _invoices[inv_id] = rec
        _invoices_by_farmer.setdefault(farmer_id, []).append(inv_id)
        # record canonical ledger 'income' placeholder for invoice creation (keeps trace)
        add_ledger_entry(
            farmer_id=farmer_id,
            unit_id=None,
            entry_type="income",
            category="invoice_created",
            amount=round(total,2),
            currency=currency,
            date_iso=_now_iso(),
            description=f"Invoice {inv_id} created to {to_id}",
            tags=["invoice","created"],
            metadata={"invoice_id": inv_id}
        )
    return rec

def get_invoice(invoice_id: str) -> Dict[str, Any]:
    return _invoices.get(invoice_id, {})

def list_invoices(farmer_id: Optional[str] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
    with _lock:
        invs = list(_invoices.values())
    if farmer_id:
        ids = _invoices_by_farmer.get(farmer_id, [])[:]
        invs = [ _invoices[i] for i in ids if _invoices.get(i) ]
    if status:
        invs = [i for i in invs if i.get("status") == status]
    return invs

def record_invoice_payment(invoice_id: str, paid_by: str, amount: float, payment_method: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    inv = _invoices.get(invoice_id)
    if not inv:
        return {"error": "invoice_not_found"}
    amt = float(amount)
    pay_id = _newid("pay")
    payment = {
        "payment_id": pay_id,
        "invoice_id": invoice_id,
        "paid_by": paid_by,
        "amount": round(amt,2),
        "payment_method": payment_method or "unknown",
        "metadata": metadata or {},
        "timestamp": _now_iso()
    }
    with _lock:
        _payments[pay_id] = payment
        # update invoice outstanding & status
        inv["outstanding_amount"] = round(max(0.0, float(inv.get("outstanding_amount",0.0)) - amt),2)
        if inv["outstanding_amount"] <= 0:
            inv["status"] = "paid"
            inv["paid_at"] = _now_iso()
        else:
            inv["status"] = "partially_paid"
        _invoices[invoice_id] = inv
        # credit wallet for farmer
        farmer_id = inv.get("farmer_id")
        if farmer_id:
            ensure_wallet(farmer_id)
            _wallets[farmer_id]["balance"] = float(_wallets[farmer_id]["balance"]) + amt
            _wallets[farmer_id]["updated_at"] = _now_iso()
        # ledger entry for payment
        add_ledger_entry(
            farmer_id=farmer_id,
            unit_id=None,
            entry_type="income",
            category="invoice_payment",
            amount=round(amt,2),
            currency=inv.get("currency","INR"),
            date_iso=_now_iso(),
            description=f"Payment {pay_id} for invoice {invoice_id} from {paid_by}",
            tags=["invoice","payment"],
            metadata={"payment_id": pay_id, "invoice_id": invoice_id}
        )
    return {"payment": payment, "invoice": inv}

# ------------------------------------------------------------------
# Payouts (insurance / marketplace) - integrated with ledger & wallet
# ------------------------------------------------------------------
def record_payout(source: str, farmer_id: str, amount: float, reference: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    pid = _newid("payout")
    rec = {
        "payout_id": pid,
        "source": source,
        "farmer_id": farmer_id,
        "amount": round(float(amount),2),
        "reference": reference,
        "metadata": metadata or {},
        "timestamp": _now_iso()
    }
    with _lock:
        _payouts.append(rec)
        # credit wallet
        ensure_wallet(farmer_id)
        _wallets[farmer_id]["balance"] = float(_wallets[farmer_id]["balance"]) + float(amount)
        _wallets[farmer_id]["updated_at"] = _now_iso()
        # ledger entry
        add_ledger_entry(
            farmer_id=farmer_id,
            unit_id=None,
            entry_type="income",
            category=f"payout::{source}",
            amount=round(float(amount),2),
            currency=_wallets[farmer_id].get("currency","INR"),
            date_iso=_now_iso(),
            description=f"Payout from {source}, reference {reference}",
            tags=["payout"],
            metadata={"payout_id": pid, "reference": reference}
        )
    return rec

def list_payouts(limit: int = 200) -> List[Dict[str, Any]]:
    return _payouts[-limit:]

# ------------------------------------------------------------------
# Finance summary (new) - integrates ledger, wallet, invoices, payouts
# ------------------------------------------------------------------
def finance_summary(farmer_id: str) -> Dict[str, Any]:
    w = ensure_wallet(farmer_id)
    invs = list_invoices(farmer_id=farmer_id)
    outstanding = sum(i.get("outstanding_amount",0) for i in invs)
    recent_ledger = [e for e in _ledger if e.get("farmer_id") == farmer_id][-50:]
    recent_payouts = [p for p in _payouts if p.get("farmer_id") == farmer_id][-20:]
    # also include wallet details
    wallet = {"balance": round(float(w["balance"]),2), "currency": w["currency"], "updated_at": w.get("updated_at")}
    return {
        "farmer_id": farmer_id,
        "wallet": wallet,
        "outstanding_invoices": round(float(outstanding),2),
        "invoices_count": len(invs),
        "recent_ledger": recent_ledger,
        "recent_payouts": recent_payouts,
        "timestamp": _now_iso()
    }

# ------------------------------------------------------------------
# Helper reports from original file retained for compatibility
# ------------------------------------------------------------------
def policy_claims_summary_stub(policy_id: str) -> Dict[str, Any]:
    """
    Placeholder that other modules might expect. Kept to avoid breaking references.
    """
    return {"policy_id": policy_id, "total_claims": 0, "total_estimated_loss": 0.0, "total_assessed": 0.0, "total_payouts": 0.0, "claims": []}

def open_claims_for_farmer_stub(farmer_id: str) -> List[Dict[str, Any]]:
    return []

# ------------------------------------------------------------------
# Expose original helper functions unchanged (aliases)
# ------------------------------------------------------------------
# monthly_summary, cashflow_summary, query_ledger, bulk_import_entries, export_ledger_csv, create_subsidy_rule, list_subsidy_rules, apply_subsidy_rule, get_entry, update_entry, delete_entry, top_categories
# are all defined above and serve as the canonical API for other modules.
# ------------------------------------------------------------------

# End of merged finance_service.py
