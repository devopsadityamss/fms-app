# backend/app/services/farmer/input_shortage_service.py

from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, Any, List, Optional

# reuse input forecasting
from app.services.farmer.input_forecasting_service import forecast_inputs_for_unit

# optional: use purchase_order_service if present to generate POs
try:
    from app.services.farmer.purchase_order_service import create_po_from_parts_request
except Exception:
    create_po_from_parts_request = None

# In-memory farmer input inventory (seed/fertilizer/pesticide)
# key -> {"item_id": "seed_wheat", "name": "Wheat Seed", "quantity": <kg or liters>, "unit": "kg" or "liter", "min_threshold": <units>}
_input_inventory_store: Dict[str, Dict[str, Any]] = {}
_inventory_lock = Lock()

# In-memory shortage alerts
_shortage_alerts: Dict[str, Dict[str, Any]] = {}
_alerts_lock = Lock()


def add_inventory_item(item_id: str, name: str, quantity: float, unit: str = "kg", min_threshold: Optional[float] = None) -> Dict[str, Any]:
    rec = {
        "item_id": item_id,
        "name": name,
        "quantity": float(quantity),
        "unit": unit,
        "min_threshold": float(min_threshold) if min_threshold is not None else 0.0,
        "updated_at": datetime.utcnow().isoformat()
    }
    with _inventory_lock:
        _input_inventory_store[item_id] = rec
    return rec


def update_inventory_quantity(item_id: str, delta: float) -> Optional[Dict[str, Any]]:
    with _inventory_lock:
        rec = _input_inventory_store.get(item_id)
        if not rec:
            return None
        rec["quantity"] = float(rec.get("quantity", 0.0)) + float(delta)
        rec["updated_at"] = datetime.utcnow().isoformat()
        _input_inventory_store[item_id] = rec
        return rec


def get_inventory(item_id: Optional[str] = None) -> Dict[str, Any]:
    with _inventory_lock:
        if item_id:
            rec = _input_inventory_store.get(item_id)
            return rec or {}
        else:
            return {"count": len(_input_inventory_store), "items": list(_input_inventory_store.values())}


def _record_shortage_alert(alert: Dict[str, Any]) -> Dict[str, Any]:
    aid = f"shortage__{alert.get('unit_id','unknown')}__{alert.get('item_id')}__{int(datetime.utcnow().timestamp())}"
    alert["alert_id"] = aid
    alert["created_at"] = datetime.utcnow().isoformat()
    alert["status"] = "open"
    with _alerts_lock:
        _shortage_alerts[aid] = alert
    return alert


def list_shortage_alerts(unit_id: Optional[str] = None, status: Optional[str] = None) -> Dict[str, Any]:
    with _alerts_lock:
        items = list(_shortage_alerts.values())
    if unit_id:
        items = [i for i in items if i.get("unit_id") == unit_id]
    if status:
        items = [i for i in items if i.get("status") == status]
    return {"count": len(items), "alerts": items}


def acknowledge_shortage(alert_id: str, acknowledged_by: Optional[str] = None) -> Dict[str, Any]:
    with _alerts_lock:
        rec = _shortage_alerts.get(alert_id)
        if not rec:
            return {"error": "alert_not_found"}
        rec["status"] = "acknowledged"
        rec["acknowledged_by"] = acknowledged_by
        rec["acknowledged_at"] = datetime.utcnow().isoformat()
        _shortage_alerts[alert_id] = rec
    return rec


# -------------------------
# Core check: single unit
# -------------------------
def check_shortages_for_unit(
    unit_id: str,
    lookahead_days: int = 30,
    safety_margin_pct: float = 0.10  # keep 10% extra buffer
) -> Dict[str, Any]:
    """
    For the given production unit:
      - call forecast_inputs_for_unit to get total inputs needed for the cycle
      - scale down to lookahead_days proportionally (simple heuristic)
      - compare with current inventory and create shortage alerts / procurement suggestions
    """

    forecast = forecast_inputs_for_unit(unit_id)
    if forecast.get("status") == "unit_not_found":
        return {"status": "unit_not_found", "unit_id": unit_id}

    total_inputs = forecast.get("total_inputs", {})
    # determine proportion: if full cycle duration not known, assume lookahead needs 25% by default
    # Better: if stage durations available, compute fraction. For now use simple fixed fraction of cycle:
    fraction = min(1.0, max(0.1, lookahead_days / 90.0))  # assume 90-day typical season
    required = {}

    # Seeds
    seed_req_total = float(total_inputs.get("seed_kg", 0) or 0)
    seed_req = round(seed_req_total * fraction * (1 + safety_margin_pct), 2)
    if seed_req > 0:
        required["seed_kg"] = {"required": seed_req, "unit": "kg", "name": "Seed"}

    # Fertilizer (dict)
    fert = total_inputs.get("fertilizer", {}) or {}
    required["fertilizer"] = {}
    for nutrient, qty in fert.items():
        req_qty = round(float(qty or 0) * fraction * (1 + safety_margin_pct), 2)
        required["fertilizer"][nutrient] = {"required": req_qty, "unit": "kg", "name": f"Fertilizer_{nutrient}"}

    # Pesticide liters
    pest_total = float(total_inputs.get("pesticide_liters", 0) or 0)
    pest_req = round(pest_total * fraction * (1 + safety_margin_pct), 2)
    if pest_req > 0:
        required["pesticide_liters"] = {"required": pest_req, "unit": "liter", "name": "Pesticides"}

    # Irrigation is not stocked here (water), skip

    # compare with inventory
    shortages = []
    with _inventory_lock:
        inv = {k: v.copy() for k, v in _input_inventory_store.items()}

    # check seed
    if "seed_kg" in required:
        inv_rec = inv.get("seed", None) or inv.get("seed_wheat") or None
        # attempt matching by name if exact key absent
        available = 0.0
        matched_item = None
        if inv_rec:
            available = float(inv_rec.get("quantity", 0) or 0)
            matched_item = inv_rec["item_id"]
        else:
            # look for any inventory item with 'seed' in id/name
            for iid, r in inv.items():
                if "seed" in iid.lower() or "seed" in r.get("name","").lower():
                    available = float(r.get("quantity",0) or 0)
                    matched_item = iid
                    break
        if available < required["seed_kg"]["required"]:
            deficit = round(required["seed_kg"]["required"] - available, 2)
            alert = {
                "unit_id": unit_id,
                "item_id": matched_item or "seed_unknown",
                "item_name": required["seed_kg"]["name"],
                "required_qty": required["seed_kg"]["required"],
                "available_qty": available,
                "deficit_qty": deficit,
                "unit": "kg",
                "severity": "high" if deficit > 0 else "low",
                "suggested_procure_qty": deficit
            }
            shortages.append(alert)
            _record_shortage_alert(alert)

    # check fertilizer nutrients
    for nut, meta in required.get("fertilizer", {}).items():
        req_q = float(meta["required"])
        # attempt to find inventory item matching nutrient (e.g., "urea", "dap", or generic fertilizer entries)
        available = 0.0
        matched_item = None
        with _inventory_lock:
            for iid, r in _input_inventory_store.items():
                if nut.lower() in iid.lower() or nut.lower() in r.get("name","").lower() or "fert" in iid.lower():
                    available = float(r.get("quantity",0) or 0)
                    matched_item = iid
                    break
        if available < req_q:
            deficit = round(req_q - available, 2)
            alert = {
                "unit_id": unit_id,
                "item_id": matched_item or f"fert_{nut}",
                "item_name": meta["name"],
                "required_qty": req_q,
                "available_qty": available,
                "deficit_qty": deficit,
                "unit": "kg",
                "severity": "medium" if deficit < req_q*0.5 else "high",
                "suggested_procure_qty": deficit
            }
            shortages.append(alert)
            _record_shortage_alert(alert)

    # check pesticides
    if "pesticide_liters" in required:
        req_q = float(required["pesticide_liters"]["required"])
        available = 0.0
        matched_item = None
        with _inventory_lock:
            for iid, r in _input_inventory_store.items():
                if "pesticide" in iid.lower() or "pesticide" in r.get("name","").lower() or "spray" in iid.lower():
                    available = float(r.get("quantity",0) or 0)
                    matched_item = iid
                    break
        if available < req_q:
            deficit = round(req_q - available, 2)
            alert = {
                "unit_id": unit_id,
                "item_id": matched_item or "pesticide_unknown",
                "item_name": required["pesticide_liters"]["name"],
                "required_qty": req_q,
                "available_qty": available,
                "deficit_qty": deficit,
                "unit": "liter",
                "severity": "medium" if deficit < req_q*0.5 else "high",
                "suggested_procure_qty": deficit
            }
            shortages.append(alert)
            _record_shortage_alert(alert)

    return {"unit_id": unit_id, "required": required, "shortages": shortages, "generated_at": datetime.utcnow().isoformat()}
    

# -------------------------
# Batch check (all units)
# -------------------------
def check_shortages_for_farm(lookahead_days: int = 30, safety_margin_pct: float = 0.10) -> Dict[str, Any]:
    results = []
    # attempt import unit store
    try:
        from app.services.farmer.unit_service import _unit_store
        unit_ids = list(_unit_store.keys())
    except Exception:
        unit_ids = []

    for uid in unit_ids:
        res = check_shortages_for_unit(uid, lookahead_days=lookahead_days, safety_margin_pct=safety_margin_pct)
        results.append(res)

    # aggregate suggested procurement lines
    suggestions = {}
    for r in results:
        for s in r["shortages"]:
            pid = s["item_id"]
            suggestions.setdefault(pid, {"item_id": pid, "item_name": s["item_name"], "total_suggested": 0.0, "unit": s["unit"]})
            suggestions[pid]["total_suggested"] += float(s.get("suggested_procure_qty", 0) or 0)

    return {"units_checked": len(results), "results": results, "procurement_suggestions": list(suggestions.values()), "generated_at": datetime.utcnow().isoformat()}


# -------------------------
# Create procurement PO suggestion (best-effort)
# -------------------------
def create_procurement_suggestion_po(unit_id: str, suggested_items: List[Dict[str, Any]], created_by: Optional[str] = None) -> Dict[str, Any]:
    """
    suggested_items: [{ "item_id": "...", "qty": <float>, "unit": "kg" | "liter" }]
    Uses purchase_order_service.create_po_from_parts_request if available, else returns a PO-like skeleton.
    """
    # translate to PO lines: part_id, qty (integer if kg/liter)
    requested_parts = []
    for it in suggested_items:
        part_id = it.get("item_id")
        qty = int(round(float(it.get("qty", 0) or 0)))
        if qty <= 0:
            continue
        requested_parts.append({"part_id": part_id, "qty": qty})

    if not requested_parts:
        return {"error": "no_valid_suggested_parts"}

    if create_po_from_parts_request:
        po = create_po_from_parts_request(requested_parts, related_maintenance_id=None, preferred_vendor_id=None, created_by=created_by)
        return {"created_via": "purchase_order_service", "po": po}
    else:
        # return a skeleton
        po = {
            "po_id": f"po_suggestion_{unit_id}_{int(datetime.utcnow().timestamp())}",
            "created_at": datetime.utcnow().isoformat(),
            "created_by": created_by,
            "lines": requested_parts,
            "status": "suggested",
            "estimated_total": None
        }
        return {"created_via": "skeleton", "po": po}
