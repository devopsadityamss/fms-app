# backend/app/services/farmer/purchase_order_service.py

from datetime import datetime
from threading import Lock
from typing import Dict, Any, List, Optional
import uuid

# reuse parts & maintenance helpers
try:
    from app.services.farmer.spare_parts_service import _parts_store, _parts_lock, add_part, list_parts
    from app.services.farmer.predictive_maintenance_service import _maintenance_orders
except Exception:
    # best-effort fallbacks (in case names differ); minimal placeholders
    _parts_store = {}
    _parts_lock = Lock()
    def add_part(part_id, name, unit_price=0.0, quantity=0, min_stock_threshold=1):
        rec = {"part_id": part_id, "name": name, "unit_price": unit_price, "quantity": quantity, "min_stock_threshold": min_stock_threshold, "consumption_history": []}
        with _parts_lock:
            _parts_store[part_id] = rec
        return rec
    def list_parts():
        with _parts_lock:
            return {"count": len(_parts_store), "items": list(_parts_store.values())}
    _maintenance_orders = {}

# In-memory PO store
_po_store: Dict[str, Dict[str, Any]] = {}
_po_lock = Lock()

# Simple parts-vendor registry (in-memory). Each vendor: vendor_id -> {"name", "lead_time_days", "price_map": {part_id: price_per_unit}}
_parts_vendor_store: Dict[str, Dict[str, Any]] = {}
_vendor_lock = Lock()


# ---------------------------
# Vendor CRUD
# ---------------------------
def register_parts_vendor(vendor_id: str, name: str, lead_time_days: int = 7, price_map: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    with _vendor_lock:
        _parts_vendor_store[vendor_id] = {
            "vendor_id": vendor_id,
            "name": name,
            "lead_time_days": int(lead_time_days),
            "price_map": price_map or {},
            "created_at": datetime.utcnow().isoformat()
        }
    return _parts_vendor_store[vendor_id]


def list_parts_vendors() -> Dict[str, Any]:
    with _vendor_lock:
        return {"count": len(_parts_vendor_store), "vendors": list(_parts_vendor_store.values())}


# ---------------------------
# Helpers: vendor suggestion & cost estimate
# ---------------------------
def suggest_vendor_for_part(part_id: str) -> Optional[str]:
    """
    Suggest vendor with lowest unit price for given part_id.
    Returns vendor_id or None if none found.
    """
    best_vid = None
    best_price = None
    with _vendor_lock:
        for vid, v in _parts_vendor_store.items():
            price = v.get("price_map", {}).get(part_id)
            if price is None:
                continue
            if best_price is None or price < best_price:
                best_price = price
                best_vid = vid
    return best_vid


def estimate_cost_for_line(part_id: str, qty: int, vendor_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Return estimated unit_price and total cost. If vendor_id provided and has price_map entry, use that; else try best vendor; else fallback to part.unit_price.
    """
    unit_price = None
    vendor_used = vendor_id
    with _vendor_lock:
        if vendor_id and vendor_id in _parts_vendor_store:
            unit_price = _parts_vendor_store[vendor_id].get("price_map", {}).get(part_id)
    if unit_price is None:
        # try best vendor
        vid = suggest_vendor_for_part(part_id)
        if vid:
            with _vendor_lock:
                unit_price = _parts_vendor_store[vid].get("price_map", {}).get(part_id)
                vendor_used = vid

    if unit_price is None:
        # fallback to stored part price
        with _parts_lock:
            p = _parts_store.get(part_id)
            if p:
                unit_price = float(p.get("unit_price", 0.0))
            else:
                unit_price = 0.0

    total = round(float(unit_price) * int(qty), 2)
    return {"vendor_id": vendor_used, "unit_price": round(float(unit_price), 2), "total_cost": total}


# ---------------------------
# Create PO: from maintenance proposal or ad-hoc
# ---------------------------
def create_po_from_parts_request(
    requested_parts: List[Dict[str, Any]],
    related_maintenance_id: Optional[str] = None,
    preferred_vendor_id: Optional[str] = None,
    created_by: Optional[str] = None
) -> Dict[str, Any]:
    """
    requested_parts: [ { part_id, qty } ... ]
    Returns PO skeleton (not approved)
    """
    po_id = str(uuid.uuid4())
    lines = []
    total_est = 0.0
    for r in requested_parts:
        pid = r.get("part_id")
        qty = int(r.get("qty", 0) or 0)
        est = estimate_cost_for_line(pid, qty, vendor_id=preferred_vendor_id)
        lines.append({
            "part_id": pid,
            "qty_requested": qty,
            "vendor_suggested": est.get("vendor_id"),
            "unit_price_est": est.get("unit_price"),
            "line_total_est": est.get("total_cost")
        })
        total_est += est.get("total_cost", 0.0)

    po = {
        "po_id": po_id,
        "created_at": datetime.utcnow().isoformat(),
        "created_by": created_by,
        "related_maintenance_id": related_maintenance_id,
        "lines": lines,
        "currency": "INR",
        "estimated_total": round(total_est, 2),
        "status": "draft",
        "approved_by": None,
        "approved_at": None,
        "vendor_id": preferred_vendor_id or (lines[0]["vendor_suggested"] if lines else None)
    }
    with _po_lock:
        _po_store[po_id] = po
    return po


def create_po_from_maintenance_orders(maintenance_order_ids: List[str], created_by: Optional[str] = None) -> Dict[str, Any]:
    """
    Aggregate parts_needed across maintenance orders and produce one PO suggestion.
    """
    agg: Dict[str, int] = {}
    for mid in maintenance_order_ids:
        mo = _maintenance_orders.get(mid)
        if not mo:
            continue
        for p in mo.get("parts_needed", []):
            pid = p.get("part_id")
            qty = int(p.get("required_qty", 0) or 0)
            agg[pid] = agg.get(pid, 0) + qty

    requested_parts = [{"part_id": k, "qty": v} for k, v in agg.items()]
    return create_po_from_parts_request(requested_parts, related_maintenance_id=",".join(maintenance_order_ids), created_by=created_by)


# ---------------------------
# PO lifecycle: approve, confirm delivery, cancel
# ---------------------------
def approve_po(po_id: str, approver: str) -> Dict[str, Any]:
    with _po_lock:
        po = _po_store.get(po_id)
        if not po:
            return {"error": "po_not_found"}
        if po.get("status") != "draft":
            return {"error": "po_not_in_draft"}
        po["status"] = "approved"
        po["approved_by"] = approver
        po["approved_at"] = datetime.utcnow().isoformat()
        # decide vendor if not set: take majority vendor suggestion or first available
        if not po.get("vendor_id"):
            vendor_counts = {}
            for l in po["lines"]:
                v = l.get("vendor_suggested")
                if v:
                    vendor_counts[v] = vendor_counts.get(v, 0) + 1
            if vendor_counts:
                chosen = sorted(vendor_counts.items(), key=lambda x: x[1], reverse=True)[0][0]
                po["vendor_id"] = chosen
    return po


def confirm_po_delivery(po_id: str, delivered_lines: Optional[List[Dict[str, Any]]] = None, received_by: Optional[str] = None) -> Dict[str, Any]:
    """
    Mark PO as delivered; update part stocks.
    delivered_lines: optional list of {part_id, qty_received, unit_price_paid}
    """
    with _po_lock:
        po = _po_store.get(po_id)
        if not po:
            return {"error": "po_not_found"}
        if po.get("status") not in ("approved", "partial"):
            return {"error": "po_not_approved_or_partial"}

    # apply deliveries
    delivered_map = {}
    if delivered_lines:
        for d in delivered_lines:
            delivered_map[d["part_id"]] = {"qty_received": int(d.get("qty_received", 0)), "unit_price_paid": float(d.get("unit_price_paid", 0.0))}
    # default: assume full delivery of requested qty
    with _parts_lock:
        for line in po["lines"]:
            pid = line["part_id"]
            requested = int(line.get("qty_requested", 0))
            received = delivered_map.get(pid, {}).get("qty_received", requested)
            unit_price_paid = delivered_map.get(pid, {}).get("unit_price_paid", line.get("unit_price_est", 0.0))
            # update or create part record
            part = _parts_store.get(pid)
            if not part:
                part = add_part(pid, name=pid, unit_price=unit_price_paid, quantity=0, min_stock_threshold=1)
            # increment stock
            part["quantity"] = int(part.get("quantity", 0)) + int(received)
            # set unit_price to paid price (simple)
            part["unit_price"] = unit_price_paid
            # optionally log consumption history not done here (consumption logged when used)
    # finalize PO
    with _po_lock:
        po["status"] = "delivered"
        po["delivered_at"] = datetime.utcnow().isoformat()
        po["received_by"] = received_by
        po["delivered_lines"] = [{"part_id": pid, "qty_received": delivered_map.get(pid, {}).get("qty_received", l["qty_requested"]), "unit_price_paid": delivered_map.get(pid, {}).get("unit_price_paid", l["unit_price_est"])} for pid, l in ((ln["part_id"], ln) for ln in po["lines"])]
    return po


def cancel_po(po_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
    with _po_lock:
        po = _po_store.get(po_id)
        if not po:
            return {"error": "po_not_found"}
        po["status"] = "cancelled"
        po["cancelled_at"] = datetime.utcnow().isoformat()
        if reason:
            po["cancel_reason"] = reason
    return po


def list_pos(status: Optional[str] = None) -> Dict[str, Any]:
    with _po_lock:
        items = list(_po_store.values())
    if status:
        items = [i for i in items if i.get("status") == status]
    return {"count": len(items), "pos": items}
