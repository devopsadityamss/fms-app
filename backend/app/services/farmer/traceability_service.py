# backend/app/services/farmer/traceability_service.py
"""
Unified Harvest Lot Traceability Service (merged)
- Standardizes on lot_id (keeps batch alias wrappers)
- Features:
  * create_lot / create_batch (alias)
  * attach/detach documents
  * record events: created, packed, stored, transferred, arrived, processed, sold, note
  * transfer ownership
  * sales recording (best-effort ledger integration)
  * provenance report (events + docs)
  * QR payload
  * export CSV / JSON
  * mock certificate generation
  * query trace per lot or per farmer
"""

from datetime import datetime
from threading import Lock
from typing import Dict, Any, List, Optional
import uuid
import io
import csv
import json

# defensive imports (best-effort)
try:
    from app.services.farmer.harvest_lot_service import get_harvest_lot as _get_harvest_lot_snapshot
except Exception:
    _get_harvest_lot_snapshot = lambda lot_id: {}

try:
    from app.services.farmer.finance_service import add_ledger_entry as _add_ledger_entry
except Exception:
    _add_ledger_entry = None

_lock = Lock()

# Primary stores
_lots: Dict[str, Dict[str, Any]] = {}            # lot_id -> lot metadata (merged batch/lot record)
_trace_records: Dict[str, List[Dict[str, Any]]] = {}  # lot_id -> ordered events
_lots_by_farmer: Dict[str, List[str]] = {}       # farmer_id -> [lot_ids]

# convenience indices
_sales_index: Dict[str, Dict[str, Any]] = {}     # sale_id -> sale record

# helpers
def _now_iso() -> str:
    return datetime.utcnow().isoformat()

def _uid(prefix: str = "id") -> str:
    return f"{prefix}_{uuid.uuid4()}"

# -----------------------
# Create / CRUD (lot-centric)
# -----------------------
def create_lot(
    farmer_id: str,
    unit_id: Optional[str],
    crop: str,
    harvested_qty_kg: float,
    harvest_date_iso: Optional[str] = None,
    variety: Optional[str] = None,
    grade: Optional[str] = None,
    doc_refs: Optional[List[Dict[str, Any]]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Primary creation method. Returns lot record and logs a 'created' trace event.
    Kept fields compatible with earlier 'batch' and 'lot' variants.
    """
    lid = _uid("lot")
    rec = {
        "lot_id": lid,
        "farmer_id": farmer_id,
        "unit_id": unit_id,
        "crop": crop.lower() if isinstance(crop, str) else crop,
        "variety": variety or None,
        "harvest_date": harvest_date_iso or datetime.utcnow().date().isoformat(),
        "harvested_qty_kg": float(harvested_qty_kg),
        "available_qty_kg": float(harvested_qty_kg),
        "grade": grade or None,
        "doc_refs": doc_refs or [],
        "metadata": metadata or {},
        "created_at": _now_iso(),
        "current_owner": farmer_id,
        "status": "created",  # created | packed | in_transit | at_warehouse | stored | processed | sold
    }
    with _lock:
        _lots[lid] = rec
        _lots_by_farmer.setdefault(farmer_id, []).append(lid)
        # create initial trace event
        _trace_records.setdefault(lid, []).append({
            "trace_id": _uid("trace"),
            "lot_id": lid,
            "type": "created",
            "actor": farmer_id,
            "details": {"snapshot": rec},
            "timestamp": _now_iso()
        })
    return rec

def create_batch(
    farmer_id: str,
    unit_id: str,
    crop: str,
    variety: Optional[str],
    harvest_date_iso: Optional[str],
    total_weight_kg: float,
    grade: Optional[str] = None,
    doc_refs: Optional[List[Dict[str, Any]]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Backwards-compatible alias: wraps create_lot and keeps field names similar to older API.
    Returns the created lot record.
    """
    return create_lot(
        farmer_id=farmer_id,
        unit_id=unit_id,
        crop=crop,
        harvested_qty_kg=total_weight_kg,
        harvest_date_iso=harvest_date_iso,
        variety=variety,
        grade=grade,
        doc_refs=doc_refs,
        metadata=metadata
    )

def get_lot(lot_id: str) -> Dict[str, Any]:
    with _lock:
        rec = _lots.get(lot_id)
        return rec.copy() if rec else {}

def list_lots_for_farmer(farmer_id: str) -> List[Dict[str, Any]]:
    with _lock:
        ids = _lots_by_farmer.get(farmer_id, [])
        return [ _lots[i].copy() for i in ids if i in _lots ]

def delete_lot(lot_id: str) -> Dict[str, Any]:
    with _lock:
        rec = _lots.pop(lot_id, None)
        if not rec:
            return {"error": "not_found"}
        _trace_records.pop(lot_id, None)
        farmer_id = rec.get("farmer_id")
        if farmer_id and farmer_id in _lots_by_farmer:
            _lots_by_farmer[farmer_id] = [i for i in _lots_by_farmer[farmer_id] if i != lot_id]
    return {"status": "deleted", "lot_id": lot_id}

# -----------------------
# Documents (attach/detach)
# -----------------------
def attach_doc_to_lot(lot_id: str, doc_ref: str, doc_type: Optional[str] = None, uploaded_by: Optional[str] = None) -> Dict[str, Any]:
    with _lock:
        if lot_id not in _lots:
            return {"error": "lot_not_found"}
        entry = {"doc_ref": doc_ref, "type": doc_type or "generic", "uploaded_by": uploaded_by or "", "uploaded_at": _now_iso()}
        _lots[lot_id].setdefault("doc_refs", []).append(entry)
        _trace_records.setdefault(lot_id, []).append({
            "trace_id": _uid("trace"),
            "lot_id": lot_id,
            "type": "doc_attached",
            "actor": uploaded_by or "",
            "details": entry,
            "timestamp": _now_iso()
        })
    return entry

def detach_doc_from_lot(lot_id: str, doc_ref: str) -> Dict[str, Any]:
    with _lock:
        if lot_id not in _lots:
            return {"error": "lot_not_found"}
        docs = _lots[lot_id].get("doc_refs", [])
        remaining = [d for d in docs if d.get("doc_ref") != doc_ref and d != doc_ref]
        _lots[lot_id]["doc_refs"] = remaining
        ev = {
            "trace_id": _uid("trace"),
            "lot_id": lot_id,
            "type": "doc_detached",
            "actor": "system",
            "details": {"doc_ref": doc_ref},
            "timestamp": _now_iso()
        }
        _trace_records.setdefault(lot_id, []).append(ev)
    return {"detached": doc_ref}

# -----------------------
# Events & custody
# -----------------------
def record_event(lot_id: str, event_type: str, actor: str, note: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    General-purpose event recorder. Supported types:
    created, packed, stored, transferred, arrived, processed, sold, note
    metadata may contain context (to, at, buyer, qty, price, etc.)
    """
    with _lock:
        if lot_id not in _lots:
            return {"error": "lot_not_found"}
        ev = {
            "trace_id": _uid("trace"),
            "lot_id": lot_id,
            "type": event_type,
            "actor": actor or "",
            "details": {"note": note or "", **(metadata or {})},
            "timestamp": _now_iso()
        }
        _trace_records.setdefault(lot_id, []).append(ev)

        # update lot record for some event types
        if event_type == "transferred":
            to = (metadata or {}).get("to")
            if to:
                _lots[lot_id]["current_owner"] = to
                _lots[lot_id]["status"] = "in_transit"
        elif event_type == "packed":
            _lots[lot_id]["status"] = "packed"
        elif event_type == "arrived":
            _lots[lot_id]["status"] = "at_warehouse"
            at = (metadata or {}).get("at")
            if at:
                _lots[lot_id]["current_owner"] = at
        elif event_type == "stored":
            _lots[lot_id]["status"] = "stored"
        elif event_type == "processed":
            _lots[lot_id]["status"] = "processed"
        elif event_type == "sold":
            _lots[lot_id]["status"] = "sold"
            buyer = (metadata or {}).get("buyer")
            if buyer:
                _lots[lot_id]["current_owner"] = buyer
    return ev

def transfer_lot(lot_id: str, from_actor: str, to_actor: str, note: Optional[str] = None) -> Dict[str, Any]:
    meta = {"to": to_actor}
    ev = record_event(lot_id, "transferred", from_actor, note=note, metadata=meta)
    return {"transfer_event": ev, "lot": get_lot(lot_id)}

# -----------------------
# Sales / finance linking
# -----------------------
def record_sale(
    lot_id: str,
    buyer_name: str,
    buyer_id: Optional[str],
    qty_kg: float,
    price_per_kg: float,
    sold_by: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Record sale event and, if finance_service is available, add an income ledger entry.
    Returns sale record.
    """
    sale_id = _uid("sale")
    total_amount = round(float(qty_kg) * float(price_per_kg), 2)
    sale_rec = {
        "sale_id": sale_id,
        "lot_id": lot_id,
        "buyer_name": buyer_name,
        "buyer_id": buyer_id,
        "qty_kg": float(qty_kg),
        "price_per_kg": float(price_per_kg),
        "total_amount": total_amount,
        "sold_by": sold_by or "",
        "metadata": metadata or {},
        "timestamp": _now_iso()
    }
    with _lock:
        _sales_index[sale_id] = sale_rec
        _trace_records.setdefault(lot_id, []).append({
            "trace_id": _uid("trace"),
            "lot_id": lot_id,
            "type": "sale",
            "actor": sold_by or "",
            "details": sale_rec,
            "timestamp": _now_iso()
        })
        # reduce available quantity best-effort
        if lot_id in _lots:
            try:
                _lots[lot_id]["available_qty_kg"] = max(0.0, float(_lots[lot_id].get("available_qty_kg", 0.0)) - float(qty_kg))
            except Exception:
                pass

    # best-effort finance ledger entry
    try:
        if _add_ledger_entry:
            # attempt to enrich with farmer/unit context
            lot_snap = _get_harvest_lot_snapshot(lot_id) or get_lot(lot_id)
            farmer_for_entry = lot_snap.get("farmer_id") or (get_lot(lot_id).get("farmer_id") if get_lot(lot_id) else None)
            unit_for_entry = lot_snap.get("unit_id") or (get_lot(lot_id).get("unit_id") if get_lot(lot_id) else None)
            _add_ledger_entry(
                farmer_id=farmer_for_entry or "unknown",
                unit_id=unit_for_entry,
                entry_type="income",
                category="sale",
                amount=total_amount,
                currency="INR",
                date_iso=_now_iso(),
                description=f"Sale of lot {lot_id} to {buyer_name}",
                tags=["sale", "harvest"],
                metadata={"sale_id": sale_id, **(metadata or {})}
            )
    except Exception:
        # ignore finance errors
        pass

    return sale_rec

def list_sales_for_lot(lot_id: str) -> List[Dict[str, Any]]:
    with _lock:
        return [s.copy() for s in _sales_index.values() if s.get("lot_id") == lot_id]

def get_sale(sale_id: str) -> Dict[str, Any]:
    with _lock:
        return _sales_index.get(sale_id, {}).copy()

# -----------------------
# Trace querying & provenance
# -----------------------
def get_trace_for_lot(lot_id: str) -> Dict[str, Any]:
    with _lock:
        events = list(_trace_records.get(lot_id, [])).copy()
    # ensure chronological order
    events_sorted = sorted(events, key=lambda e: e.get("timestamp",""))
    return {"lot_id": lot_id, "events": events_sorted, "count": len(events_sorted)}

def get_trace_for_farmer(farmer_id: str) -> Dict[str, Any]:
    with _lock:
        lots = list_lots_for_farmer(farmer_id)
    out = {}
    for l in lots:
        lid = l.get("lot_id")
        out[lid] = get_trace_for_lot(lid)
    return {"farmer_id": farmer_id, "trace": out}

def provenance_report(lot_id: str) -> Dict[str, Any]:
    lot = get_lot(lot_id)
    if not lot:
        return {"error": "lot_not_found"}
    events = get_trace_for_lot(lot_id).get("events", [])
    return {
        "lot": lot,
        "events": events,
        "doc_refs": lot.get("doc_refs", []),
        "provenance_generated_at": _now_iso()
    }

# -----------------------
# Exports & QR / certificate
# -----------------------
def export_trace_csv(lot_id: str) -> str:
    t = get_trace_for_lot(lot_id).get("events", [])
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["trace_id","timestamp","type","actor","details_json"])
    for ev in t:
        w.writerow([ev.get("trace_id"), ev.get("timestamp"), ev.get("type"), ev.get("actor"), json.dumps(ev.get("details") or {})])
    return out.getvalue()

def export_trace_json(lot_id: str) -> str:
    return json.dumps(get_trace_for_lot(lot_id), default=str, indent=2)

def qr_payload_for_lot(lot_id: str) -> Dict[str, Any]:
    lot = get_lot(lot_id)
    if not lot:
        return {"error": "lot_not_found"}
    payload = {
        "lot_id": lot.get("lot_id"),
        "crop": lot.get("crop"),
        "variety": lot.get("variety"),
        "harvest_date": lot.get("harvest_date"),
        "weight_kg": lot.get("harvested_qty_kg"),
        "current_owner": lot.get("current_owner"),
        "status": lot.get("status")
    }
    return payload

def generate_trace_certificate(lot_id: str, issuer: Optional[str] = None, notes: Optional[str] = None) -> Dict[str, Any]:
    lot = get_lot(lot_id)
    if not lot:
        return {"error": "lot_not_found"}
    trace = get_trace_for_lot(lot_id)
    cert = {
        "certificate_id": _uid("cert"),
        "lot_id": lot_id,
        "lot_snapshot": lot,
        "event_count": trace.get("count"),
        "issued_by": issuer or "system",
        "issued_at": _now_iso(),
        "notes": notes or "",
        "signature": f"MOCK-SIGN-{uuid.uuid4()}"
    }
    # append certificate issuance as a trace event
    record_event(lot_id, "note", issuer or "system", note=f"certificate_issued:{cert['certificate_id']}", metadata={"certificate": cert})
    return cert
