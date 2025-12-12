# backend/app/api/farmer/equipment_documents.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services.farmer.equipment_documents_service import (
    add_equipment_document,
    list_equipment_documents,
    get_expiring_documents,
    compute_equipment_compliance,
    fleet_compliance_overview
)

router = APIRouter()


class AddDocumentRequest(BaseModel):
    doc_type: str
    file_url: str
    issue_date: Optional[str] = None
    expiry_date: Optional[str] = None
    doc_number: Optional[str] = None
    notes: Optional[str] = None


@router.post("/equipment/{equipment_id}/documents/add")
def api_add_equipment_document(equipment_id: str, req: AddDocumentRequest):
    doc = add_equipment_document(
        equipment_id=equipment_id,
        doc_type=req.doc_type,
        file_url=req.file_url,
        issue_date=req.issue_date,
        expiry_date=req.expiry_date,
        doc_number=req.doc_number,
        notes=req.notes
    )
    return {"success": True, "document": doc}


@router.get("/equipment/{equipment_id}/documents")
def api_list_equipment_documents(equipment_id: str):
    return list_equipment_documents(equipment_id)


@router.get("/equipment/documents/expiring")
def api_expiring_documents(within_days: int = 30):
    return get_expiring_documents(within_days)


@router.get("/equipment/{equipment_id}/compliance")
def api_equipment_compliance(equipment_id: str):
    res = compute_equipment_compliance(equipment_id)
    if not res:
        raise HTTPException(status_code=404, detail="equipment_not_found")
    return res


@router.get("/equipment/compliance/fleet")
def api_fleet_compliance():
    return fleet_compliance_overview()

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services.farmer.equipment_documents_service import (
    add_equipment_document,
    verify_equipment_documents,
    fleet_document_verification
)

router = APIRouter()


# --------------------------
# Payload Schema
# --------------------------

class DocumentPayload(BaseModel):
    document_type: str
    document_number: Optional[str] = None
    issue_date: Optional[str] = None
    expiry_date: Optional[str] = None
    provider: Optional[str] = None
    notes: Optional[str] = None


# --------------------------
# Add or Update Document
# --------------------------

@router.post("/equipment/{equipment_id}/documents")
def api_add_document(equipment_id: str, req: DocumentPayload):
    doc = add_equipment_document(
        equipment_id=equipment_id,
        document_type=req.document_type,
        document_number=req.document_number,
        issue_date=req.issue_date,
        expiry_date=req.expiry_date,
        provider=req.provider,
        notes=req.notes,
    )
    return {"success": True, "document": doc}


# --------------------------
# Verify Documents
# --------------------------

@router.get("/equipment/{equipment_id}/documents/verify")
def api_verify_docs(equipment_id: str):
    result = verify_equipment_documents(equipment_id)
    if result.get("status") == "equipment_not_found":
        raise HTTPException(status_code=404, detail="equipment_not_found")
    return result


# --------------------------
# Fleet-Wide Document Verification
# --------------------------

@router.get("/equipment/documents/fleet")
def api_fleet_document_check():
    return fleet_document_verification()
