# backend/app/services/farmer/traceability_service.py

"""
Supply Chain Traceability & Batch Management (in-memory)

Features:
 - Create harvest batches (batch_id) with metadata: unit_id, crop, variety, harvest_date, weight_kg
 - Attach documents / certifications to batches (doc_ref)
 - Record chain-of-custody events (created, packed, transferred, processed, sold) with actor & timestamp
 - Transfer ownership (farmer -> trader -> buyer) with event logging
 - Query batch history and current status
 - Generate simple provenance summary (events, docs, certifications)
 - Produce a QR payload (JSON) representing batch metadata for frontend to render/encode
"""

from datetime import datetime
from threading import Lock
from typing import Dict, Any, List, Optional
import uuid

_lock = Lock()

_batches: Dict[str, Dict[str, Any]] = {}           # batch_id -> batch metadata
_batch_events: Dict[str, List[Dict[str, Any]]] = {} # batch_id -> [events]
_batches_by_farmer: Dict[str, List[str]] = {}      # farmer_id -> [batch_ids]


def _now_iso():
    return datetime.utcnow().isoformat()


def _newid(prefix: str):
    return f"{prefix}_{uuid.uuid4()}"


# ------------------------
# Batch creation & metadata
# ------------------------
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
    Create a new batch record and log a 'created' event.
    doc_refs: list of {"doc_ref": "...", "type": "organic_cert" }
    """
    bid = _newid("batch")
    rec = {
        "batch_id": bid,
        "farmer_id": farmer_id,
        "unit_id": unit_id,
        "crop": crop.lower(),
        "variety": variety or "default",
        "harvest_date": harvest_date_iso or _now_iso(),
        "total_weight_kg": float(total_weight_kg),
        "grade": grade or None,
        "doc_refs": doc_refs or [],
        "metadata": metadata or {},
        "created_at": _now_iso(),
        "current_owner": farmer_id,
        "status": "created"  # created | packed | in_transit | at_warehouse | processed | sold
    }
    with _lock:
        _b = _batches
        _b[bid] = rec
        _batch_events.setdefault(bid, []).append({
            "event_id": _newid("ev"),
            "type": "created",
            "actor": farmer_id,
            "timestamp": _now_iso(),
            "note": "batch created",
        })
        _batches_by_farmer.setdefault(farmer_id, []).append(bid)
    return rec


def get_batch(batch_id: str) -> Dict[str, Any]:
    return _batches.get(batch_id, {})


def list_batches_for_farmer(farmer_id: str) -> List[Dict[str, Any]]:
    ids = _batches_by_farmer.get(farmer_id, [])
    return [ _batches[i] for i in ids if i in _batches ]


# ------------------------
# Events & custody
# ------------------------
def record_event(batch_id: str, event_type: str, actor: str, note: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if batch_id not in _batches:
        return {"error": "batch_not_found"}
    ev = {
        "event_id": _newid("ev"),
        "type": event_type,
        "actor": actor,
        "timestamp": _now_iso(),
        "note": note or "",
        "metadata": metadata or {}
    }
    with _lock:
        _batch_events.setdefault(batch_id, []).append(ev)
        # update status/ownership on certain events
        if event_type == "transferred":
            # metadata expected to include "to" field
            to = (metadata or {}).get("to")
            if to:
                _batches[batch_id]["current_owner"] = to
                _batches[batch_id]["status"] = "in_transit"
        if event_type == "packed":
            _batches[batch_id]["status"] = "packed"
        if event_type == "arrived":
            _batches[batch_id]["status"] = "at_warehouse"
            to = (metadata or {}).get("at")
            if to:
                _batches[batch_id]["current_owner"] = to
        if event_type == "processed":
            _batches[batch_id]["status"] = "processed"
        if event_type == "sold":
            _batches[batch_id]["status"] = "sold"
            to = (metadata or {}).get("buyer")
            if to:
                _batches[batch_id]["current_owner"] = to
    return ev


def get_batch_events(batch_id: str) -> List[Dict[str, Any]]:
    return list(_batch_events.get(batch_id, []))


# ------------------------
# Transfers helper
# ------------------------
def transfer_batch(batch_id: str, from_actor: str, to_actor: str, note: Optional[str] = None) -> Dict[str, Any]:
    if batch_id not in _batches:
        return {"error": "batch_not_found"}
    ev = record_event(batch_id, "transferred", from_actor, note=note, metadata={"to": to_actor})
    return {"transfer_event": ev, "batch": _batches[batch_id]}


# ------------------------
# Attach / detach docs (metadata only)
# ------------------------
def attach_doc_to_batch(batch_id: str, doc_ref: str, doc_type: Optional[str] = None, uploaded_by: Optional[str] = None) -> Dict[str, Any]:
    if batch_id not in _batches:
        return {"error": "batch_not_found"}
    entry = {"doc_ref": doc_ref, "type": doc_type or "generic", "uploaded_by": uploaded_by, "uploaded_at": _now_iso()}
    with _lock:
        _batches[batch_id].setdefault("doc_refs", []).append(entry)
        _batch_events.setdefault(batch_id, []).append({
            "event_id": _newid("ev"),
            "type": "doc_attached",
            "actor": uploaded_by,
            "timestamp": _now_iso(),
            "note": f"doc {doc_ref} attached",
            "metadata": {"doc_ref": doc_ref, "type": doc_type}
        })
    return entry


def detach_doc_from_batch(batch_id: str, doc_ref: str) -> Dict[str, Any]:
    if batch_id not in _batches:
        return {"error": "batch_not_found"}
    with _lock:
        docs = _batches[batch_id].get("doc_refs", [])
        remaining = [d for d in docs if d.get("doc_ref") != doc_ref and d != doc_ref]
        _batches[batch_id]["doc_refs"] = remaining
        ev = {
            "event_id": _newid("ev"),
            "type": "doc_detached",
            "actor": "system",
            "timestamp": _now_iso(),
            "note": f"doc {doc_ref} detached",
            "metadata": {"doc_ref": doc_ref}
        }
        _batch_events.setdefault(batch_id, []).append(ev)
    return {"detached": doc_ref}


# ------------------------
# Provenance & QR payload
# ------------------------
def provenance_report(batch_id: str) -> Dict[str, Any]:
    b = _batches.get(batch_id)
    if not b:
        return {"error": "batch_not_found"}
    events = get_batch_events(batch_id)
    return {
        "batch": b,
        "events": events,
        "doc_refs": b.get("doc_refs", []),
        "provenance_generated_at": _now_iso()
    }


def qr_payload_for_batch(batch_id: str) -> Dict[str, Any]:
    """
    Return a small JSON-friendly payload that frontends can encode into a QR code.
    """
    b = _batches.get(batch_id)
    if not b:
        return {"error": "batch_not_found"}
    payload = {
        "batch_id": b["batch_id"],
        "crop": b["crop"],
        "variety": b.get("variety"),
        "harvest_date": b.get("harvest_date"),
        "weight_kg": b.get("total_weight_kg"),
        "current_owner": b.get("current_owner"),
        "status": b.get("status")
    }
    return payload
