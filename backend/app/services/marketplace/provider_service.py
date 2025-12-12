# backend/app/services/marketplace/provider_service.py

from datetime import datetime
from threading import Lock
from typing import Dict, Any, List, Optional
import uuid
import base64

"""
Provider Onboarding & KYC (in-memory)

Stores:
 - _provider_store: provider_id -> provider profile
 - _kyc_store: provider_id -> list of kyc doc records { doc_id, filename, mime, uploaded_at, bytes_b64, status, notes }
 - _kyc_audit: list of audit actions { action_id, provider_id, actor, action, comment, ts }

KYC status flow:
 - not_submitted -> pending -> under_review -> approved | rejected | needs_more_info
"""

_lock = Lock()

# providers
_provider_store: Dict[str, Dict[str, Any]] = {}

# provider KYC documents list (provider_id -> [doc, ...])
_kyc_store: Dict[str, List[Dict[str, Any]]] = {}

# audit trail
_kyc_audit: List[Dict[str, Any]] = []


def _now_iso() -> str:
    return datetime.utcnow().isoformat()


# -----------------------
# Provider profile
# -----------------------
def register_provider_basic(provider_id: Optional[str], name: str, contact: Optional[str] = None, address: Optional[str] = None) -> Dict[str, Any]:
    pid = provider_id or f"prov_{uuid.uuid4()}"
    rec = {
        "provider_id": pid,
        "name": name,
        "contact": contact,
        "address": address,
        "kyc_status": "not_submitted",
        "created_at": _now_iso(),
        "updated_at": _now_iso()
    }
    with _lock:
        _provider_store[pid] = rec
        _kyc_store.setdefault(pid, [])
    return rec


def get_provider(provider_id: str) -> Dict[str, Any]:
    return _provider_store.get(provider_id, {})


def list_providers(status: Optional[str] = None, query: Optional[str] = None) -> Dict[str, Any]:
    with _lock:
        items = list(_provider_store.values())
    if status:
        items = [p for p in items if p.get("kyc_status") == status]
    if query:
        q = query.strip().lower()
        items = [p for p in items if q in (p.get("name","").lower() + " " + str(p.get("contact","")).lower())]
    return {"count": len(items), "providers": items}


def update_provider(provider_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    with _lock:
        p = _provider_store.get(provider_id)
        if not p:
            return {"error": "not_found"}
        p.update(updates)
        p["updated_at"] = _now_iso()
        _provider_store[provider_id] = p
    return p


# -----------------------
# KYC documents
# -----------------------
def submit_kyc_document(provider_id: str, filename: str, mime: str, content_bytes: bytes, doc_type: Optional[str] = None) -> Dict[str, Any]:
    if provider_id not in _provider_store:
        return {"error": "provider_not_found"}
    doc_id = f"doc_{uuid.uuid4()}"
    b64 = base64.b64encode(content_bytes).decode()
    rec = {
        "doc_id": doc_id,
        "provider_id": provider_id,
        "filename": filename,
        "mime": mime,
        "doc_type": doc_type or "unspecified",
        "bytes_b64": b64,
        "status": "pending",
        "notes": None,
        "uploaded_at": _now_iso()
    }
    with _lock:
        _kyc_store.setdefault(provider_id, []).append(rec)
        # update provider kyc_status to pending
        p = _provider_store.get(provider_id)
        if p:
            p["kyc_status"] = "pending"
            p["updated_at"] = _now_iso()
            _provider_store[provider_id] = p
        _kyc_audit.append({
            "action_id": f"audit_{uuid.uuid4()}",
            "provider_id": provider_id,
            "actor": "provider",
            "action": "submit_document",
            "doc_id": doc_id,
            "comment": f"Submitted {filename}",
            "ts": _now_iso()
        })
    return rec


def list_kyc_documents(provider_id: str) -> List[Dict[str, Any]]:
    return _kyc_store.get(provider_id, [])


def get_kyc_document(provider_id: str, doc_id: str) -> Dict[str, Any]:
    docs = _kyc_store.get(provider_id, [])
    for d in docs:
        if d.get("doc_id") == doc_id:
            return d
    return {}


# -----------------------
# KYC review actions (admin)
# -----------------------
def _record_audit(provider_id: str, actor: str, action: str, comment: Optional[str], doc_id: Optional[str] = None):
    with _lock:
        _kyc_audit.append({
            "action_id": f"audit_{uuid.uuid4()}",
            "provider_id": provider_id,
            "actor": actor,
            "action": action,
            "doc_id": doc_id,
            "comment": comment,
            "ts": _now_iso()
        })


def start_kyc_review(provider_id: str, reviewer_id: str) -> Dict[str, Any]:
    if provider_id not in _provider_store:
        return {"error": "provider_not_found"}
    with _lock:
        p = _provider_store[provider_id]
        p["kyc_status"] = "under_review"
        p["updated_at"] = _now_iso()
        _provider_store[provider_id] = p
        _record_audit(provider_id, reviewer_id, "start_review", "review started")
    return {"status": "under_review", "provider": p}


def approve_kyc(provider_id: str, reviewer_id: str, comment: Optional[str] = None) -> Dict[str, Any]:
    if provider_id not in _provider_store:
        return {"error": "provider_not_found"}
    with _lock:
        p = _provider_store[provider_id]
        p["kyc_status"] = "approved"
        p["updated_at"] = _now_iso()
        _provider_store[provider_id] = p
        # mark all pending docs as approved
        for d in _kyc_store.get(provider_id, []):
            if d.get("status") == "pending":
                d["status"] = "approved"
                d["notes"] = comment
        _record_audit(provider_id, reviewer_id, "approve_kyc", comment or "approved")
    return {"status": "approved", "provider": p}


def reject_kyc(provider_id: str, reviewer_id: str, comment: Optional[str] = None) -> Dict[str, Any]:
    if provider_id not in _provider_store:
        return {"error": "provider_not_found"}
    with _lock:
        p = _provider_store[provider_id]
        p["kyc_status"] = "rejected"
        p["updated_at"] = _now_iso()
        _provider_store[provider_id] = p
        # mark pending docs as rejected
        for d in _kyc_store.get(provider_id, []):
            if d.get("status") == "pending":
                d["status"] = "rejected"
                d["notes"] = comment
        _record_audit(provider_id, reviewer_id, "reject_kyc", comment or "rejected")
    return {"status": "rejected", "provider": p}


def request_more_info(provider_id: str, reviewer_id: str, comment: Optional[str] = None) -> Dict[str, Any]:
    if provider_id not in _provider_store:
        return {"error": "provider_not_found"}
    with _lock:
        p = _provider_store[provider_id]
        p["kyc_status"] = "needs_more_info"
        p["updated_at"] = _now_iso()
        _provider_store[provider_id] = p
        _record_audit(provider_id, reviewer_id, "request_more_info", comment or "needs more documents")
    return {"status": "needs_more_info", "provider": p}


# -----------------------
# Audit & admin
# -----------------------
def get_kyc_audit(provider_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    items = list(reversed(_kyc_audit))
    if provider_id:
        items = [i for i in items if i.get("provider_id") == provider_id]
    return items[:limit]
