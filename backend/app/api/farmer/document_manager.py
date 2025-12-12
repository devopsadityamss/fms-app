"""
API Routes — Document Manager (Farmer POV)
------------------------------------------

Allows farmers to store metadata and (optionally) file bytes in-memory.

Endpoints:
 - POST /farmer/documents/upload
 - GET  /farmer/documents/{doc_id}
 - GET  /farmer/documents
 - DELETE /farmer/documents/{doc_id}
"""

from fastapi import APIRouter, UploadFile, File, Form, Query, HTTPException
from typing import Optional, List

from app.services.farmer import document_manager_service as svc

router = APIRouter()


@router.post("/farmer/documents/upload")
async def api_upload_document(
    name: str = Form(...),
    doc_type: str = Form(...),
    tags: Optional[str] = Form(None),
    unit_id: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None)
):
    # Parse tags (comma-separated string → list)
    tag_list = tags.split(",") if tags else None

    file_bytes = None
    content_type = None

    if file:
        file_bytes = await file.read()
        content_type = file.content_type

    record = svc.create_document(
        name=name,
        doc_type=doc_type,
        tags=tag_list,
        unit_id=unit_id,
        file_bytes=file_bytes,
        content_type=content_type,
        notes=notes,
    )

    return record


@router.get("/farmer/documents/{doc_id}")
def api_get_document(doc_id: str):
    rec = svc.get_document(doc_id)
    if not rec:
        raise HTTPException(status_code=404, detail="document_not_found")
    return rec


@router.get("/farmer/documents")
def api_list_documents(
    doc_type: Optional[str] = Query(None),
    unit_id: Optional[str] = Query(None),
    tag: Optional[str] = Query(None)
):
    return svc.list_documents(doc_type=doc_type, unit_id=unit_id, tag=tag)


@router.delete("/farmer/documents/{doc_id}")
def api_delete_document(doc_id: str):
    ok = svc.delete_document(doc_id)
    if not ok:
        raise HTTPException(status_code=404, detail="document_not_found")
    return {"success": True}
