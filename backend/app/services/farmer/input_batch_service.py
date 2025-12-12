# backend/app/services/farmer/input_batch_service.py
"""
Input Batch Tracking Service (Feature 327)
-----------------------------------------

Tracks all agricultural inputs:
  - Fertilizers
  - Pesticides / chemicals
  - Soil amendments
  - Growth regulators
  - Foliar sprays

Features:
 - Register input batch
 - Update details
 - Track inventory quantity (kg/L/units)
 - Record usage logs (per unit → quantity consumed)
 - Automatic stock deduction
 - Batch expiry detection
 - Batch health status (expired / low-stock)
 - Full summaries
"""

from datetime import datetime, date
from typing import Dict, Any, Optional, List
import uuid
from threading import Lock

_lock = Lock()

_batches: Dict[str, Dict[str, Any]] = {}              # batch_id → record
_batches_by_farmer: Dict[str, List[str]] = {}         # farmer_id → [batch_ids]

_usage_logs: Dict[str, Dict[str, Any]] = {}           # log_id → record
_usage_by_batch: Dict[str, List[str]] = {}            # batch_id → [log_ids]


def _now():
    return datetime.utcnow().isoformat()


def _uid(prefix="inp"):
    return f"{prefix}_{uuid.uuid4()}"


# -------------------------------------------------------
# INPUT BATCH CRUD
# -------------------------------------------------------
def add_input_batch(
    farmer_id: str,
    name: str,
    input_type: str,                # fertilizer / pesticide / herbicide / fungicide / micronutrient / etc.
    quantity_total: float,
    unit: str,                      # kg, L, ml, g, units
    brand: Optional[str] = None,
    composition: Optional[str] = None,
    expiry_date: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    bid = _uid("batch")

    rec = {
        "batch_id": bid,
        "farmer_id": farmer_id,
        "name": name,
        "input_type": input_type,
        "brand": brand or "",
        "composition": composition or "",
        "quantity_total": float(quantity_total),
        "quantity_available": float(quantity_total),
        "unit": unit,
        "expiry_date": expiry_date,
        "metadata": metadata or {},
        "created_at": _now(),
        "updated_at": None
    }

    with _lock:
        _batches[bid] = rec
        _batches_by_farmer.setdefault(farmer_id, []).append(bid)

    return rec


def get_input_batch(batch_id: str) -> Dict[str, Any]:
    with _lock:
        b = _batches.get(batch_id)
        return b.copy() if b else {}


def list_input_batches(farmer_id: str) -> List[Dict[str, Any]]:
    with _lock:
        ids = _batches_by_farmer.get(farmer_id, [])
        return [_batches[i].copy() for i in ids]


def update_input_batch(batch_id: str, updates: Dict[str, Any]):
    with _lock:
        b = _batches.get(batch_id)
        if not b:
            return {"error": "not_found"}

        # sanitize numeric fields
        if "quantity_total" in updates:
            try:
                updates["quantity_total"] = float(updates["quantity_total"])
            except:
                pass

        b.update(updates)
        b["updated_at"] = _now()
        _batches[batch_id] = b
        return b.copy()


def delete_input_batch(batch_id: str):
    with _lock:
        b = _batches.pop(batch_id, None)
        if not b:
            return {"error": "not_found"}

        farmer_id = b.get("farmer_id")
        if farmer_id and farmer_id in _batches_by_farmer:
            _batches_by_farmer[farmer_id] = [i for i in _batches_by_farmer[farmer_id] if i != batch_id]

        _usage_by_batch.pop(batch_id, None)
        return {"status": "deleted", "batch_id": batch_id}


# -------------------------------------------------------
# USAGE LOGGING + STOCK DEDUCTION
# -------------------------------------------------------
def record_usage(
    batch_id: str,
    unit_id: str,
    quantity_used: float,
    notes: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    with _lock:
        b = _batches.get(batch_id)
        if not b:
            return {"error": "batch_not_found"}

        qty = float(quantity_used)
        if qty > b["quantity_available"]:
            return {"error": "insufficient_stock", "available": b["quantity_available"]}

        log_id = _uid("use")
        rec = {
            "usage_id": log_id,
            "batch_id": batch_id,
            "unit_id": unit_id,
            "quantity_used": qty,
            "notes": notes or "",
            "metadata": metadata or {},
            "timestamp": _now()
        }

        # Deduct stock
        b["quantity_available"] -= qty
        b["updated_at"] = _now()

        _usage_logs[log_id] = rec
        _usage_by_batch.setdefault(batch_id, []).append(log_id)

        return rec


def list_usage_logs(batch_id: str) -> List[Dict[str, Any]]:
    ids = _usage_by_batch.get(batch_id, [])
    return [_usage_logs[i] for i in ids]


# -------------------------------------------------------
# EXPIRY / HEALTH ANALYSIS
# -------------------------------------------------------
def check_batch_status(batch_id: str) -> Dict[str, Any]:
    b = get_input_batch(batch_id)
    if not b:
        return {"error": "not_found"}

    status = "ok"
    warnings = []

    # expiry check
    exp = b.get("expiry_date")
    if exp:
        try:
            exp_dt = date.fromisoformat(exp)
            if exp_dt < date.today():
                status = "expired"
                warnings.append("batch_expired")
        except Exception:
            warnings.append("invalid_expiry_format")

    # low stock
    if b.get("quantity_available", 0) < (0.1 * b.get("quantity_total", 1)):
        warnings.append("low_stock")

    return {
        "batch_id": batch_id,
        "status": status,
        "quantity_available": b.get("quantity_available"),
        "warnings": warnings,
        "timestamp": _now()
    }


def batch_summary(batch_id: str) -> Dict[str, Any]:
    b = get_input_batch(batch_id)
    if not b:
        return {"error": "not_found"}

    return {
        "batch": b,
        "usage_logs": list_usage_logs(batch_id),
        "health": check_batch_status(batch_id),
        "timestamp": _now()
    }


def farmer_inventory_overview(farmer_id: str):
    batches = list_input_batches(farmer_id)
    overview = []

    for b in batches:
        overview.append({
            "batch": b,
            "health": check_batch_status(b["batch_id"]),
        })

    return {
        "farmer_id": farmer_id,
        "count": len(batches),
        "inventory": overview,
        "generated_at": _now()
    }
# ======================================================================
# INPUT INTELLIGENCE ENGINE
# Features:
#   328 - Expiry Monitoring
#   329 - Contamination Alert Detection
#   330 - Input Usage Optimizer
# ======================================================================

from datetime import date  # ensure date is available (your file already imports date)

# Mock interactions / unsafe combinations
UNSAFE_COMBINATIONS = [
    ("urea", "DAP"),
    ("glyphosate", "2,4-D"),
    ("copper_oxychloride", "sulfur"),
]

def _normalize(s: str) -> str:
    return str(s).strip().lower().replace(" ", "_")


# -------------------------------------------------------
# 328 - EXPIRED / NEAR-EXPIRY BATCH SCANNER
# -------------------------------------------------------
def scan_expired_batches(farmer_id: str, days_before: int = 15):
    """
    Scans farmer inventory and returns:
      - expired batches
      - near-expiry batches
    """
    today = date.today()
    batches = list_input_batches(farmer_id)

    expired = []
    near_exp = []

    for b in batches:
        exp = b.get("expiry_date")
        if not exp:
            continue

        try:
            exp_dt = date.fromisoformat(exp)
        except:
            continue

        if exp_dt < today:
            expired.append(b)
        elif (exp_dt - today).days <= days_before:
            near_exp.append({
                **b,
                "days_remaining": (exp_dt - today).days
            })

    return {
        "farmer_id": farmer_id,
        "expired_batches": expired,
        "near_expiry_batches": near_exp,
        "generated_at": _now()
    }


# -------------------------------------------------------
# 329 - CONTAMINATION / UNSAFE MIX ALERT ENGINE
# -------------------------------------------------------
def detect_input_contamination_risk(batch_id: str):
    """
    Simple heuristic:
      - Check if composition contains words known to react negatively.
      - Use UNSAFE_COMBINATIONS for mock detection.
    """
    b = get_input_batch(batch_id)
    if not b:
        return {"error": "batch_not_found"}

    name = _normalize(b.get("name"))
    comp = _normalize(b.get("composition"))

    risky_pairs = []
    for a, b2 in UNSAFE_COMBINATIONS:
        if a in name or a in comp:
            if b2 in name or b2 in comp:
                risky_pairs.append((a, b2))

    return {
        "batch_id": batch_id,
        "risk": "high" if risky_pairs else "low",
        "conflicts": risky_pairs,
        "timestamp": _now()
    }


def farmer_contamination_overview(farmer_id: str):
    batches = list_input_batches(farmer_id)
    out = []

    for b in batches:
        risk = detect_input_contamination_risk(b["batch_id"])
        if risk.get("risk") == "high":
            out.append(risk)

    return {
        "farmer_id": farmer_id,
        "risks": out,
        "count": len(out),
        "generated_at": _now()
    }


# -------------------------------------------------------
# 330 - INPUT USAGE OPTIMIZER
# -------------------------------------------------------
def recommend_best_batch(
    farmer_id: str,
    input_type: str,
    priority: str = "expiry"  # expiry | stock | oldest | best_quality
):
    """
    Suggests the best batch to use next.
    Strategies:
      - expiry: use the one closest to expiry
      - stock: use the one with the largest quantity_available
      - oldest: FIFO (oldest created_at)
      - best_quality: mock heuristic using composition keyword 'premium'
    """

    batches = [b for b in list_input_batches(farmer_id) if _normalize(b["input_type"]) == _normalize(input_type)]
    if not batches:
        return {"error": "no_batches"}

    today = date.today()

    if priority == "expiry":
        candidates = []
        for b in batches:
            exp = b.get("expiry_date")
            if not exp:
                continue
            try:
                dt = date.fromisoformat(exp)
                days_left = (dt - today).days
                candidates.append((days_left, b))
            except:
                continue
        if candidates:
            candidates.sort(key=lambda x: x[0])
            return {"strategy": "expiry", "recommended": candidates[0][1], "timestamp": _now()}

    if priority == "stock":
        batches.sort(key=lambda b: b.get("quantity_available", 0), reverse=True)
        return {"strategy": "stock", "recommended": batches[0], "timestamp": _now()}

    if priority == "oldest":
        batches.sort(key=lambda b: b.get("created_at"))
        return {"strategy": "oldest", "recommended": batches[0], "timestamp": _now()}

    if priority == "best_quality":
        premium = [b for b in batches if "premium" in _normalize(b.get("composition", ""))]
        if premium:
            return {"strategy": "best_quality", "recommended": premium[0], "timestamp": _now()}

    # fallback
    return {"strategy": "fallback", "recommended": batches[0], "timestamp": _now()}


# -------------------------------------------------------
# INTELLIGENCE SUMMARY
# -------------------------------------------------------
def input_intelligence_summary(farmer_id: str):
    return {
        "farmer_id": farmer_id,
        "expiry_scan": scan_expired_batches(farmer_id),
        "contamination": farmer_contamination_overview(farmer_id),
        "timestamp": _now()
    }
