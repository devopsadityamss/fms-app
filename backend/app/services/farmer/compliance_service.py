# backend/app/services/farmer/compliance_service.py

from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, Any, List, Optional, Callable
import uuid

# ===================================================================
# MOCK PHI & CHEMICAL COMPLIANCE CHECKS (for harvest safety)
# ===================================================================

def check_pre_harvest_interval(material_name: str, days_since_application: int) -> Dict[str, Any]:
    """
    Mock pre-harvest interval (PHI) check for a chemical.
    """
    # Simple mock rules:
    phi_days = {
        "Pesticide A": 7,
        "Pesticide B": 14,
        "Herbicide X": 21,
    }
    required = phi_days.get(material_name, 7)
    safe_to_harvest = days_since_application >= required
    return {
        "material": material_name,
        "required_phi_days": required,
        "days_since_application": days_since_application,
        "safe_to_harvest": safe_to_harvest
    }


def get_compliance_advice(unit_id: int, material_name: str, days_since_application: int) -> Dict[str, Any]:
    """Unified compliance check."""
    return {
        "unit_id": unit_id,
        "timestamp": datetime.utcnow(),
        "phi_check": check_pre_harvest_interval(material_name, days_since_application),
        "advice": "Delay harvest until PHI satisfied" if not check_pre_harvest_interval(material_name, days_since_application)["safe_to_harvest"] else "OK to proceed"
    }


# ===================================================================
# FULL COMPLIANCE & CERTIFICATION TRACKER (in-memory)
# ===================================================================

"""
Compliance & Certification Tracker (in-memory)
Features:
 - Register certifications per farmer/unit (type, issuer, doc_ref, issued_at, expires_at)
 - Attach document metadata (filename, storage_key, checksum) — no file handling here
 - Query current certifications, expired, expiring within N days
 - Create renewal tasks and simple workflow (open -> in_progress -> renewed -> closed)
 - Simple validation helpers and recommended renewal window
 - Optional notify_callback hook parameter on actions to allow wiring to notification service
"""

_lock = Lock()

# Stores
_certifications: Dict[str, Dict[str, Any]] = {}  # cert_id -> cert record
_certs_by_farmer: Dict[str, List[str]] = {}     # farmer_id -> [cert_id]
_renewal_tasks: Dict[str, Dict[str, Any]] = {}   # task_id -> task record
_tasks_by_farmer: Dict[str, List[str]] = {}     # farmer_id -> [task_id]

def _now_iso():
    return datetime.utcnow().isoformat()

def _parse_iso(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None

# ------------------------------
# Certification CRUD
# ------------------------------
def add_certification(
    farmer_id: str,
    unit_id: Optional[str],
    cert_type: str,  # e.g., "organic", "GAP", "kyc", "pesticide_free"
    issuer: Optional[str],
    doc_ref: Optional[str],  # pointer to file storage key or doc id
    issued_at_iso: Optional[str],
    expires_at_iso: Optional[str],
    metadata: Optional[Dict[str, Any]] = None,
    notify_callback: Optional[Callable] = None
) -> Dict[str, Any]:
    cid = f"cert_{uuid.uuid4()}"
    rec = {
        "cert_id": cid,
        "farmer_id": farmer_id,
        "unit_id": unit_id,
        "cert_type": cert_type.lower(),
        "issuer": issuer,
        "doc_ref": doc_ref,
        "issued_at": issued_at_iso or _now_iso(),
        "expires_at": expires_at_iso,
        "metadata": metadata or {},
        "created_at": _now_iso(),
        "status": "active"  # active | expired | revoked
    }
    with _lock:
        _certifications[cid] = rec
        _certs_by_farmer.setdefault(farmer_id, []).append(cid)
    # optional notify hook: e.g., new certification issued
    try:
        if notify_callback:
            notify_callback({"type": "cert_added", "cert": rec})
    except Exception:
        pass
    return rec

def get_cert(cert_id: str) -> Dict[str, Any]:
    with _lock:
        return _certifications.get(cert_id, {})

def list_certifications(farmer_id: Optional[str] = None, unit_id: Optional[str] = None) -> List[Dict[str, Any]]:
    with _lock:
        if farmer_id:
            ids = _certs_by_farmer.get(farmer_id, [])[:]
            items = [ _certifications.get(i) for i in ids ]
        else:
            items = list(_certifications.values())
    # filter by unit if requested
    if unit_id:
        items = [c for c in items if c and c.get("unit_id") == unit_id]
    # normalize None removal
    return [c for c in items if c]

def revoke_certification(cert_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
    with _lock:
        c = _certifications.get(cert_id)
        if not c:
            return {"error": "cert_not_found"}
        c["status"] = "revoked"
        c["revoked_at"] = _now_iso()
        if reason:
            c.setdefault("metadata", {})["revocation_reason"] = reason
        _certifications[cert_id] = c
    return c

# ------------------------------
# Expiry & renewal helpers
# ------------------------------
def _is_expired(cert: Dict[str, Any]) -> bool:
    exp = _parse_iso(cert.get("expires_at"))
    if not exp:
        return False
    return datetime.utcnow() > exp

def list_expired_certifications(farmer_id: Optional[str] = None) -> List[Dict[str, Any]]:
    all_c = list_certifications(farmer_id=farmer_id)
    return [c for c in all_c if _is_expired(c)]

def list_expiring_within(days: int = 30, farmer_id: Optional[str] = None) -> List[Dict[str, Any]]:
    cutoff = datetime.utcnow() + timedelta(days=days)
    res = []
    for c in list_certifications(farmer_id=farmer_id):
        exp = _parse_iso(c.get("expires_at"))
        if not exp:
            continue
        if datetime.utcnow() <= exp <= cutoff:
            res.append(c)
    return res

def recommended_renewal_window(cert_type: str) -> int:
    """
    Return recommended days before expiry to begin renewal.
    Default rules per cert type (heuristic).
    """
    ct = cert_type.lower()
    if ct == "organic":
        return 90
    if ct == "gap":
        return 60
    if ct == "kyc":
        return 30
    if ct == "pesticide_free":
        return 45
    return 30

# ------------------------------
# Renewal tasks & workflow
# ------------------------------
def create_renewal_task(
    farmer_id: str,
    cert_id: str,
    due_date_iso: Optional[str] = None,
    assigned_to: Optional[str] = None,
    notes: Optional[str] = None,
    notify_callback: Optional[Callable] = None
) -> Dict[str, Any]:
    if cert_id not in _certifications:
        return {"error": "cert_not_found"}
    tid = f"task_{uuid.uuid4()}"
    rec = {
        "task_id": tid,
        "farmer_id": farmer_id,
        "cert_id": cert_id,
        "status": "open",  # open | in_progress | renewed | closed
        "assigned_to": assigned_to,
        "created_at": _now_iso(),
        "due_date": due_date_iso,
        "notes": notes or ""
    }
    with _lock:
        _renewal_tasks[tid] = rec
        _tasks_by_farmer.setdefault(farmer_id, []).append(tid)
    # optional notify
    try:
        if notify_callback:
            notify_callback({"type": "renewal_task_created", "task": rec})
    except Exception:
        pass
    return rec

def update_renewal_task(task_id: str, updates: Dict[str, Any], notify_callback: Optional[Callable] = None) -> Dict[str, Any]:
    with _lock:
        t = _renewal_tasks.get(task_id)
        if not t:
            return {"error": "task_not_found"}
        t.update(updates)
        t["updated_at"] = _now_iso()
        _renewal_tasks[task_id] = t
    # if task marked renewed, update certification expiry if provided
    if updates.get("status") == "renewed" and updates.get("new_expires_at"):
        cert = _certifications.get(t["cert_id"])
        if cert:
            cert["expires_at"] = updates.get("new_expires_at")
            cert["metadata"] = cert.get("metadata", {})
            cert["metadata"]["last_renewed_task"] = task_id
            with _lock:
                _certifications[cert["cert_id"]] = cert
    try:
        if notify_callback:
            notify_callback({"type": "renewal_task_updated", "task": t})
    except Exception:
        pass
    return t

def list_renewal_tasks(farmer_id: Optional[str] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
    with _lock:
        items = list(_renewal_tasks.values())
    if farmer_id:
        items = [i for i in items if i.get("farmer_id") == farmer_id]
    if status:
        items = [i for i in items if i.get("status") == status]
    return items

# ------------------------------
# Utility: auto-create renewal tasks for certs nearing expiry
# ------------------------------
def auto_create_renewal_tasks(days_before: int = 30, notify_callback: Optional[Callable] = None) -> Dict[str, Any]:
    """
    For all certifications expiring within days_before, create renewal tasks if none exist.
    Returns created task ids.
    """
    created = []
    expiring = list_expiring_within(days=days_before)
    with _lock:
        existing_tasks = list(_renewal_tasks.values())
    for cert in expiring:
        farmer_id = cert.get("farmer_id")
        cert_id = cert.get("cert_id")
        # check if open task exists for this cert
        exists = any(t for t in existing_tasks if t.get("cert_id") == cert_id and t.get("status") in ("open","in_progress"))
        if exists:
            continue
        # create task due on cert.expires_at
        task = create_renewal_task(farmer_id=farmer_id, cert_id=cert_id, due_date_iso=cert.get("expires_at"), notify_callback=notify_callback)
        created.append(task.get("task_id"))
    return {"created_count": len(created), "created_tasks": created}

# ------------------------------
# Simple reports
# ------------------------------
def compliance_summary_for_farmer(farmer_id: str) -> Dict[str, Any]:
    certs = list_certifications(farmer_id=farmer_id)
    expiring_30 = list_expiring_within(30, farmer_id=farmer_id)
    expired = list_expired_certifications(farmer_id=farmer_id)
    tasks = list_renewal_tasks(farmer_id=farmer_id)
    return {
        "farmer_id": farmer_id,
        "total_certifications": len(certs),
        "expiring_within_30_days": len(expiring_30),
        "expired_count": len(expired),
        "open_renewal_tasks": len([t for t in tasks if t.get("status") in ("open","in_progress")]),
        "details": {
            "certifications": certs,
            "expiring_30": expiring_30,
            "expired": expired,
            "renewal_tasks": tasks
        },
        "timestamp": _now_iso()
    }