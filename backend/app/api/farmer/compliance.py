# backend/app/api/farmer/compliance.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from app.services.farmer.compliance_service import (
    add_certification,
    get_cert,
    list_certifications,
    revoke_certification,
    list_expired_certifications,
    list_expiring_within,
    recommended_renewal_window,
    create_renewal_task,
    update_renewal_task,
    list_renewal_tasks,
    auto_create_renewal_tasks,
    compliance_summary_for_farmer,
    get_compliance_advice,        # ← ADDED from PHI version
)

router = APIRouter()

# ===========================
# PHI & HARVEST COMPLIANCE ENDPOINT (Mock)
# ===========================

@router.get("/compliance/{unit_id}")
def compliance_overview(unit_id: int, material_name: str = "Pesticide A", days_since_application: int = 0):
    return get_compliance_advice(unit_id, material_name, days_since_application)


# ===========================
# FULL CERTIFICATION & COMPLIANCE MANAGEMENT ENDPOINTS
# ===========================

# Payloads
class CertPayload(BaseModel):
    farmer_id: str
    unit_id: Optional[str] = None
    cert_type: str
    issuer: Optional[str] = None
    doc_ref: Optional[str] = None
    issued_at_iso: Optional[str] = None
    expires_at_iso: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class RenewalTaskPayload(BaseModel):
    farmer_id: str
    cert_id: str
    due_date_iso: Optional[str] = None
    assigned_to: Optional[str] = None
    notes: Optional[str] = None

class TaskUpdatePayload(BaseModel):
    updates: Dict[str, Any]

# Endpoints
@router.post("/farmer/compliance/cert")
def api_add_cert(req: CertPayload):
    res = add_certification(
        farmer_id=req.farmer_id,
        unit_id=req.unit_id,
        cert_type=req.cert_type,
        issuer=req.issuer,
        doc_ref=req.doc_ref,
        issued_at_iso=req.issued_at_iso,
        expires_at_iso=req.expires_at_iso,
        metadata=req.metadata
    )
    return res

@router.get("/farmer/compliance/cert/{cert_id}")
def api_get_cert(cert_id: str):
    res = get_cert(cert_id)
    if not res:
        raise HTTPException(status_code=404, detail="cert_not_found")
    return res

@router.get("/farmer/compliance/list")
def api_list_certs(farmer_id: Optional[str] = None, unit_id: Optional[str] = None):
    return {"certifications": list_certifications(farmer_id=farmer_id, unit_id=unit_id)}

@router.post("/farmer/compliance/revoke/{cert_id}")
def api_revoke_cert(cert_id: str, reason: Optional[str] = None):
    res = revoke_certification(cert_id, reason=reason)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res

@router.get("/farmer/compliance/expired")
def api_list_expired(farmer_id: Optional[str] = None):
    return {"expired": list_expired_certifications(farmer_id=farmer_id)}

@router.get("/farmer/compliance/expiring")
def api_list_expiring(days: Optional[int] = 30, farmer_id: Optional[str] = None):
    return {"expiring": list_expiring_within(days=days or 30, farmer_id=farmer_id)}

@router.get("/farmer/compliance/recommend_window/{cert_type}")
def api_recommend_window(cert_type: str):
    return {"cert_type": cert_type, "recommended_days_before": recommended_renewal_window(cert_type)}

@router.post("/farmer/compliance/renewal_task")
def api_create_renewal_task(req: RenewalTaskPayload):
    res = create_renewal_task(req.farmer_id, req.cert_id, due_date_iso=req.due_date_iso, assigned_to=req.assigned_to, notes=req.notes)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res

@router.post("/farmer/compliance/renewal_task/{task_id}")
def api_update_task(task_id: str, req: TaskUpdatePayload):
    res = update_renewal_task(task_id, req.updates)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res

@router.get("/farmer/compliance/tasks")
def api_list_tasks(farmer_id: Optional[str] = None, status: Optional[str] = None):
    return {"tasks": list_renewal_tasks(farmer_id=farmer_id, status=status)}

@router.post("/farmer/compliance/auto_create_tasks")
def api_auto_create_tasks(days_before: Optional[int] = 30):
    return auto_create_renewal_tasks(days_before=days_before or 30)

@router.get("/farmer/compliance/summary/{farmer_id}")
def api_summary(farmer_id: str):
    return compliance_summary_for_farmer(farmer_id)