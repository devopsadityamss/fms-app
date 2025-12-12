# backend/app/services/farmer/spare_parts_service.py

"""
Spare Parts Inventory (Feature #211)
In-memory spare parts catalog and assignment to equipment.
"""

from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, Any, List, Optional
import uuid
import math

_parts_store: Dict[str, Dict[str, Any]] = {}
_assignment_store: Dict[str, List[Dict[str, Any]]] = {}  # equipment_id -> list of part assignments
_parts_lock = Lock()




def _now_iso():
    return datetime.utcnow().isoformat()


def add_part(
    name: str,
    sku: str = "",
    manufacturer: str = "",
    unit_price: float = 0.0,
    quantity: int = 0,
    min_stock_threshold: int = 1,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    part_id = str(uuid.uuid4())
    rec = {
        "id": part_id,
        "name": name,
        "sku": sku,
        "manufacturer": manufacturer,
        "unit_price": unit_price,
        "quantity": int(quantity),
        "min_stock_threshold": int(min_stock_threshold),
        "metadata": metadata or {},
        "created_at": _now_iso(),
    }
    with _parts_lock:
        _parts_store[part_id] = rec
    return rec


def update_part(
    part_id: str,
    name: Optional[str] = None,
    sku: Optional[str] = None,
    manufacturer: Optional[str] = None,
    unit_price: Optional[float] = None,
    quantity: Optional[int] = None,
    min_stock_threshold: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    with _parts_lock:
        rec = _parts_store.get(part_id)
        if not rec:
            return None
        if name is not None:
            rec["name"] = name
        if sku is not None:
            rec["sku"] = sku
        if manufacturer is not None:
            rec["manufacturer"] = manufacturer
        if unit_price is not None:
            rec["unit_price"] = float(unit_price)
        if quantity is not None:
            rec["quantity"] = int(quantity)
        if min_stock_threshold is not None:
            rec["min_stock_threshold"] = int(min_stock_threshold)
        if metadata is not None:
            rec["metadata"].update(metadata)
        rec["updated_at"] = _now_iso()
    return rec


def delete_part(part_id: str) -> bool:
    with _parts_lock:
        if part_id in _parts_store:
            del _parts_store[part_id]
            # remove assignments referencing this part
            for eq_id, assigns in list(_assignment_store.items()):
                _assignment_store[eq_id] = [a for a in assigns if a["part_id"] != part_id]
            return True
    return False


def get_part(part_id: str) -> Optional[Dict[str, Any]]:
    with _parts_lock:
        return _parts_store.get(part_id)


def list_parts() -> Dict[str, Any]:
    with _parts_lock:
        items = list(_parts_store.values())
    return {"count": len(items), "items": items}


def assign_part_to_equipment(part_id: str, equipment_id: str, quantity: int = 1) -> Optional[Dict[str, Any]]:
    """
    Assigns a quantity of a part to an equipment (reservation / installed).
    Does NOT auto-decrement stock — consume_part should be used for actual usage.
    """
    with _parts_lock:
        part = _parts_store.get(part_id)
        if not part:
            return None
        assign = {
            "part_id": part_id,
            "equipment_id": equipment_id,
            "quantity": int(quantity),
            "assigned_at": _now_iso(),
        }
        if equipment_id not in _assignment_store:
            _assignment_store[equipment_id] = []
        _assignment_store[equipment_id].append(assign)
    return assign


def get_parts_for_equipment(equipment_id: str) -> Dict[str, Any]:
    with _parts_lock:
        assigns = _assignment_store.get(equipment_id, [])
        # enrich with part details
        enriched = []
        for a in assigns:
            p = _parts_store.get(a["part_id"])
            enriched.append({"assignment": a, "part": p})
    return {"equipment_id": equipment_id, "count": len(enriched), "items": enriched}


def consume_part(part_id: str, quantity: int = 1) -> Optional[Dict[str, Any]]:
    """
    Decrease stock for a part. Returns updated part record.
    """
    with _parts_lock:
        part = _parts_store.get(part_id)
        if not part:
            return None
        if quantity <= 0:
            return {"error": "invalid_quantity"}
        if part["quantity"] < quantity:
            return {"error": "insufficient_stock", "available": part["quantity"]}
        part["quantity"] -= int(quantity)
        part.setdefault("consumption_history", []).append({
            "quantity": int(quantity),
            "consumed_at": _now_iso()
        })
        part["updated_at"] = _now_iso()
    return part


def check_low_stock(threshold: int = None) -> Dict[str, Any]:
    """
    Return parts below `threshold` (or their min_stock_threshold if threshold not provided).
    """
    low = []
    with _parts_lock:
        for p in _parts_store.values():
            th = threshold if threshold is not None else p.get("min_stock_threshold", 1)
            if p.get("quantity", 0) <= th:
                low.append(p)
    return {"count": len(low), "items": low}

def log_part_usage(
    part_id: str,
    equipment_id: str,
    quantity: int,
    reason: str = "maintenance",
    worker_id: str = None,
) -> Optional[Dict[str, Any]]:
    """
    Logs usage of spare parts for maintenance/repair/etc.
    Integrates with consume_part to reduce stock.
    """

    # First, consume stock
    consumed = consume_part(part_id, quantity)
    if consumed is None or "error" in consumed:
        return consumed  # propagate error

    usage_entry = {
        "part_id": part_id,
        "equipment_id": equipment_id,
        "quantity": quantity,
        "reason": reason,
        "worker_id": worker_id,
        "used_at": _now_iso(),
    }

    with _parts_lock:
        part = _parts_store.get(part_id)
        if "usage_logs" not in part:
            part["usage_logs"] = []
        part["usage_logs"].append(usage_entry)

    return usage_entry


def list_part_usage(part_id: str) -> Optional[Dict[str, Any]]:
    """
    Returns usage logs for a specific part.
    """
    with _parts_lock:
        part = _parts_store.get(part_id)
        if not part:
            return None
        logs = part.get("usage_logs", [])
    return {"part_id": part_id, "count": len(logs), "usage_logs": logs}


def list_all_usage() -> Dict[str, Any]:
    """
    Lists usage logs across all parts.
    Helpful for analytics and stock management.
    """
    logs = []
    with _parts_lock:
        for p in _parts_store.values():
            for log in p.get("usage_logs", []):
                logs.append(log)
    return {"count": len(logs), "usage_logs": logs}


def generate_restock_recommendation(part_id: str) -> Optional[Dict[str, Any]]:
    """
    Simple restocking intelligence:
    Uses:
    - current stock
    - minimum threshold
    - usage rate (if enough history)
    """

    with _parts_lock:
        part = _parts_store.get(part_id)
        if not part:
            return None

        quantity = part.get("quantity", 0)
        threshold = part.get("min_stock_threshold", 1)
        usage_logs = part.get("usage_logs", [])

    # Compute monthly usage rate (mock)
    usage_rate = 0
    if usage_logs:
        usage_rate = sum(l["quantity"] for l in usage_logs)

    if quantity <= threshold:
        need = (usage_rate * 2) or (threshold * 2)
        msg = "Stock is critically low. Restock immediately."
    elif quantity <= threshold * 2:
        need = threshold
        msg = "Stock is low. Consider restocking soon."
    else:
        need = 0
        msg = "Stock is sufficient for now."

    return {
        "part_id": part_id,
        "current_quantity": quantity,
        "recommended_restock_qty": need,
        "usage_rate_estimate": usage_rate,
        "message": msg,
        "calculated_at": _now_iso(),
    }


# -------------------------
# In-memory parts store
# -------------------------
# Example part record structure:
# {
#   "part_id": "p1",
#   "name": "Oil Filter",
#   "unit_price": 250.0,
#   "quantity": 10,
#   "min_stock_threshold": 3,
#   "consumption_history": [
#       {"equipment_id": "e1", "quantity": 1, "used_at": "2025-12-01T10:00:00"},
#       ...
#   ]
# }


# -------------------------
# Helper: add / list parts (lightweight; keep if you don't already have these)
# -------------------------
def add_part(part_id: str, name: str, unit_price: float = 0.0, quantity: int = 0, min_stock_threshold: int = 2) -> Dict[str, Any]:
    rec = {
        "part_id": part_id,
        "name": name,
        "unit_price": unit_price,
        "quantity": quantity,
        "min_stock_threshold": min_stock_threshold,
        "consumption_history": []
    }
    with _parts_lock:
        _parts_store[part_id] = rec
    return rec


def list_parts() -> Dict[str, Any]:
    with _parts_lock:
        items = list(_parts_store.values())
    return {"count": len(items), "items": items}


def record_part_consumption(part_id: str, equipment_id: str, qty: float, used_at: Optional[str] = None) -> Dict[str, Any]:
    if used_at is None:
        used_at = datetime.utcnow().isoformat()
    entry = {"equipment_id": equipment_id, "quantity": qty, "used_at": used_at}
    with _parts_lock:
        part = _parts_store.get(part_id)
        if not part:
            # create a minimal record
            part = add_part(part_id, name=part_id, unit_price=0.0, quantity=0, min_stock_threshold=1)
        part["consumption_history"].append(entry)
        # update quantity (assume consumption reduces stock)
        try:
            part["quantity"] = max(0, int(part.get("quantity", 0) - qty))
        except:
            part["quantity"] = 0
    return entry

# -------------------------
# Forecasting logic
# -------------------------
def _get_recent_consumption(part_rec: Dict[str, Any], lookback_days: int = 180) -> List[Dict[str, Any]]:
    """
    Returns consumption entries within lookback_days (default 180 days).
    """
    cutoff = datetime.utcnow() - timedelta(days=lookback_days)
    recent = []
    for e in part_rec.get("consumption_history", []):
        try:
            t = datetime.fromisoformat(e.get("used_at"))
        except Exception:
            # if malformed, include as recent to be conservative
            recent.append(e)
            continue
        if t >= cutoff:
            recent.append(e)
    return recent


def _monthly_average_from_history(part_rec: Dict[str, Any], lookback_days: int = 180) -> float:
    """
    Compute average monthly consumption (units/month) from recent history.
    Uses lookback_days window; converts to months = lookback_days/30.
    """
    recent = _get_recent_consumption(part_rec, lookback_days=lookback_days)
    total_qty = 0.0
    for r in recent:
        try:
            total_qty += float(r.get("quantity", 0))
        except:
            pass
    months = max(1.0, lookback_days / 30.0)
    avg_per_month = total_qty / months
    return avg_per_month


def forecast_parts_consumption(
    equipment_ids: Optional[List[str]] = None,
    horizon_months: int = 6,
    lookback_days: int = 180,
    safety_buffer_pct: float = 0.20
) -> Dict[str, Any]:
    """
    Fleet-level forecast of parts consumption and reorder suggestions.

    - equipment_ids: if provided, limits forecast to parts consumed by these equipment only
    - horizon_months: months to forecast ahead
    - lookback_days: data window to compute monthly averages
    - safety_buffer_pct: additional percentage to add as buffer for reorder qty

    Returns:
      {
        "horizon_months": int,
        "generated_at": iso,
        "parts": [
          {
            "part_id": "...",
            "name": "...",
            "current_stock": N,
            "avg_per_month": x,
            "forecast_consumption": y,
            "safety_buffer_pct": 0.2,
            "required_reorder_qty": z,
            "days_to_stockout_estimate": 45,
            "min_stock_threshold": M
          },
          ...
        ],
        "summary": { "total_reorder_cost_estimate": 1234.5, "parts_to_reorder_count": 4 }
      }
    """
    results = []
    total_reorder_cost = 0.0
    parts_to_reorder = 0

    with _parts_lock:
        part_items = list(_parts_store.values())

    for p in part_items:
        # Filter by equipment usage if equipment_ids provided
        recent = _get_recent_consumption(p, lookback_days=lookback_days)
        if equipment_ids:
            recent = [r for r in recent if r.get("equipment_id") in set(equipment_ids)]
            # skip if no consumption by given equipment set
            if not recent:
                continue

        avg_per_month = _monthly_average_from_history(p, lookback_days=lookback_days)
        forecast_consumption = round(avg_per_month * max(1, horizon_months), 2)

        # safety buffer quantity
        buffer_qty = math.ceil(forecast_consumption * safety_buffer_pct)

        current_stock = int(p.get("quantity", 0))
        min_threshold = int(p.get("min_stock_threshold", 1))
        # required reorder = forecast + buffer - current_stock (if positive)
        required_qty = max(0, int(math.ceil(forecast_consumption + buffer_qty - current_stock)))

        # estimate stockout days (if avg_per_month > 0)
        days_to_stockout = None
        if avg_per_month > 0:
            # months until stockout = current_stock / avg_per_month
            months_until = current_stock / avg_per_month if avg_per_month > 0 else None
            if months_until is not None:
                days_to_stockout = int(months_until * 30)

        part_reorder_cost = 0.0
        try:
            part_reorder_cost = required_qty * float(p.get("unit_price", 0.0))
        except:
            part_reorder_cost = 0.0

        if required_qty > 0 or current_stock <= min_threshold:
            parts_to_reorder += 1
            total_reorder_cost += part_reorder_cost

        results.append({
            "part_id": p.get("part_id"),
            "name": p.get("name"),
            "current_stock": current_stock,
            "min_stock_threshold": min_threshold,
            "avg_per_month": round(avg_per_month, 2),
            "forecast_consumption": forecast_consumption,
            "safety_buffer_qty": buffer_qty,
            "required_reorder_qty": required_qty,
            "estimated_reorder_cost": round(part_reorder_cost, 2),
            "days_to_stockout_estimate": days_to_stockout
        })

    return {
        "horizon_months": horizon_months,
        "count": len(results),
        "parts": sorted(results, key=lambda x: x["required_reorder_qty"], reverse=True),
        "summary": {
            "parts_to_reorder_count": parts_to_reorder,
            "total_reorder_cost_estimate": round(total_reorder_cost, 2)
        },
        "generated_at": datetime.utcnow().isoformat()
    }


def forecast_parts_for_equipment(
    equipment_id: str,
    horizon_months: int = 6,
    lookback_days: int = 180,
    safety_buffer_pct: float = 0.20
) -> Dict[str, Any]:
    """
    Forecast parts consumption specific to an equipment.

    Returns:
      {
         "equipment_id": "...",
         "parts": [ { part_id, name, avg_per_month, forecast_consumption, required_reorder_qty, days_to_stockout_estimate }, ... ],
         "summary": ...
      }
    """
    results = []
    total_cost = 0.0
    parts_to_reorder = 0

    with _parts_lock:
        part_items = list(_parts_store.values())

    for p in part_items:
        # filter consumption history by equipment_id
        recent = [r for r in p.get("consumption_history", []) if r.get("equipment_id") == equipment_id]
        if not recent:
            continue

        # compute avg/month using only recent entries for this equipment
        # create a temporary part record shaped like p but with filtered consumption_history
        temp = p.copy()
        temp["consumption_history"] = recent
        avg_per_month = _monthly_average_from_history(temp, lookback_days=lookback_days)
        forecast_consumption = round(avg_per_month * max(1, horizon_months), 2)
        buffer_qty = math.ceil(forecast_consumption * safety_buffer_pct)
        current_stock = int(p.get("quantity", 0))
        required_qty = max(0, int(math.ceil(forecast_consumption + buffer_qty - current_stock)))
        part_cost = required_qty * float(p.get("unit_price", 0.0) or 0.0)
        if required_qty > 0:
            parts_to_reorder += 1
            total_cost += part_cost

        # days to stockout based on equipment-specific avg
        days_to_stockout = None
        if avg_per_month > 0:
            months_until = current_stock / avg_per_month if avg_per_month > 0 else None
            if months_until is not None:
                days_to_stockout = int(months_until * 30)

        results.append({
            "part_id": p.get("part_id"),
            "name": p.get("name"),
            "current_stock": current_stock,
            "avg_per_month_for_equipment": round(avg_per_month, 2),
            "forecast_consumption": forecast_consumption,
            "safety_buffer_qty": buffer_qty,
            "required_reorder_qty": required_qty,
            "estimated_reorder_cost": round(part_cost, 2),
            "days_to_stockout_estimate": days_to_stockout
        })

    return {
        "equipment_id": equipment_id,
        "horizon_months": horizon_months,
        "count": len(results),
        "parts": sorted(results, key=lambda x: x["required_reorder_qty"], reverse=True),
        "summary": {
            "parts_to_reorder_count": parts_to_reorder,
            "total_reorder_cost_estimate": round(total_cost, 2)
        },
        "generated_at": datetime.utcnow().isoformat()
    }


def list_low_stock_parts(within_months: int = 6, lookback_days: int = 180, safety_buffer_pct: float = 0.20) -> Dict[str, Any]:
    """
    Convenience: returns parts that are predicted to be below min threshold or require reorder within `within_months`.
    """
    forecast = forecast_parts_consumption(horizon_months=within_months, lookback_days=lookback_days, safety_buffer_pct=safety_buffer_pct)
    low = []
    for p in forecast.get("parts", []):
        if p["required_reorder_qty"] > 0 or p["current_stock"] <= p["min_stock_threshold"]:
            low.append(p)
    return {
        "within_months": within_months,
        "count": len(low),
        "low_stock_parts": low,
        "generated_at": datetime.utcnow().isoformat()
    }
