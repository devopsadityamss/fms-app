# backend/app/services/farmer/seed_service.py
"""
Seed Batch Tracking Service (Feature 325)

Capabilities:
 - Register seed batches (seed batch id, variety, supplier, lot_no, quantity, date_received, expiry_date, seed_treatment)
 - Update / delete / list batches per farmer
 - Record germination test results (date, sample_size, germinated_count, moisture_at_test)
 - Provide germination_rate_estimate (historical average + naive prediction)
 - Alerts for near-expiry or expired batches
 - Query available quantity, allocate quantity (reserve/release), and CSV export
"""

from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, Any, List, Optional
import uuid
import io
import csv
import statistics

_lock = Lock()

_seed_batches: Dict[str, Dict[str, Any]] = {}         # batch_id -> record
_batches_by_farmer: Dict[str, List[str]] = {}         # farmer_id -> [batch_id]
_germ_tests: Dict[str, List[Dict[str, Any]]] = {}     # batch_id -> [tests]
_allocations: Dict[str, List[Dict[str, Any]]] = {}    # batch_id -> allocation history (reserve/release)

LOW_QTY_ALERT_PCT = 10.0  # percent below which to alert for low quantity
NEAR_EXPIRY_DAYS = 30     # days before expiry to mark near-expiry

def _now_iso():
    return datetime.utcnow().isoformat()

def _uid(prefix="sb"):
    return f"{prefix}_{uuid.uuid4()}"

# -----------------------
# Seed batch CRUD
# -----------------------
def create_seed_batch(
    farmer_id: str,
    variety: str,
    supplier: Optional[str],
    lot_no: Optional[str],
    quantity_kg: float,
    date_received_iso: Optional[str] = None,
    expiry_date_iso: Optional[str] = None,
    treatment: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    bid = _uid("seed")
    rec = {
        "batch_id": bid,
        "farmer_id": farmer_id,
        "variety": variety,
        "supplier": supplier or "",
        "lot_no": lot_no or "",
        "quantity_kg": float(quantity_kg),
        "available_kg": float(quantity_kg),
        "date_received": date_received_iso or datetime.utcnow().date().isoformat(),
        "expiry_date": expiry_date_iso,
        "treatment": treatment or "",
        "metadata": metadata or {},
        "created_at": _now_iso(),
        "updated_at": None
    }
    with _lock:
        _seed_batches[bid] = rec
        _batches_by_farmer.setdefault(farmer_id, []).append(bid)
    return rec

def get_seed_batch(batch_id: str) -> Dict[str, Any]:
    with _lock:
        return _seed_batches.get(batch_id, {}).copy()

def list_seed_batches(farmer_id: str, include_empty: bool = False) -> List[Dict[str, Any]]:
    with _lock:
        ids = _batches_by_farmer.get(farmer_id, [])
        out = []
        for i in ids:
            r = _seed_batches.get(i, {}).copy()
            if not include_empty and r.get("available_kg", 0) <= 0:
                continue
            out.append(r)
    return out

def update_seed_batch(batch_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    with _lock:
        rec = _seed_batches.get(batch_id)
        if not rec:
            return {"error": "not_found"}
        # careful numeric casts
        if "quantity_kg" in updates:
            try:
                new_qty = float(updates["quantity_kg"])
                delta = new_qty - rec.get("quantity_kg", 0)
                rec["quantity_kg"] = new_qty
                rec["available_kg"] = max(0.0, rec.get("available_kg", 0.0) + delta)
            except Exception:
                pass
        # expiry and dates
        for k in ("expiry_date", "date_received", "supplier", "lot_no", "treatment", "variety"):
            if k in updates:
                rec[k] = updates[k]
        rec["metadata"].update(updates.get("metadata", {}) or {})
        rec["updated_at"] = _now_iso()
        _seed_batches[batch_id] = rec
        return rec.copy()

def delete_seed_batch(batch_id: str) -> Dict[str, Any]:
    with _lock:
        rec = _seed_batches.pop(batch_id, None)
        if not rec:
            return {"error": "not_found"}
        farmer_id = rec.get("farmer_id")
        if farmer_id and farmer_id in _batches_by_farmer:
            _batches_by_farmer[farmer_id] = [i for i in _batches_by_farmer[farmer_id] if i != batch_id]
        _germ_tests.pop(batch_id, None)
        _allocations.pop(batch_id, None)
    return {"status": "deleted", "batch_id": batch_id}

# -----------------------
# Allocations (reserve / release)
# -----------------------
def allocate_seed(batch_id: str, purpose: str, qty_kg: float, reserved_by: Optional[str] = None) -> Dict[str, Any]:
    """
    Reserve (or reduce) available_kg. qty_kg positive -> reserve (reduce available), negative -> release (increase available).
    """
    with _lock:
        rec = _seed_batches.get(batch_id)
        if not rec:
            return {"error": "batch_not_found"}
        qty = float(qty_kg)
        if qty >= 0:
            if rec.get("available_kg", 0.0) < qty:
                return {"error": "insufficient_quantity", "available_kg": rec.get("available_kg", 0.0)}
            rec["available_kg"] = round(rec.get("available_kg", 0.0) - qty, 3)
            action = "reserved"
        else:
            # release
            rec["available_kg"] = round(rec.get("available_kg", 0.0) + abs(qty), 3)
            action = "released"
        rec["updated_at"] = _now_iso()
        _seed_batches[batch_id] = rec
        alloc = {
            "alloc_id": _uid("alloc"),
            "batch_id": batch_id,
            "purpose": purpose,
            "qty_kg": qty,
            "action": action,
            "reserved_by": reserved_by,
            "timestamp": _now_iso()
        }
        _allocations.setdefault(batch_id, []).append(alloc)
    return {"allocation": alloc, "batch": rec.copy()}

def list_allocations(batch_id: str) -> List[Dict[str, Any]]:
    with _lock:
        return list(_allocations.get(batch_id, []))

# -----------------------
# Germination tests
# -----------------------
def record_germination_test(batch_id: str, sample_size: int, germinated_count: int, date_iso: Optional[str] = None, moisture_pct: Optional[float] = None, notes: Optional[str] = None) -> Dict[str, Any]:
    with _lock:
        if batch_id not in _seed_batches:
            return {"error": "batch_not_found"}
    rec = {
        "test_id": _uid("gt"),
        "batch_id": batch_id,
        "date": date_iso or datetime.utcnow().date().isoformat(),
        "sample_size": int(sample_size),
        "germinated_count": int(germinated_count),
        "germination_pct": round((int(germinated_count) / max(1, int(sample_size))) * 100.0, 2),
        "moisture_pct": float(moisture_pct) if moisture_pct is not None else None,
        "notes": notes or "",
        "recorded_at": _now_iso()
    }
    with _lock:
        _germ_tests.setdefault(batch_id, []).append(rec)
    return rec

def list_germination_tests(batch_id: str) -> List[Dict[str, Any]]:
    with _lock:
        return list(_germ_tests.get(batch_id, []))

def latest_germination_rate(batch_id: str) -> Optional[float]:
    tests = list_germination_tests(batch_id)
    if not tests:
        return None
    latest = sorted(tests, key=lambda x: x.get("recorded_at", ""), reverse=True)[0]
    return latest.get("germination_pct")

def historical_germination_stats(batch_id: str) -> Dict[str, Any]:
    tests = list_germination_tests(batch_id)
    if not tests:
        return {"count": 0, "mean": None, "stdev": None}
    vals = [t["germination_pct"] for t in tests]
    mean = statistics.mean(vals)
    stdev = statistics.pstdev(vals) if len(vals) > 1 else 0.0
    return {"count": len(vals), "mean": round(mean,2), "stdev": round(stdev,2)}

# -----------------------
# Simple prediction stub
# -----------------------
def predict_germination_rate(batch_id: str, use_history: bool = True) -> Dict[str, Any]:
    """
    Naive predictor:
     - if germination tests exist: return historical mean
     - else return a default based on variety metadata or a conservative 70%
    """
    rec = get_seed_batch(batch_id)
    if not rec:
        return {"error": "batch_not_found"}
    if use_history:
        stats = historical_germination_stats(batch_id)
        if stats.get("count",0) > 0:
            return {"batch_id": batch_id, "predicted_germination_pct": stats["mean"], "method": "historical_mean"}
    # fallback default mapping (simple)
    variety_defaults = {
        "wheat": 85.0,
        "rice": 80.0,
        "maize": 88.0,
        "soybean": 82.0
    }
    v = rec.get("variety","").lower()
    pred = variety_defaults.get(v, 70.0)
    return {"batch_id": batch_id, "predicted_germination_pct": pred, "method": "default_variety_or_global"}

# -----------------------
# Alerts & checks
# -----------------------
def list_near_expiry_batches(farmer_id: str, within_days: int = NEAR_EXPIRY_DAYS) -> List[Dict[str, Any]]:
    out = []
    with _lock:
        ids = _batches_by_farmer.get(farmer_id, [])
    now = datetime.utcnow().date()
    for bid in ids:
        b = get_seed_batch(bid)
        exp = b.get("expiry_date")
        if not exp:
            continue
        try:
            ed = datetime.fromisoformat(exp).date()
        except Exception:
            continue
        if 0 <= (ed - now).days <= within_days:
            out.append(b)
    return out

def list_expired_batches(farmer_id: str) -> List[Dict[str, Any]]:
    out = []
    with _lock:
        ids = _batches_by_farmer.get(farmer_id, [])
    now = datetime.utcnow().date()
    for bid in ids:
        b = get_seed_batch(bid)
        exp = b.get("expiry_date")
        if not exp:
            continue
        try:
            ed = datetime.fromisoformat(exp).date()
        except Exception:
            continue
        if ed < now:
            out.append(b)
    return out

# -----------------------
# Inventory exports
# -----------------------
def export_batches_csv(farmer_id: str) -> str:
    batches = list_seed_batches(farmer_id, include_empty=True)
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["batch_id","variety","supplier","lot_no","quantity_kg","available_kg","date_received","expiry_date","treatment","created_at"])
    for b in batches:
        w.writerow([b.get("batch_id"), b.get("variety"), b.get("supplier"), b.get("lot_no"), b.get("quantity_kg"), b.get("available_kg"), b.get("date_received"), b.get("expiry_date"), b.get("treatment"), b.get("created_at")])
    return out.getvalue()
