# backend/app/api/marketplace/provider.py

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.services.marketplace.provider_service import (
    register_provider_basic,
    get_provider,
    list_providers,
    update_provider,
    submit_kyc_document,
    list_kyc_documents,
    get_kyc_document,
    start_kyc_review,
    approve_kyc,
    reject_kyc,
    request_more_info,
    get_kyc_audit
)

router = APIRouter()


# ---------- payloads
class ProviderPayload(BaseModel):
    provider_id: Optional[str] = None
    name: str
    contact: Optional[str] = None
    address: Optional[str] = None


# ---------- provider endpoints
@router.post("/market/provider/onboard")
def api_onboard_provider(req: ProviderPayload):
    return register_provider_basic(req.provider_id, req.name, contact=req.contact, address=req.address)


@router.get("/market/provider/{provider_id}")
def api_get_provider(provider_id: str):
    p = get_provider(provider_id)
    if not p:
        raise HTTPException(status_code=404, detail="provider_not_found")
    return p


@router.get("/market/providers")
def api_list_providers(status: Optional[str] = None, q: Optional[str] = None):
    return list_providers(status=status, query=q)


@router.post("/market/provider/{provider_id}/update")
def api_update_provider(provider_id: str, updates: Dict[str, Any]):
    res = update_provider(provider_id, updates)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res


# ---------- KYC document upload (file)
@router.post("/market/provider/{provider_id}/kyc/submit")
async def api_submit_kyc(provider_id: str, file: UploadFile = File(...), doc_type: Optional[str] = Form(None)):
    try:
        content = await file.read()
    except Exception:
        raise HTTPException(status_code=400, detail="file_read_error")
    res = submit_kyc_document(provider_id, file.filename, file.content_type or "application/octet-stream", content, doc_type=doc_type)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res


@router.get("/market/provider/{provider_id}/kyc")
def api_list_kyc_documents(provider_id: str):
    return {"documents": list_kyc_documents(provider_id)}


@router.get("/market/provider/{provider_id}/kyc/{doc_id}")
def api_get_kyc(provider_id: str, doc_id: str):
    d = get_kyc_document(provider_id, doc_id)
    if not d:
        raise HTTPException(status_code=404, detail="doc_not_found")
    # return metadata only (bytes_b64 can be large); but include it if you want
    return {k: v for k, v in d.items() if k != "bytes_b64"}


# ---------- KYC reviewer actions (admin)
@router.post("/market/provider/{provider_id}/kyc/review/start")
def api_start_review(provider_id: str, reviewer_id: str):
    res = start_kyc_review(provider_id, reviewer_id)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res


@router.post("/market/provider/{provider_id}/kyc/approve")
def api_approve_kyc(provider_id: str, reviewer_id: str, comment: Optional[str] = None):
    res = approve_kyc(provider_id, reviewer_id, comment=comment)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res


@router.post("/market/provider/{provider_id}/kyc/reject")
def api_reject_kyc(provider_id: str, reviewer_id: str, comment: Optional[str] = None):
    res = reject_kyc(provider_id, reviewer_id, comment=comment)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res


@router.post("/market/provider/{provider_id}/kyc/request_more_info")
def api_request_more_info(provider_id: str, reviewer_id: str, comment: Optional[str] = None):
    res = request_more_info(provider_id, reviewer_id, comment=comment)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res


@router.get("/market/provider/{provider_id}/kyc/audit")
def api_get_kyc_audit(provider_id: Optional[str] = None, limit: Optional[int] = 100):
    return {"audit": get_kyc_audit(provider_id=provider_id, limit=limit or 100)}
